"""
Generic Playwright scraper for platforms with no dedicated implementation.
Uses heuristic selectors to extract job titles, links, and optionally dates.
"""

import logging
from urllib.parse import urljoin, urlparse

from scraper.base import BaseScraper
from scraper.models import JobPosting
from scraper.utils import fetch_dynamic, el_text, clean_desc, parse_date, rate_limit

log = logging.getLogger(__name__)
PLATFORM = "generic"

JOB_LINK_SELECTORS = [
    "a[href*='/job/']",
    "a[href*='/jobs/']",
    "a[href*='/careers/']",
    "a[href*='/position']",
    "a[href*='/opening']",
    "a[href*='/posting']",
    "a[href*='/apply']",
]

DESCRIPTION_SELECTORS = [
    "[data-testid*='description']",
    "[class*='job-description']",
    "[class*='jobDescription']",
    "[class*='posting-description']",
    "[id*='job-description']",
    "[id*='jobDescription']",
    "article",
    "main",
]

# Selectors for date on a job detail page, tried in order
DATE_SELECTORS = [
    "time[datetime]",                        # <time datetime="2024-03-15">
    "[data-testid*='date']",
    "[class*='posted-date']",
    "[class*='postedDate']",
    "[class*='post-date']",
    "[class*='job-date']",
]


class GenericScraper(BaseScraper):
    """Playwright-based fallback scraper with heuristic extraction."""

    def get_jobs(self) -> list[JobPosting]:
        soup = fetch_dynamic(self.url)
        if not soup:
            log.warning(f"[{self.company}] Generic: no content returned for {self.url}")
            return []

        base = self._base_url()
        seen = set()
        jobs = []

        for selector in JOB_LINK_SELECTORS:
            links = soup.select(selector)
            if not links:
                continue
            for a in links:
                href = a.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)
                title = el_text(a) or "N/A"
                link  = href if href.startswith("http") else urljoin(base, href)
                desc, posted_date = self._desc_and_date(link)
                jobs.append(self._make_posting(title, link, PLATFORM, description=desc, posted_date=posted_date))
                rate_limit()
            if jobs:
                break

        if not jobs:
            log.warning(
                f"[{self.company}] Generic: no job links found. "
                "Consider adding a dedicated scraper for this site."
            )

        log.info(f"[{self.company}] Generic: {len(jobs)} jobs")
        return jobs

    def get_description(self, job_url: str) -> str:
        desc, _ = self._desc_and_date(job_url)
        return desc

    def _desc_and_date(self, job_url: str) -> tuple[str, str | None]:
        """Fetch the job page once, extract both description and posted date."""
        soup = fetch_dynamic(job_url)
        if not soup:
            return "", None

        desc = ""
        for selector in DESCRIPTION_SELECTORS:
            el = soup.select_one(selector)
            if el:
                desc = clean_desc(el_text(el))
                break

        posted_date = None
        for selector in DATE_SELECTORS:
            el = soup.select_one(selector)
            if el:
                # Prefer the datetime attribute; fall back to visible text
                raw = el.get("datetime") or el_text(el)
                posted_date = parse_date(raw)
                if posted_date:
                    break

        return desc, posted_date

    def _base_url(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"
