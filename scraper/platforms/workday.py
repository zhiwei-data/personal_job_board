import logging
from urllib.parse import urljoin, urlparse

from scraper.base import BaseScraper
from scraper.models import JobPosting
from scraper.utils import fetch_dynamic, el_text, clean_desc, parse_date, rate_limit

log = logging.getLogger(__name__)
PLATFORM = "workday"

LIST_SELECTOR   = "li[class*='css-'][data-automation-id='compositeContainer']"
TITLE_SELECTOR  = "a[data-automation-id='jobTitle']"
DETAIL_SELECTOR = "div[data-automation-id='job-posting-details']"
# Workday shows posted date in a <dd> near "Date Posted"
DATE_SELECTOR   = "dd[data-automation-id='postedOn'], dd[data-automation-id='datePosted']"


class WorkdayScraper(BaseScraper):
    """
    Workday boards are fully JS-rendered — Playwright required.
    - posted_date: extracted from the individual job page's "Date Posted" field.
    """

    def get_jobs(self) -> list[JobPosting]:
        soup = fetch_dynamic(self.url, wait_selector=TITLE_SELECTOR)
        if not soup:
            log.warning(f"[{self.company}] Workday: no content returned")
            return []

        base = self._base_url()
        jobs = []
        for card in soup.select(LIST_SELECTOR):
            a = card.select_one(TITLE_SELECTOR)
            if not a:
                continue
            title = el_text(a)
            href  = a.get("href", "")
            link  = href if href.startswith("http") else urljoin(base, href)
            loc   = el_text(
                card.select_one("dd[data-automation-id='workerSubType']") or
                card.select_one("dl dd")
            )
            dept  = el_text(
                card.select_one("dd[data-automation-id='primaryJob']") or
                card.select_one("dl dt")
            )
            desc, posted_date = self._desc_and_date(link)
            jobs.append(self._make_posting(title, link, PLATFORM, dept or "N/A", loc or "N/A", desc, posted_date))
            rate_limit()

        log.info(f"[{self.company}] Workday: {len(jobs)} jobs")
        return jobs

    def get_description(self, job_url: str) -> str:
        desc, _ = self._desc_and_date(job_url)
        return desc

    def _desc_and_date(self, job_url: str) -> tuple[str, str | None]:
        """Fetch the job page once and extract both description and posted date."""
        soup = fetch_dynamic(job_url, wait_selector=DETAIL_SELECTOR)
        if not soup:
            return "", None
        desc        = clean_desc(el_text(soup.select_one(DETAIL_SELECTOR)))
        date_el     = soup.select_one(DATE_SELECTOR)
        posted_date = parse_date(el_text(date_el)) if date_el else None
        return desc, posted_date

    def _base_url(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"
