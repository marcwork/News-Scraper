"""
Hacker News Top Stories Scraper
================================
A production-ready web scraper that collects top stories from Hacker News
(news.ycombinator.com) and exports results to both CSV and JSON formats.

Author: Portfolio Demo Project
Use Case: Demonstrates web scraping, data extraction, error handling,
          rate limiting, and clean CLI-driven Python automation —
          skills directly applicable to Upwork automation/scraping jobs.

Dependencies:
    pip install requests beautifulsoup4

Usage:
    python project.py                        # scrape top 30 stories (default)
    python project.py --pages 3              # scrape 3 pages (~90 stories)
    python project.py --out-dir ./results    # custom output directory
    python project.py --pages 2 --delay 2.0 # slow down requests (polite scraping)
"""

import argparse
import csv
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

# ── Logging setup ─────────────────────────────────────────────────────────────
# Use INFO by default so the user can see progress without debug noise.
# Change to DEBUG for development / troubleshooting.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL = "https://news.ycombinator.com"
PAGE_URL = f"{BASE_URL}/?p={{page}}"   # HN uses ?p=N for pagination

# Mimic a real browser so we don't get blocked by basic bot-detection checks.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

MAX_RETRIES = 3          # how many times to retry a failed request
RETRY_BACKOFF = 2.0      # seconds to wait between retries (doubles each attempt)


# ── Data Model ────────────────────────────────────────────────────────────────
@dataclass
class Story:
    """
    Represents a single Hacker News story.
    Using a dataclass gives us free __repr__, type hints, and easy dict conversion
    via asdict() — which feeds directly into JSON/CSV export.
    """
    rank: int
    title: str
    url: str
    domain: str
    score: int
    comments: int
    hn_link: str
    scraped_at: str  # ISO-8601 timestamp for audit trail


# ── Core Scraping Logic ───────────────────────────────────────────────────────
def fetch_page(url: str, session: requests.Session, retry: int = 0) -> Optional[BeautifulSoup]:
    """
    Fetch a single URL and return a parsed BeautifulSoup object.

    Implements exponential back-off on failure so a transient network hiccup
    doesn't kill the whole job — important for long-running scrape runs.
    Returns None if all retries are exhausted.
    """
    try:
        log.debug("GET %s", url)
        response = session.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()   # raises HTTPError for 4xx / 5xx
        return BeautifulSoup(response.text, "html.parser")

    except requests.exceptions.HTTPError as e:
        log.warning("HTTP error %s for %s", e.response.status_code, url)
    except requests.exceptions.ConnectionError:
        log.warning("Connection error for %s", url)
    except requests.exceptions.Timeout:
        log.warning("Timeout for %s", url)
    except requests.exceptions.RequestException as e:
        log.warning("Request failed: %s", e)

    # Retry with exponential back-off
    if retry < MAX_RETRIES:
        wait = RETRY_BACKOFF * (2 ** retry)
        log.info("Retrying in %.1f s … (attempt %d/%d)", wait, retry + 1, MAX_RETRIES)
        time.sleep(wait)
        return fetch_page(url, session, retry + 1)

    log.error("Giving up on %s after %d retries", url, MAX_RETRIES)
    return None


def parse_stories(soup: BeautifulSoup, scraped_at: str) -> List[Story]:
    """
    Parse a single HN page and return a list of Story objects.

    HN's HTML structure uses:
      - <tr class="athing">  for the title/link row
      - <tr class="subtext"> for score / comments (the next sibling row)

    We zip both rows together so we can extract all fields in one pass.
    """
    stories: List[Story] = []

    # All story title rows have class="athing"
    thing_rows = soup.find_all("tr", class_="athing")

    for row in thing_rows:
        try:
            # ── Title & URL ──────────────────────────────────────────────────
            title_tag = row.find("span", class_="titleline")
            link_tag = title_tag.find("a") if title_tag else None
            if not link_tag:
                continue   # malformed row — skip silently

            title = link_tag.get_text(strip=True)
            url = link_tag.get("href", "")

            # HN occasionally shows internal links (e.g., "item?id=…") without domain
            if url.startswith("item?"):
                url = f"{BASE_URL}/{url}"

            # Extract the displayed domain (e.g., "github.com")
            domain_tag = title_tag.find("span", class_="sitestr")
            domain = domain_tag.get_text(strip=True) if domain_tag else "news.ycombinator.com"

            # Rank number is in a <span class="rank"> inside the same row
            rank_tag = row.find("span", class_="rank")
            rank = int(rank_tag.get_text(strip=True).rstrip(".")) if rank_tag else 0

            # ── Score & Comments (next sibling row) ──────────────────────────
            subtext_row = row.find_next_sibling("tr")
            subtext = subtext_row.find("td", class_="subtext") if subtext_row else None

            score = 0
            comments = 0
            hn_link = BASE_URL

            if subtext:
                score_tag = subtext.find("span", class_="score")
                if score_tag:
                    # "123 points" → 123
                    score = int(score_tag.get_text(strip=True).split()[0])

                # Comments link is the last <a> tag in the subtext
                links = subtext.find_all("a")
                if links:
                    last_link = links[-1]
                    hn_link = f"{BASE_URL}/{last_link.get('href', '')}"
                    comment_text = last_link.get_text(strip=True)
                    # Could be "42 comments", "1 comment", "discuss", etc.
                    if "comment" in comment_text:
                        comments = int(comment_text.split()[0])

            stories.append(Story(
                rank=rank,
                title=title,
                url=url,
                domain=domain,
                score=score,
                comments=comments,
                hn_link=hn_link,
                scraped_at=scraped_at,
            ))

        except (AttributeError, ValueError, TypeError) as e:
            # Log the parse error but keep going — one bad row shouldn't stop all
            log.debug("Skipping row due to parse error: %s", e)
            continue

    return stories


# ── Export Helpers ────────────────────────────────────────────────────────────
def save_json(stories: List[Story], path: str) -> None:
    """Serialize story list to pretty-printed JSON for easy downstream use."""
    data = [asdict(s) for s in stories]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("JSON saved → %s (%d records)", path, len(data))


def save_csv(stories: List[Story], path: str) -> None:
    """Serialize story list to CSV — useful for Excel / Google Sheets analysis."""
    if not stories:
        return
    fields = list(asdict(stories[0]).keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(s) for s in stories)
    log.info("CSV saved → %s (%d rows)", path, len(stories))


# ── Main Orchestration ────────────────────────────────────────────────────────
def scrape(pages: int = 1, delay: float = 1.0, out_dir: str = ".") -> List[Story]:
    """
    Orchestrate the full scrape: fetch N pages, parse, deduplicate, return results.

    We use a requests.Session so TCP connections are reused across pages —
    this is faster and gentler on the server than opening a new connection each time.
    """
    os.makedirs(out_dir, exist_ok=True)
    all_stories: List[Story] = []
    scraped_at = datetime.utcnow().isoformat() + "Z"

    # Session reuse: keeps cookies, pools connections, reduces overhead
    with requests.Session() as session:
        for page_num in range(1, pages + 1):
            url = PAGE_URL.format(page=page_num)
            log.info("Scraping page %d/%d — %s", page_num, pages, url)

            soup = fetch_page(url, session)
            if soup is None:
                log.warning("Skipping page %d (fetch failed)", page_num)
                continue

            stories = parse_stories(soup, scraped_at)
            log.info("  Found %d stories on page %d", len(stories), page_num)
            all_stories.extend(stories)

            # Polite delay between pages — avoid hammering the server.
            # Even 1 second makes a big difference at scale.
            if page_num < pages:
                log.debug("Sleeping %.1f s before next page …", delay)
                time.sleep(delay)

    # Deduplicate by URL in case the same story appears on multiple pages
    seen_urls: set = set()
    unique: List[Story] = []
    for s in all_stories:
        if s.url not in seen_urls:
            seen_urls.add(s.url)
            unique.append(s)

    log.info("Total unique stories collected: %d", len(unique))
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Hacker News top stories and export to CSV + JSON."
    )
    parser.add_argument(
        "--pages", type=int, default=1,
        help="Number of HN pages to scrape (default: 1, ~30 stories per page)"
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Seconds to wait between page requests (default: 1.0)"
    )
    parser.add_argument(
        "--out-dir", default=".",
        help="Output directory for CSV and JSON files (default: current dir)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable DEBUG-level logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    log.info("=== Hacker News Scraper ===")
    log.info("Pages: %d | Delay: %.1f s | Output: %s", args.pages, args.delay, args.out_dir)

    stories = scrape(pages=args.pages, delay=args.delay, out_dir=args.out_dir)

    if not stories:
        log.error("No stories collected. Check your internet connection or HN's HTML structure.")
        return

    # Timestamp-stamped filenames prevent accidental overwrites on repeated runs
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_json(stories, os.path.join(args.out_dir, f"hn_stories_{ts}.json"))
    save_csv(stories,  os.path.join(args.out_dir, f"hn_stories_{ts}.csv"))

    # Quick preview in the terminal
    print(f"\n{'─'*60}")
    print(f"{'#':>3}  {'Score':>5}  {'Cmt':>4}  Title")
    print(f"{'─'*60}")
    for s in stories[:10]:
        title_short = s.title[:45] + "…" if len(s.title) > 45 else s.title
        print(f"{s.rank:>3}  {s.score:>5}  {s.comments:>4}  {title_short}")
    if len(stories) > 10:
        print(f"  … and {len(stories) - 10} more stories")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
