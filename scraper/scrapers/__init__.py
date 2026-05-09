"""Platform-specific scraper registry."""

from scraper.scrapers.base import BaseScraper, CustomScraper
from scraper.scrapers.linkedin import LinkedInScraper
from scraper.scrapers.naukri import NaukriScraper
from scraper.scrapers.upwork import UpWorkScraper
from scraper.scrapers.indeed import IndeedScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "upwork": UpWorkScraper,
    "indeed": IndeedScraper,
    "custom": CustomScraper,  # concrete class — was BaseScraper (abstract), which caused TypeError
}

__all__ = [
    "SCRAPER_REGISTRY",
    "BaseScraper",
    "CustomScraper",
    "LinkedInScraper",
    "NaukriScraper",
    "UpWorkScraper",
    "IndeedScraper",
]
