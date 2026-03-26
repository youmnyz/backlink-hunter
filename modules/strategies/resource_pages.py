"""
Strategy: Resource Page Link Building
Find curated "resources" or "useful links" pages in our niche
where our site could be listed.
"""
import time
from rich.console import Console
from modules.searcher import search, build_resource_page_queries
from modules.scraper import fetch, parse, extract_emails, extract_contact_page_url, pick_best_email
from modules.analyzer import score_opportunity, get_site_name, deduplicate_by_domain

console = Console()


def _is_resource_page(title: str, url: str, snippet: str) -> bool:
    """Quick heuristic to confirm a page is actually a resources/links page."""
    signals = [
        "resource", "useful links", "recommended", "further reading",
        "best tools", "helpful links", "reading list", "link page",
        "tools and resources", "inurl:resources", "inurl:links",
    ]
    text = (title + " " + url + " " + snippet).lower()
    return any(s in text for s in signals)


def run(config: dict) -> list[dict]:
    niche = config["niche"]["primary"]
    keywords = config["niche"].get("keywords", [])
    max_results = config["scraper"].get("max_results_per_strategy", 30)
    delay = config["scraper"].get("request_delay_seconds", 2)
    timeout = config["scraper"].get("timeout_seconds", 10)
    target_domain = config["target"]["domain"]
    target_name = config["target"].get("name", "")

    console.print("\n[bold cyan]📋 Strategy: Resource Page Link Building[/bold cyan]")

    queries = build_resource_page_queries(niche, keywords)
    raw_results: list[dict] = []
    for query in queries:
        if len(raw_results) >= max_results * 2:
            break
        console.print(f"  [dim]Searching: {query}[/dim]")
        raw_results.extend(search(query, max_results=10, pause=delay))

    seen_urls = set()
    candidates = []
    for r in raw_results:
        url = r.get("url", "")
        if not url or target_domain in url or url in seen_urls:
            continue
        seen_urls.add(url)
        if _is_resource_page(r.get("title", ""), url, r.get("snippet", "")):
            candidates.append(r)

    console.print(
        f"  Confirmed [green]{min(len(candidates), max_results)}[/green] resource pages. Enriching..."
    )

    opportunities = []
    for r in candidates[:max_results]:
        url = r["url"]
        title = r.get("title", "")
        snippet = r.get("snippet", "")

        opp = {
            "strategy": "Resource Page",
            "url": url,
            "site_name": get_site_name(url, title),
            "title": title,
            "snippet": snippet[:200],
            "contact_email": "",
            "contact_page": "",
            "score": score_opportunity(url, title, snippet, keywords),
            "status": "New",
            "notes": "Resource page — request inclusion for " + (target_name or target_domain),
        }

        resp = fetch(url, timeout=timeout)
        if resp and resp.status_code == 200:
            soup = parse(resp.text, url)
            emails = extract_emails(soup)
            contact_page = extract_contact_page_url(soup, url) or ""
            if emails:
                opp["contact_email"] = pick_best_email(emails)
            opp["contact_page"] = contact_page

            # If no email on resource page, try contact page
            if not opp["contact_email"] and contact_page:
                cresp = fetch(contact_page, timeout=timeout)
                if cresp and cresp.status_code == 200:
                    csoup = parse(cresp.text, contact_page)
                    cemails = extract_emails(csoup)
                    if cemails:
                        opp["contact_email"] = pick_best_email(cemails)

        console.print(
            f"  [green]✓[/green] {opp['site_name']:<30} score={opp['score']:>3}  "
            f"email={'✓' if opp['contact_email'] else '—'}"
        )
        opportunities.append(opp)
        time.sleep(delay)

    deduped = deduplicate_by_domain(opportunities)
    console.print(f"  [bold]Resource Page opportunities: {len(deduped)}[/bold]")
    return deduped
