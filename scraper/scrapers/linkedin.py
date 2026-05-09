"""LinkedIn-specific scraper."""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from scraper.engine import ScraperConfig
from scraper.scrapers.base import BaseScraper


class LinkedInScraper(BaseScraper):
    """Scraper tailored for LinkedIn job listing pages.

    LinkedIn pages use dynamic rendering and infinite scroll, so the
    ScrapeGraphAI graph is configured to scroll and wait for lazy-loaded
    job cards before extraction.
    """

    platform: str = "linkedin"

    PROMPT: str = (
        "Extract all job listings from this LinkedIn page. For each job, extract "
        "the following fields as a JSON object:\n"
        "\n"
        "- title: Job title\n"
        "- company: Company name\n"
        "- location: Job location (city, state/country)\n"
        "- salary: Salary range if available\n"
        "- description: Full job description text\n"
        "- requirements: Key requirements/skills listed\n"
        "- url: Direct link to the job posting\n"
        "- skills: List of required skills (as array)\n"
        "- posted_date: When the job was posted (relative or absolute date)\n"
        "\n"
        "Return a JSON array of job objects. If there are no jobs, return an "
        "empty array."
    )

    def __init__(self, config: Optional[ScraperConfig] = None) -> None:
        super().__init__(config=config)
        logger.debug("LinkedInScraper initialised")

    def get_prompt(self) -> str:
        """Return the LinkedIn-specific extraction prompt."""
        return self.PROMPT

    def get_search_config(self) -> dict[str, Any]:
        """LinkedIn-specific search / graph configuration.

        Adds scroll behaviour to handle infinite-scroll job listings and a
        wait selector for the job card container.
        """
        return {
            "scroll": True,
            "scroll_interval": 2,
            "wait_for": "div.scaffold-layout__list",
            "headless": self.config.headless,
        }
