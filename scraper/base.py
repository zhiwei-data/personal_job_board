"""
Abstract base class all platform scrapers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional

from scraper.models import JobPosting


class BaseScraper(ABC):
    """
    Every platform scraper inherits from this.

    Subclasses must implement:
      - get_jobs()        -> list[JobPosting]  scrape listing page
      - get_description() -> str               scrape individual job page
    """

    def __init__(self, company: str, industry: str, url: str):
        self.company  = company
        self.industry = industry
        self.url      = url

    @abstractmethod
    def get_jobs(self) -> list[JobPosting]:
        """Scrape the job listing page and return a list of JobPosting objects."""
        ...

    @abstractmethod
    def get_description(self, job_url: str) -> str:
        """Fetch and return the full description for a single job posting."""
        ...

    def _make_posting(
        self,
        title: str,
        link: str,
        platform: str,
        department: str = "N/A",
        location: str = "N/A",
        description: str = "",
        posted_date: Optional[str] = None,
    ) -> JobPosting:
        """Convenience factory — avoids repeating company/industry in every scraper."""
        return JobPosting(
            company=self.company,
            industry=self.industry,
            platform=platform,
            title=title,
            department=department,
            location=location,
            description=description,
            link=link,
            posted_date=posted_date,
        )
