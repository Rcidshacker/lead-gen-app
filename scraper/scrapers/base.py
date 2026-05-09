"""Base scraper abstract class and shared utilities."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from loguru import logger

from scraper.engine import ScraperConfig


class BaseScraper(ABC):
    """Abstract base class for all platform-specific scrapers.

    Every concrete scraper must define a ``platform`` identifier and implement
    :meth:`get_prompt`.  Common helper methods for normalisation, salary
    parsing, and text cleaning are provided so that subclasses stay DRY.
    """

    platform: str = "custom"
    """Identifier used in the :data:`SCRAPER_REGISTRY`."""

    def __init__(self, config: Optional[ScraperConfig] = None) -> None:
        self.config = config or ScraperConfig()
        self.logger = logging.getLogger(f"scraper.{self.platform}")

    # ------------------------------------------------------------------
    # Abstract API
    # ------------------------------------------------------------------

    @abstractmethod
    def get_prompt(self) -> str:
        """Return the LLM extraction prompt for this platform.

        The prompt should instruct the model which fields to extract and how
        to structure them (ideally as a JSON list of objects).

        Returns:
            A human-readable prompt string.
        """
        ...

    # ------------------------------------------------------------------
    # Optional overrides
    # ------------------------------------------------------------------

    def get_search_config(self) -> dict[str, Any]:
        """Return extra ScrapeGraphAI configuration for this platform.

        Override in subclasses to inject platform-specific settings such as
        scroll depth, wait selectors, or cookie injection.

        Returns:
            A dictionary merged into the ScrapeGraphAI ``config`` param.
        """
        return {}

    def extract(self, raw_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Validate and normalise a single raw scraped job dict.

        The method checks that required fields are present, cleans text
        fields, and returns a normalised dictionary.  If required fields are
        missing the job is discarded and ``None`` is returned.

        Args:
            raw_data: The raw dict returned by ScrapeGraphAI for one job.

        Returns:
            A normalised dict, or ``None`` if validation fails.
        """
        title = self.clean_text(raw_data.get("title", ""))
        company = self.clean_text(raw_data.get("company", ""))

        if not title or not company:
            logger.warning(
                f"[{self.platform}] Skipping job — missing title or company: "
                f"title={title!r}, company={company!r}"
            )
            return None

        salary_raw = raw_data.get("salary", "")
        salary_parsed = self.parse_salary(str(salary_raw)) if salary_raw else ""

        return {
            "title": title,
            "company": company,
            "location": self.clean_text(raw_data.get("location", "")),
            "salary": salary_parsed,
            "description": self.clean_text(raw_data.get("description", "")),
            "requirements": self.clean_text(raw_data.get("requirements", "")),
            "url": str(raw_data.get("url", "")),
            "skills": raw_data.get("skills", []),
            "platform": self.platform,
            "raw_data": raw_data,
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def parse_salary(salary_str: str) -> str:
        """Normalise a salary string into a consistent ``"<min>-<max> <currency>"`` format.

        Handles patterns such as:
        * ``$80,000 - $120,000``
        * ``80k-120k USD``
        * ``£45,000 per annum``
        * ``₹10,00,000 – ₹15,00,000``
        * ``$50/hr``

        Args:
            salary_str: The raw salary text.

        Returns:
            A cleaned, normalised salary string.  Returns the original string
            unchanged when no recognised pattern is found.
        """
        if not salary_str:
            return ""

        # Strip whitespace
        s = salary_str.strip()

        # Currency symbols / codes
        currency_map: dict[str, str] = {
            "$": "USD",
            "USD": "USD",
            "£": "GBP",
            "GBP": "GBP",
            "€": "EUR",
            "EUR": "EUR",
            "₹": "INR",
            "INR": "INR",
            "A$": "AUD",
            "AUD": "AUD",
            "C$": "CAD",
            "CAD": "CAD",
        }

        detected_currency = ""
        for sym, code in currency_map.items():
            if sym in s:
                detected_currency = code
                s = s.replace(sym, "")
                break

        # Normalise "k" suffix → "000"
        s = re.sub(r"([\d,.]+)\s*k\b", r"\g<1>000", s, flags=re.IGNORECASE)

        # Extract numeric ranges
        # Pattern: "80,000 - 120,000" or "80000–120000"
        range_match = re.search(
            r"([\d,.]+)\s*[-–—~to]+\s*([\d,.]+)", s
        )
        if range_match:
            low = range_match.group(1).replace(",", "")
            high = range_match.group(2).replace(",", "")
            return f"{low}-{high} {detected_currency}".strip()

        # Pattern: single number (e.g., "80000")
        single_match = re.search(r"([\d,.]+)", s)
        if single_match:
            value = single_match.group(1).replace(",", "")
            return f"{value} {detected_currency}".strip()

        # Pattern: hourly rate (e.g., "50/hr" after symbol removal)
        hourly_match = re.search(r"([\d,.]+)\s*/\s*hr", s, re.IGNORECASE)
        if hourly_match:
            value = hourly_match.group(1).replace(",", "")
            return f"{value}/hr {detected_currency}".strip()

        # Fallback — return cleaned original
        return re.sub(r"\s+", " ", salary_str.strip())

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalise a text field.

        * Strips leading/trailing whitespace.
        * Collapses internal whitespace and newlines.
        * Removes zero-width characters and non-printable Unicode.
        * HTML-entity decodes ``&amp;``, ``&lt;``, ``&gt;``, ``&nbsp;``.

        Args:
            text: The raw text string.

        Returns:
            A cleaned text string.
        """
        if not text:
            return ""

        import html

        cleaned = html.unescape(str(text))
        # Remove zero-width characters
        cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", cleaned)
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
