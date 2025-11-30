# Job search helpers

This repository contains two small utilities:

- `job_search.py` scrapes AI/ML research-focused roles from a curated list of company and university career pages, scores them, and prints a sorted list.
- `email.py` formats the collected jobs and sends them via SMTP so results can be delivered to an inbox.

## Running the scraper

The scraper performs many network requests, so expect it to take a while:

```bash
python job_search.py
```

## Stanford research crawler

`stanford_research_agent.py` crawls Stanford AI labs, gathers people and recent papers, summarizes them, and writes JSON plus a
styled HTML report. Run it locally with:

```bash
python stanford_research_agent.py --out-json results/stanford_research.json --out-html results/stanford_research.html
```

The scheduled GitHub Actions workflow (`.github/workflows/stanford_research.yml`) runs the crawler every three days and uploads
the newest report as an artifact.


If you only need a one-off send with environment variables, use the convenience helper:

```python
from email import send_job_results_from_env
send_job_results_from_env(sorted_jobs, "recipient@example.com")
```
