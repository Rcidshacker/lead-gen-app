"""Indeed-specific scraper."""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from scraper.engine import ScraperConfig
from scraper.scrapers.base import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper tailored for Indeed job listing pages.

    Indeed surfaces company ratings and remote-work badges that are useful for
    lead scoring downstream.
    """

    platform: str = "indeed"

    PROMPT: str = (
        "Extract all job listings from this Indeed page. For each job, extract "
        "the following fields as a JSON object:\n"
        "\n"
        "- title: Job title\n"
        "- company: Company name\n"
        "- location: Job location\n"
        "- salary: Salary information if available\n"
        "- description: Full job description\n"
        "- requirements: Key requirements\n"
        "- url: Direct link to the job posting\n"
        "- rating: Company rating if available (numeric, e.g. 4.2)\n"
        "- remote: Whether the job is remote (\"Yes\" or \"No\")\n"
        "\n"
        "Return a JSON array of job objects. If there are no jobs, return an "
        "empty array."
    )

    def __init__(self, config: Optional[ScraperConfig] = None) -> None:
        super().__init__(config=config)
        logger.debug("IndeedScraper initialised")

    def get_prompt(self) -> str:
        """Return the Indeed-specific extraction prompt."""
        return self.PROMPT

    def get_search_config(self) -> dict[str, Any]:
        """Indeed-specific search / graph configuration.

        Indeed uses pagination and may serve job cards via JS after the
        initial page load.
        """
        return {
            "scroll": True,
            "scroll_interval": 2,
            "wait_for": "div.job_seen_beacon",
            "headless": self.config.headless,
        }
