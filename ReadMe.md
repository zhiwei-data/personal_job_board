# Job Board Scraper

Scrapes job titles, descriptions, and links from company career pages.
Reads a CSV of companies, auto-detects the ATS platform from the URL,
and writes results to a dated CSV.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python run.py
python run.py --input data/input/companies.csv
python run.py --input data/input/companies.csv --output data/output/jobs.csv
python run.py --verbose   # debug logging
```

## Input format

`data/input/companies.csv`:

| column        | required | description                        |
|---------------|----------|------------------------------------|
| `company`     | yes      | Company name                       |
| `industry`    | no       | Industry label                     |
| `career_page` | yes      | Full URL to the job board/search   |

## Supported platforms

Platform is auto-detected from the URL. Supported:

| Platform       | Detection pattern               |
|----------------|---------------------------------|
| Greenhouse     | `boards.greenhouse.io`          |
| Lever          | `jobs.lever.co`                 |
| Ashby          | `jobs.ashbyhq.com`              |
| Workday        | `*.myworkdayjobs.com`           |
| Generic        | anything else (Playwright)      |

## Output

`data/output/jobs_YYYY-MM-DD.csv` with columns:
`company`, `industry`, `platform`, `title`, `department`, `location`, `description`, `link`

## Adding a new platform

1. Create `scraper/platforms/<name>.py` extending `BaseScraper`
2. Add one line to `scraper/registry.py`
3. Add the URL pattern to `PLATFORM_PATTERNS` in `scraper/utils.py`