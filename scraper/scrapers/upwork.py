"""UpWork-specific scraper."""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from scraper.engine import ScraperConfig
from scraper.scrapers.base import BaseScraper


class UpWorkScraper(BaseScraper):
    """Scraper tailored for UpWork freelance job listing pages.

    UpWork listings include contract-type metadata (fixed-price vs hourly)
    and experience-level tags that are unique to this platform.
    """

    platform: str = "upwork"

    PROMPT: str = (
        "Extract all freelance job listings from this UpWork page. For each job, "
        "extract the following fields as a JSON object:\n"
        "\n"
        "- title: Project/job title\n"
        "- company: Client name (if available)\n"
        "- location: Client location\n"
        "- salary: Budget or hourly rate\n"
        "- description: Full project description\n"
        "- requirements: Required skills and experience\n"
        "- url: Direct link to the job posting\n"
        "- skills: List of required skills\n"
        "- job_type: \"Fixed price\" or \"Hourly\"\n"
        "- experience_level: \"Entry\", \"Intermediate\", or \"Expert\"\n"
        "\n"
        "Return a JSON array of job objects. If there are no jobs, return an "
        "empty array."
    )

    def __init__(self, config: Optional[ScraperConfig] = None) -> None:
        super().__init__(config=config)
        logger.debug("UpWorkScraper initialised")

    def get_prompt(self) -> str:
        """Return the UpWork-specific extraction prompt."""
        return self.PROMPT

    def get_search_config(self) -> dict[str, Any]:
        """UpWork-specific search / graph configuration.

        UpWork feeds are loaded dynamically and may require scrolling past
        the initial viewport to surface all visible results.
        """
        return {
            "scroll": True,
            "scroll_interval": 2,
            "wait_for": "section.up-job-card",
            "headless": self.config.headless,
        }
