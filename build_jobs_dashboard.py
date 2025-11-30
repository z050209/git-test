#!/usr/bin/env python
"""
Build an HTML job dashboard from a jobs.json-style file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict
import html


def load_jobs(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_company_index(jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_company: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for job in jobs:
        company = job.get("company") or "(Unknown company)"
        by_company[company].append(job)

    for c in by_company:
        by_company[c] = sorted(
            by_company[c],
            key=lambda j: j.get("score", 0),
            reverse=True,
        )
    return dict(by_company)


def build_html(jobs: List[Dict[str, Any]]) -> str:
    by_company = build_company_index(jobs)
    company_names = sorted(by_company.keys())

    chips = []
    for company in company_names:
        safe_id = (
            html.escape(company)
            .replace(" ", "_")
            .replace("&", "_")
            .replace("/", "_")
        )
        chips.append(
            f"<button class='company-chip' data-company='{safe_id}' "
            f"onclick=\"filterByCompany('{safe_id}')\">{html.escape(company)}</button>"
        )

    sections = []
    for company in company_names:
        safe_id = (
            html.escape(company)
            .replace(" ", "_")
            .replace("&", "_")
            .replace("/", "_")
        )
        jobs_in_company = by_company[company]

        job_cards = []
        for job in jobs_in_company:
            title = job.get("title") or "(no title)"
            location = job.get("location") or ""
            link = job.get("link") or "#"
            source = job.get("source") or ""
            score = job.get("score", 0)
            remote = job.get("remote", False)

            remote_label = "Onsite / Hybrid"
            remote_class = "remote-onsite"
            if isinstance(remote, bool) and remote:
                remote_label = "Remote possible"
                remote_class = "remote-yes"

            job_cards.append(
                "<div class='job-card'>"
                f"<h3 class='job-title'><a href='{html.escape(link)}' target='_blank'>{html.escape(title)}</a></h3>"
                "<div class='job-meta'>"
                f"<span class='job-location'>{html.escape(location)}</span>"
                f"<span class='job-score'>Score: {score}</span>"
                f"<span class='job-source'>Source: {html.escape(source)}</span>"
                f"<span class='job-remote {remote_class}'>{remote_label}</span>"
                "</div>"
                "</div>"
            )

        sections.append(
            f"<section class='company-section' id='company-{safe_id}' data-company='{safe_id}'>"
            f"<h2 class='company-title'>{html.escape(company)}</h2>"
            f"<div class='jobs-grid'>{''.join(job_cards)}</div>"
            "</section>"
        )

    style = """
    <style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        padding: 0;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
        background: #f5f7fb;
        color: #111827;
    }
    header {
        background: linear-gradient(135deg, #1e3a8a, #4f46e5);
        color: #f9fafb;
        padding: 1.6rem 2rem;
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.3);
        position: sticky;
        top: 0;
        z-index: 10;
    }
    header h1 {
        margin: 0;
        font-size: 1.6rem;
    }
    main { padding: 1.5rem 2rem; max-width: 1100px; margin: 0 auto; }
    .filter-bar { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
    .company-chip {
        border-radius: 999px;
        border: 1px solid #9ca3af;
        padding: 0.3rem 0.9rem;
        background: #fff;
        cursor: pointer;
    }
    .jobs-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px,1fr));
        gap: 1rem;
    }
    .job-card {
        border: 1px solid #e5e7eb;
        padding: 0.75rem;
        border-radius: 10px;
        background: #fafafa;
    }
    .job-title { margin: 0 0 0.3rem 0; font-size: 1rem; }
    .job-meta { font-size: 0.85rem; display: flex; flex-wrap: wrap; gap: 0.3rem; }
    .job-location { background: #eff6ff; padding: 0.2rem 0.4rem; border-radius: 6px; }
    .job-score { background: #ecfdf5; padding: 0.2rem 0.4rem; border-radius: 6px; }
    .job-source { background: #fef3c7; padding: 0.2rem 0.4rem; border-radius: 6px; }
    </style>
    """

    script = """
    <script>
    function filterByCompany(companyId) {
        const sections = document.querySelectorAll('.company-section');
        const chips = document.querySelectorAll('.company-chip');

        if (!companyId) {
            sections.forEach(s => s.style.display = '');
            chips.forEach(c => c.classList.remove('active'));
            return;
        }
        sections.forEach(sec => {
            sec.style.display = (sec.getAttribute('data-company') === companyId) ? '' : 'none';
        });
        chips.forEach(c => {
            c.classList.toggle('active', c.getAttribute('data-company') === companyId);
        });
    }
    </script>
    """

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Job Dashboard</title>"
        f"{style}{script}"
        "</head><body>"
        "<header><h1>Job Opportunities Dashboard</h1></header>"
        "<main>"
        "<div class='filter-bar'>"
        "<button class='company-chip' onclick=\"filterByCompany('')\">All</button>"
        f"{''.join(chips)}"
        "</div>"
        f"{''.join(sections)}"
        "</main></body></html>"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build job HTML dashboard")
    parser.add_argument("--in-json", type=Path, required=True, help="Input JSON file (job list)")
    parser.add_argument("--out-html", type=Path, default=None, help="Output HTML file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    jobs = load_jobs(args.in_json)

    # 自动生成 HTML 文件名 = json 名字 + .html
    if args.out_html is None:
        out_html = args.in_json.with_suffix(".html")
    else:
        out_html = args.out_html

    html_doc = build_html(jobs)
    out_html.parent.mkdir(parents=True, exist_ok=True)

    with out_html.open("w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"[OK] Dashboard saved to {out_html.resolve()}")


if __name__ == "__main__":
    main()
