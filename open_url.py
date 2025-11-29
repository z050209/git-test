import json
import argparse
import webbrowser


def main():
    parser = argparse.ArgumentParser(description="Open job URLs from JSON file with range control.")

    parser.add_argument(
        "--file", "-f",
        default="jobs.json",
        help="Path to JSON file."
    )

    # 指定范围，例如 --range 1 10
    parser.add_argument(
        "--range", "-r",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Open URLs from index START to END (1-based)."
    )

    parser.add_argument(
        "--sort",
        action="store_true",
        help="Sort by score descending."
    )

    parser.add_argument(
        "--keyword", "-k",
        type=str,
        help="Filter title by substring."
    )

    parser.add_argument(
        "--dry",
        action="store_true",
        help="Only print links, don't open browser."
    )

    args = parser.parse_args()

    # Load JSON
    with open(args.file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    # Filter keyword
    if args.keyword:
        jobs = [j for j in jobs if args.keyword.lower() in j["title"].lower()]

    # Sort by score descending
    if args.sort:
        jobs = sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)

    # Extract URLs
    urls = [j["link"] for j in jobs]

    total = len(urls)
    print(f"Total jobs: {total}")

    # If user specified range
    if args.range:
        start, end = args.range
        # convert to 0-based index
        start = max(start - 1, 0)
        end = min(end, total)
        urls = urls[start:end]
        print(f"Opening range {start+1}–{end} ({len(urls)} urls)")

    # Output
    for url in urls:
        print("->", url)
        if not args.dry:
            webbrowser.open(url)


if __name__ == "__main__":
    main()
