# Job search helpers

This repository contains two small utilities:

- `job_search.py` scrapes AI/ML research-focused roles from a curated list of company and university career pages, scores them, and prints a sorted list.
- `email.py` formats the collected jobs and sends them via SMTP so results can be delivered to an inbox.

## Running the scraper

The scraper performs many network requests, so expect it to take a while:

```bash
python job_search.py
```

## Emailing the results

`email.py` is intentionally decoupled from the scraper. A typical workflow is to import both modules and send the sorted results after collection:

```python
from job_search import collect_all_jobs, score_job
from email import SMTPConfig, send_job_results

jobs = collect_all_jobs()
for job in jobs:
    job["score"] = score_job(job)

sorted_jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)
config = SMTPConfig.from_env()
send_job_results(sorted_jobs, "recipient@example.com", config)
```

The SMTP settings are loaded from environment variables when using `SMTPConfig.from_env()`:

- `SMTP_HOST`
- `SMTP_PORT` (defaults to 587)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS` (defaults to true)
- `SMTP_FROM_ADDRESS` (defaults to the username when omitted)

If you only need a one-off send with environment variables, use the convenience helper:

```python
from email import send_job_results_from_env
send_job_results_from_env(sorted_jobs, "recipient@example.com")
```
