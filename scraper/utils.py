"""
Shared utilities: HTTP fetching (requests + Playwright fallback),
platform auto-detection from URL, and text helpers.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# ── HTTP constants ─────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY = 1.5    # seconds between requests
MAX_DESC_CHARS = 2000  # truncate long descriptions

# Minimum content length to consider a requests() response usable.
# Pages below this are likely JS shells that need Playwright.
MIN_CONTENT_LENGTH = 2000


# ── Platform detection ─────────────────────────────────────────────────────────

# Order matters: more specific patterns first
PLATFORM_PATTERNS: list[tuple[str, str]] = [
    (r"boards\.greenhouse\.io",          "greenhouse"),
    (r"boards\.eu\.greenhouse\.io",      "greenhouse"),
    (r"jobs\.lever\.co",                 "lever"),
    (r"jobs\.ashbyhq\.com",              "ashby"),
    (r"\.myworkdayjobs\.com",            "workday"),
    (r"myworkday\.com",                  "workday"),
    (r"\.bamboohr\.com",                 "bamboohr"),
    (r"apply\.workable\.com",            "workable"),
    (r"jobs\.smartrecruiters\.com",      "smartrecruiters"),
    (r"smartrecruiters\.com",            "smartrecruiters"),
    (r"jobs\.jobvite\.com",              "jobvite"),
    (r"careers\.jobvite\.com",           "jobvite"),
    (r"\.recruitee\.com",                "recruitee"),
    (r"icims\.com",                      "icims"),
]


def detect_platform(url: str) -> str:
    """Return a platform key inferred from the URL, or 'generic' if unknown."""
    for pattern, platform in PLATFORM_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "generic"


# ── HTTP fetch (requests) ──────────────────────────────────────────────────────

def fetch_static(url: str, as_json: bool = False):
    """
    Fetch a URL with requests.
    Returns parsed JSON, BeautifulSoup, or None on failure.
    Does NOT raise — logs and returns None.
    """
    import requests  # local import so the module loads without requests installed

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        if as_json:
            return resp.json()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        log.debug(f"requests fetch failed: {url} — {e}")
        return None


def is_content_rich(soup: Optional[BeautifulSoup]) -> bool:
    """Return True if the soup looks like a real page, not a JS shell."""
    if soup is None:
        return False
    return len(soup.get_text(strip=True)) >= MIN_CONTENT_LENGTH


# ── Playwright fetch ───────────────────────────────────────────────────────────

def fetch_dynamic(url: str, wait_selector: Optional[str] = None, timeout: int = 15000) -> Optional[BeautifulSoup]:
    """
    Fetch a URL using Playwright (headless Chromium).
    Waits for `wait_selector` to appear if provided, else waits for networkidle.
    Returns BeautifulSoup or None on failure.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=HEADERS["User-Agent"],
                java_script_enabled=True,
            )
            page.goto(url, timeout=timeout)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout)
                except PWTimeout:
                    log.debug(f"Selector '{wait_selector}' not found on {url}, continuing anyway")
            else:
                page.wait_for_load_state("networkidle", timeout=timeout)

            html = page.content()
            browser.close()
            return BeautifulSoup(html, "lxml")
    except Exception as e:
        log.warning(f"Playwright fetch failed: {url} — {e}")
        return None


def fetch(url: str, force_dynamic: bool = False, wait_selector: Optional[str] = None) -> Optional[BeautifulSoup]:
    """
    Two-tier fetch:
      1. Try requests (fast, no browser).
      2. If content looks like a JS shell, fall back to Playwright.
    Set force_dynamic=True to skip straight to Playwright.
    """
    if not force_dynamic:
        soup = fetch_static(url)
        if is_content_rich(soup):
            return soup
        log.debug(f"Static fetch thin for {url}, retrying with Playwright")

    time.sleep(REQUEST_DELAY)
    return fetch_dynamic(url, wait_selector=wait_selector)


# ── Text helpers ───────────────────────────────────────────────────────────────

def el_text(el) -> str:
    """Safe .get_text() from a possibly-None BeautifulSoup element."""
    return el.get_text(separator=" ", strip=True) if el else ""


def clean_desc(raw: str) -> str:
    """Collapse whitespace and truncate to MAX_DESC_CHARS."""
    return " ".join(raw.split())[:MAX_DESC_CHARS]


def rate_limit():
    """Sleep between requests to be a polite crawler."""
    time.sleep(REQUEST_DELAY)


# ── Date helpers ───────────────────────────────────────────────────────────────

# Common date formats seen across ATS platforms
_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",     # 2024-03-15T10:30:00
    "%Y-%m-%dT%H:%M:%SZ",    # 2024-03-15T10:30:00Z
    "%Y-%m-%dT%H:%M:%S.%f",  # 2024-03-15T10:30:00.000
    "%Y-%m-%d",               # 2024-03-15
    "%B %d, %Y",              # March 15, 2024
    "%b %d, %Y",              # Mar 15, 2024
    "%d %B %Y",               # 15 March 2024
    "%d %b %Y",               # 15 Mar 2024
    "%m/%d/%Y",               # 03/15/2024
    "%d/%m/%Y",               # 15/03/2024
]


def parse_date(raw: Optional[str]) -> Optional[str]:
    """
    Try to parse a raw date string into ISO format (YYYY-MM-DD).
    Returns None if raw is empty or unparseable.
    """
    from datetime import datetime

    if not raw:
        return None
    raw = raw.strip()
    # Strip trailing timezone offsets like +00:00 or -05:00, and trailing Z
    raw_clean = re.sub(r"[+-]\d{2}:\d{2}$", "", raw).rstrip("Z").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw_clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    log.debug(f"Could not parse date: '{raw}'")
    return None
