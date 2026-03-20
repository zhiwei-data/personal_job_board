import logging

from scraper.base import BaseScraper
from scraper.models import JobPosting
from scraper.utils import fetch_static, fetch, el_text, clean_desc, parse_date, rate_limit

log = logging.getLogger(__name__)
PLATFORM = "lever"


class LeverScraper(BaseScraper):
    """
    Uses Lever's public v0 API for job listings.
    - posted_date: available as `createdAt` (Unix ms timestamp) in the API response.
    Falls back to HTML scraping if the API is unavailable.
    """

    def get_jobs(self) -> list[JobPosting]:
        slug    = self.url.rstrip("/").split("/")[-1]
        api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        data    = fetch_static(api_url, as_json=True)

        if isinstance(data, list):
            return self._from_api(data)

        log.debug(f"[{self.company}] Lever API unavailable, falling back to HTML")
        return self._from_html()

    def _from_api(self, items: list) -> list[JobPosting]:
        jobs = []
        for item in items:
            title = item.get("text", "N/A")
            link  = item.get("hostedUrl", "")
            cats  = item.get("categories", {})
            dept  = cats.get("team", "N/A")
            loc   = cats.get("location", "N/A")
            desc  = self.get_description(link)
            # Lever returns createdAt as Unix milliseconds
            posted_date = self._parse_lever_ts(item.get("createdAt"))
            jobs.append(self._make_posting(title, link, PLATFORM, dept, loc, desc, posted_date))
            rate_limit()
        log.info(f"[{self.company}] Lever API: {len(jobs)} jobs")
        return jobs

    def _from_html(self) -> list[JobPosting]:
        soup = fetch(self.url)
        if not soup:
            return []
        jobs = []
        for posting in soup.select("div.posting"):
            title = el_text(posting.select_one("h5"))
            a     = posting.select_one("a.posting-btn-submit") or posting.select_one("a[href]")
            link  = a.get("href", "") if a else ""
            dept  = el_text(posting.select_one(".sort-by-team"))
            loc   = el_text(posting.select_one(".sort-by-location"))
            desc  = self.get_description(link) if link else ""
            posted_date = self._date_from_job_page(link) if link else None
            jobs.append(self._make_posting(title, link, PLATFORM, dept or "N/A", loc or "N/A", desc, posted_date))
            rate_limit()
        log.info(f"[{self.company}] Lever HTML: {len(jobs)} jobs")
        return jobs

    def get_description(self, job_url: str) -> str:
        soup = fetch(job_url)
        if not soup:
            return ""
        el = soup.select_one(".section-wrapper, .content-wrapper, .posting-content")
        return clean_desc(el_text(el))

    def _date_from_job_page(self, job_url: str) -> str | None:
        soup = fetch(job_url)
        if not soup:
            return None
        time_el = soup.select_one("time[datetime]")
        if time_el:
            return parse_date(time_el.get("datetime"))
        return None

    @staticmethod
    def _parse_lever_ts(ts) -> str | None:
        """Convert Lever's Unix millisecond timestamp to YYYY-MM-DD."""
        if not ts:
            return None
        try:
            from datetime import datetime, timezone
            return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return None
