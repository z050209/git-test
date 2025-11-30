"""
Stanford AI research crawler patterned after job_search.py.

This script:
- Crawls a set of Stanford AI lab/faculty seed pages.
- Extracts people, labs, and publications.
- Summarizes papers and surfaces a key diagram URL when available.
- Exposes a CLI to export JSON and a styled HTML report.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Iterable, List, Optional
from urllib.parse import urljoin

requests_spec = importlib.util.find_spec("requests")
requests = importlib.util.module_from_spec(requests_spec) if requests_spec else None  # type: ignore
if requests_spec and requests_spec.loader:
    requests_spec.loader.exec_module(requests)  # type: ignore

bs4_spec = importlib.util.find_spec("bs4")
if bs4_spec and bs4_spec.loader:
    bs4_module = importlib.util.module_from_spec(bs4_spec)
    bs4_spec.loader.exec_module(bs4_module)
    BeautifulSoup = bs4_module.BeautifulSoup  # type: ignore[attr-defined]
else:
    BeautifulSoup = None  # type: ignore

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

INCLUDE_TOPICS = [
    "nlp",
    "natural language",
    "llm",
    "multimodal",
    "generative",
    "diffusion",
    "reinforcement learning",
    "rlhf",
    "preference learning",
    "tokenization",
    "foundation model",
    "computer vision",
]

SESSION = requests.Session() if requests is not None else None
if SESSION is not None:
    SESSION.headers.update(DEFAULT_HEADERS)


@dataclass
class Paper:
    title: str
    link: str
    overview: str
    key_diagram: Optional[str] = None


@dataclass
class Person:
    name: str
    role: str
    homepage: str
    papers: List[Paper] = field(default_factory=list)


@dataclass
class Lab:
    name: str
    url: str
    topics: List[str]
    people: List[Person] = field(default_factory=list)


LAB_SEEDS = [
    Lab(
        name="Stanford AI Lab (SAIL)",
        url="https://ai.stanford.edu/people/",
        topics=["robotics", "computer vision", "nlp", "multimodal"],
    ),
    Lab(
        name="HAI Faculty", url="https://hai.stanford.edu/people/faculty", topics=["llm", "multimodal", "policy"],
    ),
    Lab(
        name="Stanford NLP Group",
        url="https://nlp.stanford.edu/people/",
        topics=["nlp", "llm", "rlhf"],
    ),
    Lab(
        name="Center for Research on Foundation Models (CRFM)",
        url="https://crfm.stanford.edu/people.html",
        topics=["foundation model", "preference learning", "tokenization"],
    ),
    Lab(
        name="Vision & Learning Lab",
        url="https://vision.stanford.edu/people.html",
        topics=["computer vision", "multimodal", "generative"],
    ),
    Lab(
        name="Stanford IRIS (Robotics)",
        url="https://iris.stanford.edu/people",
        topics=["robotics", "reinforcement learning"],
    ),
]


ROLE_HINTS = {
    "prof": "Professor",
    "faculty": "Faculty",
    "director": "Director",
    "phd": "PhD Student",
    "ph.d": "PhD Student",
    "student": "Student",
    "postdoc": "Postdoc",
    "research": "Researcher",
}


def require_bs4() -> None:
    if BeautifulSoup is None:
        raise ImportError(
            "beautifulsoup4 is required for parsing HTML. Install via `pip install -r requirements.txt`."
        )


def require_requests() -> None:
    if requests is None or SESSION is None:
        raise ImportError(
            "requests is required for crawling. Install via `pip install -r requirements.txt`."
        )


def safe_get(url: str, **kwargs) -> Optional[requests.Response]:
    require_requests()
    try:
        resp = SESSION.get(url, timeout=20, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as exc:  # pragma: no cover - network failures
        print(f"[WARN] failed to fetch {url}: {exc}")
        return None


def summarize_text(text: str, max_sentences: int = 2, max_length: int = 420) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    summary = " ".join(sentences[:max_sentences])
    if len(summary) > max_length:
        summary = summary[:max_length].rsplit(" ", 1)[0] + "…"
    return summary


def detect_role(text: str) -> str:
    lowered = text.lower()
    for hint, role in ROLE_HINTS.items():
        if hint in lowered:
            return role
    return "Member"


def extract_key_diagram_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
    if meta and meta.get("content"):
        return urljoin(base_url, meta["content"])
    img = soup.find("img")
    if img and img.get("src"):
        return urljoin(base_url, img["src"])
    return None


def extract_people_from_html(html: str, base_url: str, max_people: int = 30) -> List[Person]:
    require_bs4()
    soup = BeautifulSoup(html, "lxml")
    people: List[Person] = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        name = anchor.get_text(strip=True)
        if not name or len(name.split()) > 5:
            continue
        context = anchor.find_parent().get_text(" ", strip=True) if anchor.find_parent() else name
        role = detect_role(context)
        homepage = urljoin(base_url, anchor["href"])
        key = (name.lower(), homepage)
        if key in seen:
            continue
        people.append(Person(name=name, role=role, homepage=homepage))
        seen.add(key)
        if len(people) >= max_people:
            break
    return people


def extract_publications_from_html(html: str, base_url: str, max_papers: int = 3) -> List[Paper]:
    require_bs4()
    soup = BeautifulSoup(html, "lxml")
    papers: List[Paper] = []
    for block in soup.find_all(["li", "article", "p" ]):
        if len(papers) >= max_papers:
            break
        link = block.find("a", href=True)
        title = link.get_text(strip=True) if link else block.get_text(strip=True)
        if not title or len(title.split()) < 3:
            continue
        href = urljoin(base_url, link["href"]) if link else base_url
        overview = summarize_text(block.get_text(" ", strip=True))
        block_soup = BeautifulSoup(str(block), "lxml")
        key_diagram = extract_key_diagram_url(block_soup, base_url)
        papers.append(Paper(title=title, link=href, overview=overview, key_diagram=key_diagram))
    return papers


def crawl_lab(lab: Lab, max_people: int = 25, max_papers: int = 3) -> Lab:
    response = safe_get(lab.url)
    if not response:
        return lab
    people = extract_people_from_html(response.text, lab.url, max_people=max_people)
    for person in people:
        person_resp = safe_get(person.homepage)
        if not person_resp:
            continue
        person.papers = extract_publications_from_html(person_resp.text, person.homepage, max_papers=max_papers)
    lab.people = people
    return lab


def crawl_all(labs: Iterable[Lab], max_people: int, max_papers: int) -> List[Lab]:
    results: List[Lab] = []
    for lab in labs:
        results.append(crawl_lab(lab, max_people=max_people, max_papers=max_papers))
    return results


def build_html_page(labs: List[Lab]) -> str:
    cards = []
    for lab in labs:
        person_cards = []
        for person in lab.people:
            paper_items = []
            for paper in person.papers:
                figure_html = (
                    f'<div class="paper-figure">'
                    f"<img src='{paper.key_diagram}' alt='diagram for {paper.title}' />"  # type: ignore[str-format]
                    f"</div>" if paper.key_diagram else ""
                )
                paper_items.append(
                    f"<li><a href='{paper.link}' target='_blank'>{paper.title}</a>"
                    f"<p class='paper-overview'>{paper.overview}</p>{figure_html}</li>"
                )
            person_cards.append(
                "<div class='person-card'>"
                f"<h4><a href='{person.homepage}' target='_blank'>{person.name}</a></h4>"
                f"<p class='role'>{person.role}</p>"
                f"<ul class='papers'>{''.join(paper_items)}</ul>"
                "</div>"
            )
        cards.append(
            "<section class='lab-card'>"
            f"<h2><a href='{lab.url}' target='_blank'>{lab.name}</a></h2>"
            f"<p class='topics'>Topics: {', '.join(lab.topics)}</p>"
            f"<div class='people-grid'>{''.join(person_cards)}</div>"
            "</section>"
        )

    style = """
    <style>
    body { font-family: 'Inter', 'Helvetica', sans-serif; margin: 0; padding: 2rem; background:#f5f7fb; }
    h1 { margin-bottom: 1rem; }
    a { color: #1455cc; text-decoration: none; }
    .lab-card { background: #fff; padding: 1.5rem; margin-bottom: 1rem; border-radius: 12px; box-shadow: 0 6px 14px rgba(0,0,0,0.05); }
    .topics { color: #4a5568; margin-top: 0; }
    .people-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }
    .person-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.75rem; background:#fafbff; }
    .person-card h4 { margin: 0 0 0.25rem 0; }
    .role { color: #6b7280; margin: 0 0 0.5rem 0; }
    .papers { padding-left: 1rem; margin: 0; }
    .papers li { margin-bottom: 0.75rem; }
    .paper-overview { margin: 0.25rem 0; color:#374151; font-size: 0.95rem; }
    .paper-figure img { max-width: 100%; border-radius: 8px; margin-top: 0.35rem; }
    </style>
    """
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Stanford AI Research</title>"
        f"{style}</head><body><h1>Stanford AI Research</h1>{''.join(cards)}</body></html>"
    )


def write_outputs(labs: List[Lab], out_json: str, out_html: Optional[str]) -> None:
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump([asdict(l) for l in labs], f, ensure_ascii=False, indent=2)
    if out_html:
        os.makedirs(os.path.dirname(out_html) or ".", exist_ok=True)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(build_html_page(labs))


def run(
    max_people: int,
    max_papers: int,
    out_json: str,
    out_html: Optional[str],
    labs: Optional[Iterable[Lab]] = None,
) -> None:
    labs_to_use = list(labs) if labs is not None else LAB_SEEDS
    crawled = crawl_all(labs_to_use, max_people=max_people, max_papers=max_papers)
    write_outputs(crawled, out_json=out_json, out_html=out_html)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl Stanford AI research labs and export reports")
    parser.add_argument("--out-json", default="results/stanford_research.json", help="Output JSON path")
    parser.add_argument("--out-html", default="results/stanford_research.html", help="Output HTML path")
    parser.add_argument("--max-people", type=int, default=20, help="Max people per lab")
    parser.add_argument("--max-papers", type=int, default=3, help="Max papers per person")
    parser.add_argument("--labs", nargs="*", help="Filter labs by name keyword")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_labs = LAB_SEEDS
    if args.labs:
        selected_labs = [lab for lab in LAB_SEEDS if any(k.lower() in lab.name.lower() for k in args.labs)]
    run(
        max_people=args.max_people,
        max_papers=args.max_papers,
        out_json=args.out_json,
        out_html=args.out_html,
        labs=selected_labs,
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
