import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.base import BaseScraper
from scraper.models import JobPosting
from scraper.utils import fetch_static, fetch, el_text, clean_desc, parse_date, rate_limit

log = logging.getLogger(__name__)
PLATFORM = "greenhouse"


class GreenhouseScraper(BaseScraper):
    """
    Uses Greenhouse's public JSON API for job listings.
    - posted_date: available as `updated_at` in the API response.
    Falls back to HTML scraping if the API is unavailable.
    """

    def get_jobs(self) -> list[JobPosting]:
        slug = self.url.rstrip("/").split("/")[-1]
        base = (
            "https://boards.eu.greenhouse.io"
            if "eu.greenhouse" in self.url
            else "https://boards.greenhouse.io"
        )
        api_url = f"{base}/v1/boards/{slug}/jobs?content=true"

        data = fetch_static(api_url, as_json=True)
        if data and "jobs" in data:
            return self._from_api(data["jobs"], base)

        log.debug(f"[{self.company}] Greenhouse API unavailable, falling back to HTML")
        return self._from_html(base)

    def _from_api(self, items: list, base: str) -> list[JobPosting]:
        jobs = []
        for item in items:
            title       = item.get("title", "N/A")
            link        = item.get("absolute_url", "")
            dept        = (item.get("departments") or [{}])[0].get("name", "N/A")
            loc         = item.get("location", {}).get("name", "N/A")
            desc        = clean_desc(
                BeautifulSoup(item.get("content", ""), "lxml").get_text(" ", strip=True)
            )
            posted_date = parse_date(item.get("updated_at"))
            jobs.append(self._make_posting(title, link, PLATFORM, dept, loc, desc, posted_date))
            rate_limit()
        log.info(f"[{self.company}] Greenhouse API: {len(jobs)} jobs")
        return jobs

    def _from_html(self, base: str) -> list[JobPosting]:
        soup = fetch(self.url)
        if not soup:
            return []
        jobs = []
        for section in soup.select("section.level-0"):
            dept = el_text(section.select_one("h3"))
            for opening in section.select("div.opening"):
                a = opening.select_one("a")
                if not a:
                    continue
                title = el_text(a)
                link  = urljoin(base, a.get("href", ""))
                loc   = el_text(opening.select_one(".location"))
                desc  = self.get_description(link)
                # No date available in HTML listing; may exist on job page
                posted_date = self._date_from_job_page(link)
                jobs.append(self._make_posting(title, link, PLATFORM, dept or "N/A", loc or "N/A", desc, posted_date))
                rate_limit()
        log.info(f"[{self.company}] Greenhouse HTML: {len(jobs)} jobs")
        return jobs

    def get_description(self, job_url: str) -> str:
        soup = fetch(job_url)
        if not soup:
            return ""
        el = soup.select_one("#content, .job__description, .job-description")
        return clean_desc(el_text(el))

    def _date_from_job_page(self, job_url: str) -> str | None:
        """Try to extract date from a <time> element on the individual job page."""
        soup = fetch(job_url)
        if not soup:
            return None
        time_el = soup.select_one("time[datetime]")
        if time_el:
            return parse_date(time_el.get("datetime"))
        return None
