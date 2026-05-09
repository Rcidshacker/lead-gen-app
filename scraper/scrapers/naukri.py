"""Naukri-specific scraper."""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from scraper.engine import ScraperConfig
from scraper.scrapers.base import BaseScraper


class NaukriScraper(BaseScraper):
    """Scraper tailored for Naukri.com job listing pages.

    Naukri pages are heavily JavaScript-rendered and include experience and
    education fields that are less common on Western platforms.
    """

    platform: str = "naukri"

    PROMPT: str = (
        "Extract all job listings from this Naukri page. For each job, extract "
        "the following fields as a JSON object:\n"
        "\n"
        "- title: Job title / role\n"
        "- company: Company name\n"
        "- location: Job location\n"
        "- salary: Salary range if mentioned\n"
        "- description: Full job description\n"
        "- requirements: Key qualifications and skills\n"
        "- experience: Required experience in years\n"
        "- url: Direct link to the job posting\n"
        "- skills: List of required skills\n"
        "- education: Required education (degree, field)\n"
        "\n"
        "Return a JSON array of job objects. If there are no jobs, return an "
        "empty array."
    )

    def __init__(self, config: Optional[ScraperConfig] = None) -> None:
        super().__init__(config=config)
        logger.debug("NaukriScraper initialised")

    def get_prompt(self) -> str:
        """Return the Naukri-specific extraction prompt."""
        return self.PROMPT

    def get_search_config(self) -> dict[str, Any]:
        """Naukri-specific search / graph configuration.

        Naukri uses client-side rendering with pagination that loads more
        results on scroll.
        """
        return {
            "scroll": True,
            "scroll_interval": 2,
            "wait_for": "div.listingContainer",
            "headless": self.config.headless,
        }
