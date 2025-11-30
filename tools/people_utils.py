import json
from pathlib import Path
from typing import List, Dict, Any

PEOPLE_PATH = Path("data/stanford_people.json")


def load_people(path: Path = PEOPLE_PATH) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def print_summary(people: List[Dict[str, Any]]) -> None:
    print(f"Total people: {len(people)}")
    by_lab = {}
    for p in people:
        for lab in p.get("labs", []):
            by_lab.setdefault(lab, 0)
            by_lab[lab] += 1
    print("\nBy lab:")
    for lab, cnt in sorted(by_lab.items(), key=lambda x: -x[1]):
        print(f"  {lab}: {cnt}")

    print("\nCore people:")
    for p in people:
        if "core" in p.get("tags", []):
            print(f" - {p['name']} ({', '.join(p.get('labs', []))})")


if __name__ == "__main__":
    people = load_people()
    print_summary(people)
