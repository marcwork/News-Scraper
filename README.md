# Portfolio Project — Hacker News Top Stories Scraper

| Field | Detail |
|-------|--------|
| **Project Title** | Hacker News Top Stories Scraper |
| **Tech Tags** | `Python` `requests` `BeautifulSoup4` `Web Scraping` `CSV` `JSON` `CLI` `Automation` |
| **One-Line Summary** | Production-ready Python scraper that extracts Hacker News top stories with retry logic, rate limiting, and dual CSV/JSON export — deployable out of the box. |

## Files

| File | Description |
|------|-------------|
| `project.py` | Full scraper implementation (315 lines, runnable) |
| `description.md` | Upwork portfolio description for client-facing display |

## Quick Start

```bash
pip install requests beautifulsoup4
python project.py --pages 2 --delay 1.0 --out-dir ./results
```

## Key Features

- ✅ Retry with exponential back-off
- ✅ Polite rate limiting between requests
- ✅ Structured logging (INFO / DEBUG)
- ✅ Type-annotated, dataclass-based data model
- ✅ CSV + JSON dual export with timestamped filenames
- ✅ Argparse CLI — zero code changes needed for configuration
- ✅ Deduplication across pages
