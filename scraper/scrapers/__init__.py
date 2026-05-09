"""Platform-specific scraper registry."""

from scraper.scrapers.base import BaseScraper
from scraper.scrapers.linkedin import LinkedInScraper
from scraper.scrapers.naukri import NaukriScraper
from scraper.scrapers.upwork import UpWorkScraper
from scraper.scrapers.indeed import IndeedScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "upwork": UpWorkScraper,
    "indeed": IndeedScraper,
    "custom": BaseScraper,
}

__all__ = [
    "SCRAPER_REGISTRY",
    "BaseScraper",
    "LinkedInScraper",
    "NaukriScraper",
    "UpWorkScraper",
    "IndeedScraper",
]
