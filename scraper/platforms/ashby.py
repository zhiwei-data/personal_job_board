import logging

import requests

from scraper.base import BaseScraper
from scraper.models import JobPosting
from scraper.utils import HEADERS, fetch, el_text, clean_desc, parse_date, rate_limit

log = logging.getLogger(__name__)
PLATFORM = "ashby"

_GQL_QUERY = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
  ) {
    jobPostings {
      id
      title
      departmentName
      locationName
      publishedDate
    }
  }
}
"""


class AshbyScraper(BaseScraper):
    """
    Uses Ashby's GraphQL API for job listings.
    - posted_date: available as `publishedDate` in the GraphQL response.
    """

    def get_jobs(self) -> list[JobPosting]:
        slug    = self.url.rstrip("/").split("/")[-1]
        payload = {
            "operationName": "ApiJobBoardWithTeams",
            "variables":     {"organizationHostedJobsPageName": slug},
            "query":         _GQL_QUERY,
        }
        try:
            resp = requests.post(
                "https://jobs.ashbyhq.com/api/non-user-graphql",
                json=payload,
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            postings = (
                resp.json()
                .get("data", {})
                .get("jobBoard", {})
                .get("jobPostings", [])
            )
        except Exception as e:
            log.warning(f"[{self.company}] Ashby API failed: {e}")
            return []

        jobs = []
        for item in postings:
            title       = item.get("title", "N/A")
            dept        = item.get("departmentName", "N/A")
            loc         = item.get("locationName", "N/A")
            link        = f"https://jobs.ashbyhq.com/{slug}/{item.get('id', '')}"
            desc        = self.get_description(link)
            posted_date = parse_date(item.get("publishedDate"))
            jobs.append(self._make_posting(title, link, PLATFORM, dept, loc, desc, posted_date))
            rate_limit()

        log.info(f"[{self.company}] Ashby: {len(jobs)} jobs")
        return jobs

    def get_description(self, job_url: str) -> str:
        soup = fetch(job_url)
        if not soup:
            return ""
        el = soup.select_one(
            "div[class*='posting-description'], div[class*='job-description'], main"
        )
        return clean_desc(el_text(el))
