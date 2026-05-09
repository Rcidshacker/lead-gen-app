"""Core scraping engine that wraps ScrapeGraphAI for intelligent job extraction.

Implements a layered LLM fallback strategy so that scraping remains resilient
even when the primary model hallucinates, times out, or returns empty results.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from loguru import logger

from scraper.utils.normalizer import generate_content_hash, normalize_url
from scraper.utils.rate_limiter import RateLimiter


@dataclass
class ScraperConfig:
    """Configuration for the scraping engine.

    Attributes:
        model: Primary LLM model identifier for ScrapeGraphAI.
        fallback_models: Ordered list of fallback model names to try when
            the primary model fails (timeout, empty result, API error).
        temperature: Sampling temperature for the LLM (lower = more deterministic).
        headless: Whether to run the browser in headless mode.
        max_pages: Maximum number of pages to scrape per source.
        delay: Delay in seconds between consecutive requests.
        timeout: HTTP request timeout in seconds.
        verbose: Enable verbose logging from ScrapeGraphAI.
        max_retries_per_model: How many times to retry each model before
            falling back to the next one.
    """

    model: str = field(
        default_factory=lambda: os.getenv("SGAI_MODEL", "gpt-4o-mini")
    )
    fallback_models: list[str] = field(
        default_factory=lambda: [
            m.strip()
            for m in os.getenv("SGAI_FALLBACK_MODELS", "").split(",")
            if m.strip()
        ]
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("SGAI_TEMPERATURE", "0.1"))
    )
    headless: bool = True
    max_pages: int = 5
    delay: int = field(
        default_factory=lambda: int(os.getenv("SCRAPER_DEFAULT_DELAY", "2"))
    )
    timeout: int = field(
        default_factory=lambda: int(os.getenv("SCRAPER_TIMEOUT", "30"))
    )
    verbose: bool = True
    max_retries_per_model: int = 1

    @property
    def all_models(self) -> list[str]:
        """Return primary model followed by fallbacks."""
        models = [self.model]
        for fb in self.fallback_models:
            if fb not in models:
                models.append(fb)
        return models


class ScraperEngine:
    """Main orchestrator that routes scraping jobs to platform-specific scrapers.

    The engine detects the target platform from the URL, selects the appropriate
    scraper class from the registry, builds a ScrapeGraphAI ``SmartScraperGraph``,
    and normalises the raw result into a uniform job-listing schema.

    LLM Fallback Strategy
    ---------------------
    If the primary model fails (timeout, API error, or returns empty results),
    the engine automatically falls back to the next model in the configured
    chain.  This ensures scraping resilience without manual intervention.

    Example::

        engine = ScraperEngine()
        jobs = await engine.scrape(job_source)
    """

    def __init__(self, config: Optional[ScraperConfig] = None) -> None:
        self.config = config or ScraperConfig()
        self._graph: Any = None
        self._rate_limiter = RateLimiter(default_rate=1.0)
        # Per-platform conservative limits — these sites block aggressive scrapers
        self._rate_limiter.set_rate("www.linkedin.com", 0.25)   # 1 req / 4s
        self._rate_limiter.set_rate("linkedin.com", 0.25)
        self._rate_limiter.set_rate("www.naukri.com", 0.5)      # 1 req / 2s
        self._rate_limiter.set_rate("naukri.com", 0.5)
        self._rate_limiter.set_rate("www.upwork.com", 0.33)     # 1 req / 3s
        self._rate_limiter.set_rate("upwork.com", 0.33)
        self._rate_limiter.set_rate("www.indeed.com", 0.5)
        self._rate_limiter.set_rate("indeed.com", 0.5)
        logger.info(
            f"ScraperEngine initialized with model={self.config.model}, "
            f"fallbacks={self.config.fallback_models}"
        )

    # ------------------------------------------------------------------
    # Platform detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_platform(url: str) -> str:
        """Detect the job platform from a URL hostname.

        Args:
            url: The URL to inspect.

        Returns:
            A platform key such as ``"linkedin"``, ``"naukri"``, ``"upwork"``,
            ``"indeed"``, or ``"custom"`` for unrecognised domains.
        """
        host = urlparse(url).hostname or ""
        platform_map: dict[str, str] = {
            "linkedin.com": "linkedin",
            "naukri.com": "naukri",
            "upwork.com": "upwork",
            "indeed.com": "indeed",
        }
        for domain, platform in platform_map.items():
            if domain in host:
                return platform
        return "custom"

    @staticmethod
    def _get_scraper_prompt(platform: str) -> str:
        """Return the extraction prompt for *platform*.

        This is kept as a static helper for backwards-compatibility.  The
        canonical prompts now live inside each scraper class.
        """
        prompts: dict[str, str] = {
            "linkedin": (
                "Extract all job listings from this LinkedIn page. For each job, "
                "extract:\n"
                "- title: Job title\n"
                "- company: Company name\n"
                "- location: Job location (city, state/country)\n"
                "- salary: Salary range if available\n"
                "- description: Full job description text\n"
                "- requirements: Key requirements/skills listed\n"
                "- url: Direct link to the job posting\n"
                "- skills: List of required skills (as array)\n"
                "- posted_date: When the job was posted (relative or absolute date)"
            ),
            "naukri": (
                "Extract all job listings from this Naukri page. For each job, "
                "extract:\n"
                "- title: Job title / role\n"
                "- company: Company name\n"
                "- location: Job location\n"
                "- salary: Salary range if mentioned\n"
                "- description: Full job description\n"
                "- requirements: Key qualifications and skills\n"
                "- experience: Required experience in years\n"
                "- url: Direct link to the job posting\n"
                "- skills: List of required skills\n"
                "- education: Required education"
            ),
            "upwork": (
                "Extract all freelance job listings from this UpWork page. For each "
                "job, extract:\n"
                "- title: Project/job title\n"
                "- company: Client name (if available)\n"
                "- location: Client location\n"
                "- salary: Budget or hourly rate\n"
                "- description: Full project description\n"
                "- requirements: Required skills and experience\n"
                "- url: Direct link to the job posting\n"
                "- skills: List of required skills\n"
                "- job_type: Fixed price or Hourly\n"
                "- experience_level: Entry, Intermediate, Expert"
            ),
            "indeed": (
                "Extract all job listings from this Indeed page. For each job, "
                "extract:\n"
                "- title: Job title\n"
                "- company: Company name\n"
                "- location: Job location\n"
                "- salary: Salary information if available\n"
                "- description: Full job description\n"
                "- requirements: Key requirements\n"
                "- url: Direct link to the job posting\n"
                "- rating: Company rating if available\n"
                "- remote: Whether the job is remote"
            ),
            "custom": (
                "Extract all job listings from this page. For each job, extract:\n"
                "- title: Job title\n"
                "- company: Company name\n"
                "- location: Job location if available\n"
                "- salary: Salary information if available\n"
                "- description: Full job description or summary\n"
                "- requirements: Key requirements or qualifications\n"
                "- url: Direct link to the job posting\n"
                "- skills: List of required skills if mentioned"
            ),
        }
        return prompts.get(platform, prompts["custom"])

    # ------------------------------------------------------------------
    # Main entry-point
    # ------------------------------------------------------------------

    async def scrape(self, source: Any) -> list[dict]:
        """Scrape a job source and return normalised job listings.

        Implements a layered LLM fallback: if the primary model fails or
        returns empty results, each fallback model is tried in order before
        giving up.

        Args:
            source: Any object with a ``url`` attribute, or a plain URL string.

        Returns:
            A list of normalised job dictionaries.
        """
        from scraper.scrapers import SCRAPER_REGISTRY

        url: str = getattr(source, "url", str(source))
        platform: str = self._detect_platform(url)

        # Apply per-domain rate limit before any network activity
        _domain = urlparse(url).hostname or "unknown"
        self._rate_limiter.acquire(_domain)
        logger.info(f"Rate limit cleared for domain={_domain}")

        scrape_config: dict = getattr(source, "scrape_config", {}) or {}

        logger.info(f"Starting scrape: platform={platform}, url={url}")

        # Look up platform-specific scraper
        scraper_class = SCRAPER_REGISTRY.get(platform)
        if scraper_class is None:
            logger.warning(f"No specific scraper for {platform}, using generic")
            scraper_class = SCRAPER_REGISTRY.get("custom")

        scraper = scraper_class(config=self.config)
        prompt: str = scraper.get_prompt()

        # ── Layered LLM fallback strategy ──────────────────────────────
        last_error: Exception | None = None
        models_to_try = self.config.all_models

        for model_name in models_to_try:
            try:
                result = await self._scrape_with_model(
                    prompt=prompt,
                    source=url,
                    model_name=model_name,
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                    base_url=os.getenv("OPENAI_BASE_URL"),
                )

                if not result:
                    logger.warning(
                        f"Model {model_name} returned empty result for {url}"
                    )
                    last_error = ValueError(f"Empty result from {model_name}")
                    continue  # try next fallback

                # Normalise results (includes URL normalization)
                jobs = self._normalize_results(result, platform)
                logger.info(
                    f"Scrape completed for {url} using {model_name}, "
                    f"{len(jobs)} job listings extracted"
                )
                return jobs

            except ImportError:
                logger.error(
                    "scrapegraphai not installed. Run: pip install scrapegraphai"
                )
                return []
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Model {model_name} failed for {url}: {exc}. "
                    f"Trying next fallback..."
                )
                continue

        # All models exhausted
        logger.error(
            f"All {len(models_to_try)} models failed for {url}. "
            f"Last error: {last_error}"
        )
        if last_error:
            raise last_error
        return []

    async def _scrape_with_model(
        self,
        prompt: str,
        source: str,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> Any:
        """Run ScrapeGraphAI with a specific model configuration.

        Parameters
        ----------
        prompt:
            Extraction prompt for the target platform.
        source:
            URL to scrape.
        model_name:
            LLM model identifier (e.g. "gpt-4o-mini").
        api_key:
            API key for the LLM provider.
        base_url:
            Optional custom base URL (for OpenRouter, etc.).

        Returns
        -------
        Any
            Raw result from ``SmartScraperGraph.run()``.
        """
        from scrapegraphai.graphs import SmartScraperGraph  # type: ignore[import-untyped]

        llm_config: dict[str, Any] = {
            "model": model_name,
            "temperature": self.config.temperature,
            "api_key": api_key,
        }
        if base_url:
            llm_config["base_url"] = base_url

        self._graph = SmartScraperGraph(
            prompt=prompt,
            source=source,
            config={
                "llm": llm_config,
                "headless": self.config.headless,
                "verbose": self.config.verbose,
            },
        )

        result: Any = self._graph.run()
        logger.info(
            f"Model {model_name} returned for {source}, "
            f"raw result keys: "
            f"{list(result.keys()) if isinstance(result, dict) else 'N/A'}"
        )
        return result

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    def _normalize_results(self, result: Any, platform: str) -> list[dict]:
        """Normalize scraping results into a consistent format.

        The raw ScrapeGraphAI result may be a single dict (one job), a dict whose
        values contain lists, or a plain list.  This method handles all cases and
        returns a uniform list of job dictionaries.

        URLs are normalized using :func:`~scraper.utils.normalizer.normalize_url`
        and a content hash is pre-computed for deduplication using
        :func:`~scraper.utils.normalizer.generate_content_hash`.

        Args:
            result: The raw result returned by ``SmartScraperGraph.run()``.
            platform: The detected platform identifier.

        Returns:
            A list of normalised job dictionaries.
        """
        jobs: list[dict] = []

        if isinstance(result, dict):
            # Look for a key whose value is a list of job dicts
            for _key, value in result.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and any(
                        k in value[0] for k in ("title", "company", "description")
                    ):
                        jobs = value
                        break

            # Fallback: treat the whole dict as a single job
            if not jobs and any(
                k in result for k in ("title", "company", "description")
            ):
                jobs = [result]

        elif isinstance(result, list):
            jobs = result

        # Normalise each job entry
        normalized: list[dict] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue

            title = job.get("title", "")
            company = job.get("company", "")
            location = job.get("location", "")
            raw_url = job.get("url", "")
            normalized_url = normalize_url(raw_url) if raw_url else ""

            normalized.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": str(job.get("salary", "")),
                    "description": job.get("description", ""),
                    "requirements": job.get("requirements", ""),
                    "url": normalized_url,
                    "skills": job.get("skills", []),
                    "platform": platform,
                    "raw_data": job,
                    "contact_info": {},
                    # Pre-computed content hash for deduplication
                    "content_hash": generate_content_hash(title, company, location),
                }
            )

        return normalized
