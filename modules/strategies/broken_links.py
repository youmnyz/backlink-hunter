"""
Strategy: Broken Link Building
Find pages in our niche that contain broken outbound links.
We can then reach out and offer our content as a replacement.
"""
import time
from urllib.parse import urlparse
from rich.console import Console
from modules.searcher import search, build_broken_link_queries
from modules.scraper import (
    fetch, parse, extract_links, extract_emails,
    extract_contact_page_url, check_url_status, get_domain
)
from modules.analyzer import score_opportunity, get_site_name, deduplicate_by_domain

console = Console()

# HTTP status codes we treat as "broken"
BROKEN_STATUSES = {0, 404, 410, 403, 500, 503}


def _is_external(href: str, host_domain: str) -> bool:
    try:
        netloc = urlparse(href).netloc.lower().replace("www.", "")
        return netloc and netloc != host_domain
    except Exception:
        return False


def run(config: dict) -> list[dict]:
    niche = config["niche"]["primary"]
    keywords = config["niche"].get("keywords", [])
    max_results = config["scraper"].get("max_results_per_strategy", 30)
    delay = config["scraper"].get("request_delay_seconds", 2)
    timeout = config["scraper"].get("timeout_seconds", 10)
    check_broken = config["scraper"].get("check_broken_links", True)
    target_domain = config["target"]["domain"]

    console.print("\n[bold cyan]🔗 Strategy: Broken Link Building[/bold cyan]")

    queries = build_broken_link_queries(niche, keywords)
    raw_results: list[dict] = []
    for query in queries:
        if len(raw_results) >= max_results * 3:
            break
        console.print(f"  [dim]Searching: {query}[/dim]")
        raw_results.extend(search(query, max_results=10, pause=delay))

    # Deduplicate candidate pages
    seen_urls = set()
    candidate_pages = []
    for r in raw_results:
        url = r.get("url", "")
        if not url or target_domain in url or url in seen_urls:
            continue
        seen_urls.add(url)
        candidate_pages.append(r)

    console.print(
        f"  Scanning [green]{min(len(candidate_pages), max_results)}[/green] pages "
        f"for broken outbound links..."
    )

    opportunities = []
    for page in candidate_pages[:max_results]:
        page_url = page["url"]
        host = get_domain(page_url)

        resp = fetch(page_url, timeout=timeout)
        if not resp or resp.status_code != 200:
            time.sleep(delay)
            continue

        soup = parse(resp.text, page_url)
        all_links = extract_links(soup, page_url)
        external_links = [l for l in all_links if _is_external(l["href"], host)]

        if not check_broken:
            # If we skip checking, report the page as a general outreach target
            if external_links:
                opp = _make_opportunity(page, page_url, external_links[0]["href"],
                                        "unchecked", keywords)
                if opp:
                    opportunities.append(opp)
            time.sleep(delay)
            continue

        # Check each outbound link
        broken_found = False
        for link in external_links[:20]:  # cap per-page checks
            href = link["href"]
            status = check_url_status(href, timeout=6)
            if status in BROKEN_STATUSES:
                console.print(
                    f"  [red]✗[/red] Broken link found on [bold]{host}[/bold]: "
                    f"{link['text'][:40]} → {href[:60]} [dim](HTTP {status})[/dim]"
                )
                emails = extract_emails(soup)
                contact_page = extract_contact_page_url(soup, page_url) or ""
                opp = {
                    "strategy": "Broken Link",
                    "url": page_url,
                    "site_name": get_site_name(page_url, page.get("title", "")),
                    "title": page.get("title", ""),
                    "snippet": f"Broken link: '{link['text']}' → {href}",
                    "broken_link_url": href,
                    "broken_link_text": link["text"],
                    "contact_email": emails[0] if emails else "",
                    "contact_page": contact_page,
                    "score": score_opportunity(page_url, page.get("title", ""),
                                               page.get("snippet", ""), keywords) + 15,
                    "status": "New",
                    "notes": f"Broken outbound link (HTTP {status}): {href}",
                }
                opportunities.append(opp)
                broken_found = True

            time.sleep(0.5)  # brief pause between link checks

        if not broken_found:
            console.print(f"  [dim]No broken links on {host}[/dim]")

        time.sleep(delay)

    deduped = deduplicate_by_domain(opportunities)
    console.print(f"  [bold]Broken Link opportunities: {len(deduped)}[/bold]")
    return deduped


def _make_opportunity(page, page_url, broken_href, status_str, keywords):
    return {
        "strategy": "Broken Link",
        "url": page_url,
        "site_name": get_site_name(page_url, page.get("title", "")),
        "title": page.get("title", ""),
        "snippet": page.get("snippet", "")[:200],
        "broken_link_url": broken_href,
        "broken_link_text": "",
        "contact_email": "",
        "contact_page": "",
        "score": score_opportunity(page_url, page.get("title", ""),
                                   page.get("snippet", ""), keywords),
        "status": "New",
        "notes": f"Potential broken link target: {broken_href}",
    }
