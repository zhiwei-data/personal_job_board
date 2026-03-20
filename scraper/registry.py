"""
Registry: maps platform key → scraper class.

To add a new platform:
  1. Create scraper/platforms/<name>.py with a class extending BaseScraper
  2. Add one line here
"""

from scraper.platforms.ashby       import AshbyScraper
from scraper.platforms.generic     import GenericScraper
from scraper.platforms.greenhouse  import GreenhouseScraper
from scraper.platforms.lever       import LeverScraper
from scraper.platforms.workday     import WorkdayScraper

REGISTRY: dict[str, type] = {
    "greenhouse":      GreenhouseScraper,
    "lever":           LeverScraper,
    "ashby":           AshbyScraper,
    "workday":         WorkdayScraper,
    "generic":         GenericScraper,
}

SUPPORTED_PLATFORMS = ", ".join(sorted(REGISTRY))


def get_scraper(platform: str):
    """Return the scraper class for the given platform key, or GenericScraper."""
    return REGISTRY.get(platform.lower(), GenericScraper)