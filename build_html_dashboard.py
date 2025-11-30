#!/usr/bin/env python
"""
Build a simple HTML dashboard from OpenAlex-based Stanford AI papers JSON.

Input JSON format (produced by fetch_papers.py):

{
  "generated_at": "...",
  "source": "openalex",
  "from_date": "YYYY-MM-DD",
  "people": [
    {
      "name": "...",
      "labs": ["..."],
      "topics": ["..."],
      "status": "faculty|phd|...",
      "homepage": "https://...",
      "openalex_id": "https://openalex.org/A...",
      "works": [
        {
          "id": "https://openalex.org/W...",
          "title": "...",
          "publication_date": "YYYY-MM-DD",
          "publication_year": 2025,
          "doi": "10.XXXX/...",
          "venue": "NeurIPS",
          "open_access": "gold|...",
          "url": "https://..."
        }
      ]
    }
  ]
}

Usage:
  python build_html_dashboard.py
  python build_html_dashboard.py --in-json results/stanford_ai_papers_openalex.json \
                                 --out-html results/stanford_ai_dashboard.html
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, DefaultDict
from collections import defaultdict
import html


DEFAULT_IN_JSON = Path("results/stanford_ai_papers_openalex.json")
DEFAULT_OUT_HTML = Path("results/stanford_ai_dashboard.html")


def load_data(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_lab_index(people: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group people by lab name.
    A person can appear under multiple labs if they list multiple.
    """
    by_lab: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in people:
        labs = p.get("labs") or ["(Unspecified lab)"]
        for lab in labs:
            by_lab[lab].append(p)
    return dict(by_lab)


def status_label(status: str) -> str:
    s = (status or "").lower()
    mapping = {
        "faculty": "Faculty",
        "phd": "PhD",
        "postdoc": "Postdoc",
        "ms": "MS",
        "student": "Student",
        "other": "Researcher",
    }
    return mapping.get(s, status.title() if status else "")


def build_html(in_data: Dict[str, Any]) -> str:
    generated_at = in_data.get("generated_at", "")
    from_date = in_data.get("from_date", "")
    people = in_data.get("people", [])

    lab_index = build_lab_index(people)
    lab_names = sorted(lab_index.keys())

    # ---- Build lab filter buttons ----
    lab_filter_buttons = []
    for lab in lab_names:
        safe_lab_id = html.escape(lab).replace(" ", "_").replace("&", "_").replace("/", "_")
        lab_filter_buttons.append(
            f"<button class='lab-chip' data-lab='{safe_lab_id}' "
            f"onclick=\"filterByLab('{safe_lab_id}')\">{html.escape(lab)}</button>"
        )

    # ---- Build main lab sections ----
    lab_sections = []
    for lab in lab_names:
        people_in_lab = lab_index[lab]
        safe_lab_id = html.escape(lab).replace(" ", "_").replace("&", "_").replace("/", "_")

        person_cards = []
        for p in sorted(
                people_in_lab,
                key=lambda x: (
                    len(x.get("works") or []),
                    x.get("name", "")
                ),
                reverse=True
            ):
            name = p.get("name", "")
            homepage = p.get("homepage") or ""
            status = status_label(p.get("status", ""))
            topics = p.get("topics") or []
            works = p.get("works") or []

            topic_badges = " ".join(
                f"<span class='topic-badge'>{html.escape(t)}</span>" for t in topics
            )

            # Build works list
            work_items = []
            for w in works:
                title = w.get("title") or "(no title)"
                url = w.get("url") or w.get("id") or "#"
                pub_date = w.get("publication_date") or ""
                year = w.get("publication_year") or ""
                venue = w.get("venue") or ""
                doi = w.get("doi")
                oa = w.get("open_access") or None

                meta_parts = []
                if year:
                    meta_parts.append(str(year))
                if venue:
                    meta_parts.append(venue)
                if pub_date and pub_date != f"{year}-01-01":
                    meta_parts.append(pub_date)
                meta_str = " · ".join(meta_parts)

                oa_badge = ""
                if oa:
                    oa_badge = f"<span class='oa-badge oa-{oa}'>{oa}</span>"

                doi_html = ""
                if doi:
                    doi_html = (
                        f"<span class='doi'>DOI: "
                        f"<a href='https://doi.org/{html.escape(doi)}' target='_blank'>{html.escape(doi)}</a>"
                        f"</span>"
                    )

                work_items.append(
                    "<li class='work-item'>"
                    f"<a href='{html.escape(url)}' target='_blank' class='work-title'>{html.escape(title)}</a>"
                    f"<div class='work-meta'>{html.escape(meta_str)} {oa_badge}</div>"
                    f"{doi_html}"
                    "</li>"
                )

            works_html = (
                "<ul class='works-list'>" + "".join(work_items) + "</ul>"
                if work_items
                else "<p class='no-works'>No recent works in the selected time window.</p>"
            )

            name_html = (
                f"<a href='{html.escape(homepage)}' target='_blank'>{html.escape(name)}</a>"
                if homepage
                else html.escape(name)
            )

            person_cards.append(
                "<div class='person-card'>"
                f"<div class='person-header'>"
                f"<h3 class='person-name'>{name_html}</h3>"
                f"<span class='person-status'>{html.escape(status)}</span>"
                "</div>"
                f"<div class='person-topics'>{topic_badges}</div>"
                f"{works_html}"
                "</div>"
            )

        lab_sections.append(
            f"<section class='lab-section' id='lab-{safe_lab_id}' data-lab='{safe_lab_id}'>"
            f"<h2 class='lab-title'>{html.escape(lab)}</h2>"
            f"<div class='lab-people-grid'>{''.join(person_cards)}</div>"
            "</section>"
        )

    style = """
    <style>
    * { box-sizing: border-box; }
    body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
        margin: 0;
        padding: 0;
        background: #f5f7fb;
        color: #111827;
    }
    header {
        background: linear-gradient(135deg, #1e3a8a, #0f766e);
        color: #f9fafb;
        padding: 1.75rem 2rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.35);
        position: sticky;
        top: 0;
        z-index: 10;
    }
    header h1 {
        margin: 0;
        font-size: 1.6rem;
        letter-spacing: 0.02em;
    }
    .subtitle {
        margin-top: 0.5rem;
        font-size: 0.95rem;
        opacity: 0.9;
    }
    main {
        padding: 1.5rem 2rem 2.5rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    .lab-filter-bar {
        margin-bottom: 1rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
    }
    .lab-filter-title {
        font-weight: 600;
        margin-right: 0.5rem;
        font-size: 0.95rem;
    }
    .lab-chip {
        border-radius: 999px;
        border: 1px solid rgba(148, 163, 184, 0.7);
        padding: 0.25rem 0.75rem;
        background: #f9fafb;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.15s ease;
    }
    .lab-chip:hover {
        background: #e5e7eb;
    }
    .lab-chip.active {
        background: #1d4ed8;
        border-color: #1d4ed8;
        color: #f9fafb;
        box-shadow: 0 0 0 1px rgba(191, 219, 254, 0.9);
    }
    .lab-section {
        background: #ffffff;
        border-radius: 14px;
        padding: 1.25rem 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 5px 18px rgba(15, 23, 42, 0.08);
    }
    .lab-title {
        margin: 0 0 0.75rem 0;
        font-size: 1.2rem;
        color: #111827;
    }
    .lab-people-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1rem;
    }
    .person-card {
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 0.75rem 0.85rem 0.9rem;
        background: #f9fafb;
    }
    .person-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.5rem;
    }
    .person-name {
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
    }
    .person-name a {
        color: #1e3a8a;
        text-decoration: none;
    }
    .person-name a:hover {
        text-decoration: underline;
    }
    .person-status {
        font-size: 0.8rem;
        padding: 0.1rem 0.4rem;
        border-radius: 999px;
        background: #eef2ff;
        color: #4338ca;
        white-space: nowrap;
    }
    .person-topics {
        margin-top: 0.3rem;
        margin-bottom: 0.5rem;
    }
    .topic-badge {
        display: inline-block;
        font-size: 0.72rem;
        padding: 0.1rem 0.4rem;
        border-radius: 999px;
        background: #e0f2fe;
        color: #075985;
        margin-right: 0.25rem;
        margin-bottom: 0.15rem;
    }
    .works-list {
        list-style: none;
        padding-left: 0;
        margin: 0.25rem 0 0 0;
    }
    .work-item {
        margin-bottom: 0.5rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px dashed #e5e7eb;
    }
    .work-item:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .work-title {
        font-size: 0.9rem;
        font-weight: 500;
        color: #111827;
        text-decoration: none;
    }
    .work-title:hover {
        text-decoration: underline;
        color: #1e3a8a;
    }
    .work-meta {
        font-size: 0.78rem;
        color: #6b7280;
        margin-top: 0.15rem;
    }
    .doi {
        font-size: 0.75rem;
        color: #4b5563;
    }
    .doi a {
        color: #1d4ed8;
        text-decoration: none;
    }
    .doi a:hover {
        text-decoration: underline;
    }
    .oa-badge {
        margin-left: 0.35rem;
        font-size: 0.7rem;
        padding: 0.08rem 0.4rem;
        border-radius: 999px;
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #047857;
        background: #ecfdf5;
        text-transform: uppercase;
    }
    .no-works {
        font-size: 0.82rem;
        color: #6b7280;
        margin: 0.35rem 0 0 0;
    }
    footer {
        text-align: center;
        font-size: 0.8rem;
        color: #6b7280;
        padding: 1rem 0 1.5rem;
    }
    @media (max-width: 640px) {
        header {
            padding: 1.25rem 1rem;
        }
        main {
        padding: 1rem 1rem 2rem;
        }
    }
    </style>
    """

    script = """
    <script>
    function filterByLab(labId) {
        const sections = document.querySelectorAll('.lab-section');
        const chips = document.querySelectorAll('.lab-chip');

        if (!labId) {
            sections.forEach(s => s.style.display = '');
            chips.forEach(c => c.classList.remove('active'));
            return;
        }

        sections.forEach(sec => {
            if (sec.getAttribute('data-lab') === labId) {
                sec.style.display = '';
            } else {
                sec.style.display = 'none';
            }
        });

        chips.forEach(c => {
            if (c.getAttribute('data-lab') === labId) {
                c.classList.add('active');
            } else {
                c.classList.remove('active');
            }
        });
    }
    </script>
    """

    html_doc = (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8' />"
        "<title>Stanford AI Research Dashboard</title>"
        f"{style}"
        f"{script}"
        "</head>"
        "<body>"
        "<header>"
        "<h1>Stanford AI Research Dashboard</h1>"
        f"<div class='subtitle'>Data source: OpenAlex · From date: {html.escape(from_date)} · "
        f"Generated at: {html.escape(generated_at)}</div>"
        "</header>"
        "<main>"
        "<div class='lab-filter-bar'>"
        "<span class='lab-filter-title'>Filter by lab:</span>"
        "<button class='lab-chip' onclick=\"filterByLab('')\">All</button>"
        f"{''.join(lab_filter_buttons)}"
        "</div>"
        f"{''.join(lab_sections)}"
        "</main>"
        "<footer>Generated from OpenAlex via fetch_papers.py · This dashboard is local to your machine.</footer>"
        "</body></html>"
    )
    return html_doc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an HTML dashboard from Stanford AI papers JSON (OpenAlex)."
    )
    parser.add_argument(
        "--in-json",
        type=Path,
        default=DEFAULT_IN_JSON,
        help="Input JSON file produced by fetch_papers.py",
    )
    parser.add_argument(
        "--out-html",
        type=Path,
        default=DEFAULT_OUT_HTML,
        help="Output HTML file path",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()

    # --- Load input data ---
    in_json = args.in_json
    data = load_data(in_json)

    # derive stem
    stem = in_json.stem   # e.g. stanford_ai_papers_openalex_20251130_124422
    parent = in_json.parent

    # If user didn't manually specify out-html → auto match json
    if args.out_html == DEFAULT_OUT_HTML:
        out_html = parent / f"{stem}.html"
        print(f"[INFO] Auto output HTML => {out_html}")
    else:
        out_html = args.out_html
        print(f"[INFO] Using user-defined output => {out_html}")

    # --- Build dashboard ---
    html_doc = build_html(data)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    with out_html.open("w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"[OK] Dashboard written to: {out_html.resolve()}")


if __name__ == "__main__":
    main()
