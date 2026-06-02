# Hacker News Top Stories Scraper — Portfolio Project

## Project Overview

This project showcases a **production-ready Python web scraper** built for real-world reliability. It collects top stories from Hacker News (news.ycombinator.com) — one of the tech world's most active link aggregators — and exports the data to both **CSV** and **JSON** formats, ready for analysis, dashboards, or downstream pipelines.

## What This Demonstrates

If you need a web scraping or automation specialist, here's what this project shows I can deliver:

**Robust Data Extraction.** The scraper parses Hacker News's HTML structure to extract story titles, URLs, domains, vote scores, and comment counts — all the fields that matter for real analysis. It handles edge cases like internal HN links, missing fields, and malformed rows without crashing.

**Production-Grade Error Handling.** Network calls include automatic retry logic with exponential back-off — so a single timeout doesn't kill a long-running job. Every exception is caught, logged, and handled gracefully.

**Polite, Responsible Scraping.** Configurable rate limiting between requests, realistic browser headers, and connection session reuse ensure the scraper is both fast and respectful of the target server — a requirement for any professional automation work.

**Clean, Maintainable Code.** The project uses Python dataclasses for the data model, type hints throughout, structured logging, and a clean separation between fetch → parse → export stages. Anyone can read, extend, or maintain it.

**Flexible CLI Interface.** Users can control page depth, request delay, and output directory via command-line arguments — no code changes needed for common configuration.

## Technical Stack

- **Language:** Python 3.8+
- **Libraries:** `requests`, `BeautifulSoup4`
- **Output Formats:** JSON, CSV
- **Patterns:** Retry/back-off, session reuse, dataclasses, argparse CLI

## Why Hire Me?

Whether you need a scraper for lead generation, price monitoring, competitor tracking, or data pipeline feeding — this project reflects the quality I bring to every engagement. I write code that runs in production, not just in demos.

*Available for contracts. Let's discuss your requirements.*
