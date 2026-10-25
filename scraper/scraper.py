"""Standalone web scraper using Scrapling."""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Optional

from scrapling.fetchers import Fetcher


@dataclass
class ScrapeRule:
    name: str
    selector: str
    selector_type: str = "css"  # "css" or "xpath"
    multiple: bool = False
    attribute: Optional[str] = None


@dataclass
class ScrapeResult:
    url: str
    data: dict = field(default_factory=dict)
    error: Optional[str] = None


def extract_field(page, rule: ScrapeRule) -> list[str] | str | None:
    if rule.selector_type == "xpath":
        elements = page.xpath(rule.selector)
    else:
        elements = page.css(rule.selector)

    if rule.attribute:
        values = [el.attrib.get(rule.attribute, "") for el in elements]
    else:
        values = [el.text for el in elements if el.text]

    if rule.multiple:
        return values
    return values[0] if values else None


def scrape(url: str, rules: list[ScrapeRule], timeout: int = 30) -> ScrapeResult:
    result = ScrapeResult(url=url)
    try:
        page = Fetcher.get(url, timeout=timeout)
        result.data = {
            rule.name: extract_field(page, rule)
            for rule in rules
        }
    except Exception as exc:
        result.error = str(exc)
    return result


def scrape_many(urls: list[str], rules: list[ScrapeRule], timeout: int = 30) -> list[ScrapeResult]:
    return [scrape(url, rules, timeout) for url in urls]


def _default_rules() -> list[ScrapeRule]:
    return [
        ScrapeRule(name="title", selector="title", multiple=False),
        ScrapeRule(name="headings", selector="h1, h2, h3", multiple=True),
        ScrapeRule(name="links", selector="a", attribute="href", multiple=True),
        ScrapeRule(name="meta_description", selector='meta[name="description"]', attribute="content"),
    ]


def main():
    parser = argparse.ArgumentParser(description="Scrape one or more URLs using Scrapling.")
    parser.add_argument("urls", nargs="+", help="URLs to scrape")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--output", "-o", help="Write JSON output to this file instead of stdout")
    parser.add_argument(
        "--selector",
        "-s",
        action="append",
        metavar="NAME:CSS_SELECTOR",
        help="Custom CSS selector in the form name:selector. Repeatable.",
    )
    args = parser.parse_args()

    rules = _default_rules()
    if args.selector:
        rules = []
        for item in args.selector:
            if ":" not in item:
                print(f"Invalid selector '{item}': must be name:selector", file=sys.stderr)
                sys.exit(1)
            name, selector = item.split(":", 1)
            rules.append(ScrapeRule(name=name.strip(), selector=selector.strip(), multiple=True))

    results = scrape_many(args.urls, rules, timeout=args.timeout)
    output = [asdict(r) for r in results]

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"Results written to {args.output}")
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
