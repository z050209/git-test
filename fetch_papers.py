#!/usr/bin/env python
"""
Fetch recent papers for Stanford AI people using the OpenAlex API.

Pipeline:
1. Load people from data/stanford_people.json.
2. For each person:
   - Resolve their OpenAlex author ID (if not already in ids.openalex).
   - Fetch their recent works from OpenAlex /works endpoint.
3. Save a compact JSON summary to results/stanford_ai_papers_openalex.json.

Usage (examples):
  python fetch_papers.py
  python fetch_papers.py --from-date 2025-01-01 --max-papers 5
  python fetch_papers.py --people-json data/stanford_people.json --out-json results/stanford_ai_papers.json

OpenAlex best practice:
  - Set environment variable OPENALEX_MAILTO to your email.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://api.openalex.org"
DEFAULT_PEOPLE_JSON = Path("data/stanford_people.json")
DEFAULT_OUT_JSON = Path("results/stanford_ai_papers_openalex.json")


# ---------- Data classes ----------


@dataclass
class Work:
    id: str
    title: str
    publication_date: Optional[str]
    publication_year: Optional[int]
    doi: Optional[str]
    venue: Optional[str]
    open_access: Optional[str]
    url: Optional[str]


@dataclass
class PersonPapers:
    name: str
    labs: List[str]
    topics: List[str]
    status: str
    homepage: str
    openalex_id: Optional[str]
    works: List[Work]


# ---------- OpenAlex helpers ----------


def get_mailto() -> str:
    """Get mailto param for OpenAlex (recommended by docs)."""
    mailto = os.getenv("OPENALEX_MAILTO", "").strip()
    if not mailto:
        # You can set OPENALEX_MAILTO in your environment to something like "youremail@example.com".
        return ""
    return mailto


def openalex_get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """GET request to OpenAlex with basic error handling."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    mailto = get_mailto()
    if mailto:
        params = {**params, "mailto": mailto}

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def resolve_openalex_author_id(name: str, affiliation_hint: str = "Stanford") -> Optional[str]:
    """
    Resolve an author's OpenAlex ID given their name.

    Strategy:
      - Search /authors with ?search=<name>.
      - Prefer results whose last_known_institution.display_name contains 'Stanford' (case-insensitive).
      - Fallback to the top search result if nothing matches Stanford.

    Returns:
      OpenAlex author ID URL string (e.g. "https://openalex.org/A5023888391") or None.
    """
    try:
        data = openalex_get("authors", {"search": name, "per-page": 25})
    except Exception as exc:
        print(f"[WARN] Failed to search OpenAlex authors for '{name}': {exc}")
        return None

    results = data.get("results", [])
    if not results:
        print(f"[INFO] No OpenAlex author found for '{name}'")
        return None

    # Try to find a Stanford-affiliated author first
    aff_lower = affiliation_hint.lower()
    for author in results:
        inst = author.get("last_known_institution") or {}
        display_name = (inst.get("display_name") or "").lower()
        if aff_lower in display_name:
            return author.get("id")

    # Fallback: take the first result
    return results[0].get("id")


def fetch_works_for_author(
    author_id: str,
    from_date: str,
    max_papers: int = 10,
) -> List[Work]:
    """
    Fetch recent works for a given OpenAlex author ID.

    Uses /works?filter=authorships.author.id:ID,from_publication_date:YYYY-MM-DD
    Sorted by publication_date desc, limited by max_papers.
    """
    if not author_id:
        return []

    # OpenAlex IDs can come as full URL like "https://openalex.org/Axxxx"
    # For filters, they accept just the Axxxx part or full URL. We'll pass the full ID.
    filters = f"authorships.author.id:{author_id},from_publication_date:{from_date}"

    params = {
        "filter": filters,
        "sort": "publication_date:desc",
        "per-page": max_papers,
    }

    try:
        data = openalex_get("works", params)
    except Exception as exc:
        print(f"[WARN] Failed to fetch works for author {author_id}: {exc}")
        return []

    results = data.get("results", [])
    works: List[Work] = []
    for w in results:
        # Extract key fields
        work_id = w.get("id")
        title = w.get("display_name") or ""
        pub_date = w.get("publication_date")
        pub_year = w.get("publication_year")
        doi = w.get("doi")
        # Venue is under primary_location or host_venue depending on version
        venue = None
        primary_location = w.get("primary_location") or {}
        host_venue = primary_location.get("source") or w.get("host_venue") or {}
        if isinstance(host_venue, dict):
            venue = host_venue.get("display_name")

        open_access_status = None
        oa = w.get("open_access") or {}
        if isinstance(oa, dict):
            open_access_status = oa.get("oa_status")

        # URL to view the paper (prefer primary_location.landing_page_url)
        url = primary_location.get("landing_page_url") or w.get("id")

        works.append(
            Work(
                id=work_id,
                title=title,
                publication_date=pub_date,
                publication_year=pub_year,
                doi=doi,
                venue=venue,
                open_access=open_access_status,
                url=url,
            )
        )

    return works


# ---------- People loading & orchestration ----------


def load_people(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_papers_for_people(
    people_json: Path,
    from_date: str,
    max_papers: int,
    sleep_sec: float = 0.5,
) -> List[PersonPapers]:
    people_data = load_people(people_json)
    results: List[PersonPapers] = []

    for p in people_data:
        name = p.get("name", "")
        status = p.get("status", "")
        labs = p.get("labs", []) or []
        topics = p.get("topics", []) or []
        homepage = p.get("homepage", "")
        ids = p.get("ids", {}) or {}
        openalex_id = ids.get("openalex")

        print(f"\n[INFO] Processing {name} ...")

        # Resolve author ID if missing
        if not openalex_id:
            openalex_id = resolve_openalex_author_id(name, affiliation_hint="Stanford")
            if openalex_id:
                print(f"  -> Resolved OpenAlex ID: {openalex_id}")
            else:
                print("  -> Could not resolve OpenAlex ID, skipping works.")
                results.append(
                    PersonPapers(
                        name=name,
                        labs=labs,
                        topics=topics,
                        status=status,
                        homepage=homepage,
                        openalex_id=None,
                        works=[],
                    )
                )
                continue

        # Fetch works
        works = fetch_works_for_author(openalex_id, from_date=from_date, max_papers=max_papers)
        print(f"  -> Retrieved {len(works)} works since {from_date}")

        results.append(
            PersonPapers(
                name=name,
                labs=labs,
                topics=topics,
                status=status,
                homepage=homepage,
                openalex_id=openalex_id,
                works=works,
            )
        )

        # Be nice to the API
        time.sleep(sleep_sec)

    return results


def save_results(out_path: Path, people_papers: List[PersonPapers], from_date: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "source": "openalex",
        "from_date": from_date,
        "people": [asdict(pp) for pp in people_papers],
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Saved results to {out_path}")


# ---------- CLI ----------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch recent papers for Stanford AI people using OpenAlex."
    )
    parser.add_argument(
        "--people-json",
        type=Path,
        default=DEFAULT_PEOPLE_JSON,
        help="Path to stanford_people.json",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=DEFAULT_OUT_JSON,
        help="Output JSON path for collected papers",
    )
    parser.add_argument(
        "--from-date",
        type=str,
        default=None,
        help="Only include works with publication_date >= this date (YYYY-MM-DD). "
             "Default: 365 days ago from today.",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=10,
        help="Max number of papers per person",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=0.5,
        help="Sleep seconds between API calls (be nice to OpenAlex).",
    )
    return parser.parse_args()
def main() -> None:
    args = parse_args()

    if args.from_date is None:
        # 默认看最近一年
        one_year_ago = dt.date.today() - dt.timedelta(days=365)
        from_date = one_year_ago.isoformat()
    else:
        from_date = args.from_date

    print(f"[INFO] Using from_date = {from_date}")
    print(f"[INFO] Loading people from {args.people_json}")

    # ---------- 自动生成带 timestamp 的文件名 ----------
    out_path = args.out_json
    if out_path == DEFAULT_OUT_JSON:  # only auto timestamp when user uses default
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"stanford_ai_papers_openalex_{ts}.json"
        out_path = Path("results") / out_name
        print(f"[INFO] Auto output filename => {out_path}")
    else:
        print(f"[INFO] Using custom output => {out_path}")

    # ---------- 执行抓取 ----------
    people_papers = collect_papers_for_people(
        people_json=args.people_json,
        from_date=from_date,
        max_papers=args.max_papers,
        sleep_sec=args.sleep_sec,
    )

    save_results(out_path, people_papers, from_date=from_date)

if __name__ == "__main__":
    main()
