"""
run.py — CLI entrypoint for the job board scraper.

Usage:
    python run.py
    python run.py --input data/input/companies.csv
    python run.py --input data/input/companies.csv --output data/output/jobs.csv
"""

import argparse
import csv
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from scraper import get_scraper, detect_platform
from scraper.models import JobPosting

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_INPUT  = "data/input/companies.csv"
DEFAULT_OUTPUT = f"data/output/jobs_{date.today()}.csv"


def load_companies(csv_path: str) -> list[dict]:
    path = Path(csv_path)
    if not path.exists():
        sys.exit(f"ERROR: Input file not found: {csv_path}")

    companies = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        required   = {"company", "career_page"}
        if not required.issubset(fieldnames):
            sys.exit(
                f"ERROR: Input CSV must have at least columns: {required}\n"
                f"Found: {fieldnames}"
            )
        for row in reader:
            companies.append(row)

    log.info(f"Loaded {len(companies)} companies from '{csv_path}'")
    return companies


def scrape_company(row: dict) -> list[JobPosting]:
    company  = row["company"].strip()
    url      = row["career_page"].strip()
    industry = row.get("industry", "N/A").strip()

    # Auto-detect platform from URL
    platform = detect_platform(url)
    log.info(f"→ [{platform.upper()}] {company}")

    scraper_cls = get_scraper(platform)
    scraper     = scraper_cls(company=company, industry=industry, url=url)

    try:
        return scraper.get_jobs()
    except Exception as e:
        log.error(f"  ✗ Failed scraping {company}: {e}")
        return []


def save_results(jobs: list[JobPosting], output_path: str) -> pd.DataFrame:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    records = [j.to_dict() for j in jobs]
    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False, encoding="utf-8")
    log.info(f"\n✅  Saved {len(df)} jobs → {output_path}")
    return df


def main():
    parser = argparse.ArgumentParser(description="Job board scraper")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="Input CSV file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV file")
    parser.add_argument("--verbose", action="store_true",   help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    companies = load_companies(args.input)

    all_jobs: list[JobPosting] = []
    for row in companies:
        jobs = scrape_company(row)
        all_jobs.extend(jobs)
        log.info(f"  {len(jobs)} jobs found | total so far: {len(all_jobs)}")

    if not all_jobs:
        log.warning("No jobs scraped. Check network connectivity and input URLs.")
        return

    df = save_results(all_jobs, args.output)

    print(f"\nPreview — first 10 results:\n")
    print(df[["company", "platform", "title", "location"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()