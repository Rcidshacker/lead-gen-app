"""Core scraping engine that wraps ScrapeGraphAI for intelligent job extraction.

Implements a layered LLM fallback strategy so that scraping remains resilient
even when the primary model hallucinates, times out, or returns empty results.
"""

import asyncio
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

        # Sites behind Akamai/Cloudflare block standard headless Chrome.
        # Pre-fetch rendered HTML via camoufox and pass as a string source so
        # SmartScraperGraph skips its own fetch step entirely.
        llm_source: str = url
        if scraper.needs_stealth_browser:
            logger.info(f"Stealth browser required for {platform}, pre-fetching via camoufox")
            llm_source = await self._fetch_with_camoufox(url)
            if not llm_source:
                raise RuntimeError(f"camoufox returned empty content for {url}")
            logger.info(f"camoufox fetched {len(llm_source)} bytes for {url}")

        # ── Layered LLM fallback strategy ──────────────────────────────
        last_error: Exception | None = None
        models_to_try = self.config.all_models

        loop = asyncio.get_event_loop()

        for model_name in models_to_try:
            try:
                # SmartScraperGraph.run() calls asyncio.run() internally; run it
                # in a thread so it gets its own clean event loop context.
                import functools
                result = await loop.run_in_executor(
                    None,
                    functools.partial(
                        self._scrape_with_model_sync,
                        prompt=prompt,
                        source=llm_source,
                        model_name=model_name,
                        api_key=os.getenv("OPENAI_API_KEY", ""),
                        base_url=os.getenv("OPENAI_BASE_URL"),
                    ),
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

    async def _fetch_with_camoufox(self, url: str) -> str:
        """Fetch rendered page HTML via camoufox (anti-bot Firefox fork).

        Used for sites protected by Akamai, Cloudflare, or similar WAFs that
        block standard headless Chromium.  Waits for any JS job-card selector
        to appear before capturing the full DOM.

        Args:
            url: Target URL to fetch.

        Returns:
            Full rendered HTML as a string, or empty string on failure.
        """
        try:
            from camoufox.async_api import AsyncCamoufox  # type: ignore[import-untyped]
        except ImportError:
            logger.error("camoufox not installed. Run: pip install 'camoufox[geoip]'")
            return ""

        try:
            async with AsyncCamoufox(headless=True, os="windows") as browser:
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                # Best-effort wait for job card container
                try:
                    await page.wait_for_selector(
                        "article.jobTuple, [data-job-id], [class*='srp-jobtuple'], "
                        "[class*='job-tuple'], [class*='jobCard']",
                        timeout=8_000,
                    )
                except Exception:
                    pass  # proceed with whatever rendered
                html = await page.content()

            # Strip script/style/meta noise so the LLM sees only visible DOM
            cleaned = self._strip_noise_from_html(html)
            logger.info(
                f"camoufox fetched {len(html)} bytes → {len(cleaned)} bytes "
                f"after stripping noise from {url}"
            )
            return cleaned
        except Exception as exc:
            logger.error(f"camoufox fetch failed for {url}: {exc}")
            return ""

    @staticmethod
    def _strip_noise_from_html(html: str) -> str:
        """Extract only job-card elements from HTML (or strip noise as fallback).

        Strategy:
        1. Try known job-card selectors to return only the listing section.
        2. Fall back to full HTML with script/style/meta stripped.

        This keeps the LLM context focused on actual job data.
        """
        try:
            from bs4 import BeautifulSoup  # type: ignore[import-untyped]

            soup = BeautifulSoup(html, "lxml")

            # Try to isolate job listing containers first
            job_card_selectors = [
                "article.jobTuple",
                "[data-job-id]",
                "[class*='srp-jobtuple']",
                "[class*='job-tuple']",
                "[class*='jobCard']",
                "[class*='job_card']",
                "li.job-posting",
                "div.job-container",
            ]
            cards = []
            for sel in job_card_selectors:
                cards = soup.select(sel)
                if cards:
                    break

            if cards:
                # Cap at 10 cards so free LLMs don't time out
                cards = cards[:10]
                # Convert to plain text (title + company + location + URL per line)
                # This slashes token count vs raw HTML
                lines = []
                for card in cards:
                    text = " | ".join(card.stripped_strings)
                    href = ""
                    link = card.find("a", href=True)
                    if link:
                        href = link.get("href", "")
                    lines.append(f"{text} | URL: {href}")
                plain_text = "\n".join(lines)
                return f"<html><body><pre>{plain_text}</pre></body></html>"

            # Fallback: strip all noise from full page
            for tag in soup(["script", "style", "link", "meta", "noscript", "svg", "path", "img"]):
                tag.decompose()
            return str(soup)
        except Exception:
            return html  # last resort

    def _scrape_with_model_sync(
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
        from scrapegraphai.graphs.abstract_graph import AbstractGraph  # type: ignore[import-untyped]

        # ScrapeGraphAI v1.6 _set_model_token only handles a fixed set of LLM
        # types. When model_instance is a plain ChatOpenAI the attribute is never
        # set, causing _create_graph to raise AttributeError. Patch it once per
        # call so the configured token limit is always available.
        _orig_create_llm = AbstractGraph._create_llm

        def _patched_create_llm(self_graph, llm_cfg, chat=False):
            result = _orig_create_llm(self_graph, llm_cfg, chat)
            if not hasattr(self_graph, "model_token"):
                self_graph.model_token = llm_cfg.get("model_tokens", 8192)
            return result

        AbstractGraph._create_llm = _patched_create_llm

        embeddings_config: dict[str, Any] | None = None

        if base_url:
            # ScrapeGraphAI v1.6 only recognises a fixed set of model-name prefixes.
            # For any custom OpenAI-compatible endpoint (OpenRouter, etc.) bypass
            # that detection entirely by passing pre-built LangChain instances.
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # type: ignore[import-untyped]

            llm_config: dict[str, Any] = {
                "model_instance": ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    base_url=base_url,
                    temperature=self.config.temperature,
                ),
                "model_tokens": int(os.getenv("SGAI_MAX_TOKENS", "4096")),
            }
            embeddings_config = {
                "model_instance": OpenAIEmbeddings(
                    model="text-embedding-ada-002",
                    api_key=api_key,
                    base_url=base_url,
                )
            }
        else:
            llm_config = {
                "model": model_name,
                "temperature": self.config.temperature,
                "api_key": api_key,
            }

        graph_config: dict[str, Any] = {
            "llm": llm_config,
            "headless": self.config.headless,
            "verbose": self.config.verbose,
        }
        if embeddings_config is not None:
            graph_config["embeddings"] = embeddings_config

        self._graph = SmartScraperGraph(
            prompt=prompt,
            source=source,
            config=graph_config,
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
