"""
Strategy: Guest Post Outreach
Search for blogs/sites that accept guest contributions in our niche.
"""
import time
from rich.console import Console
from modules.searcher import search, build_guest_post_queries
from modules.scraper import fetch, parse, extract_emails, extract_contact_page_url, get_page_title, get_domain, pick_best_email
from modules.analyzer import score_opportunity, get_site_name, deduplicate_by_domain

console = Console()


def run(config: dict) -> list[dict]:
    niche = config["niche"]["primary"]
    keywords = config["niche"].get("keywords", [])
    max_results = config["scraper"].get("max_results_per_strategy", 30)
    delay = config["scraper"].get("request_delay_seconds", 2)
    timeout = config["scraper"].get("timeout_seconds", 10)
    target_domain = config["target"]["domain"]

    console.print("\n[bold cyan]🔍 Strategy: Guest Post Outreach[/bold cyan]")

    queries = build_guest_post_queries(niche, keywords)
    raw_results: list[dict] = []

    for query in queries:
        if len(raw_results) >= max_results * 2:
            break
        console.print(f"  [dim]Searching: {query}[/dim]")
        results = search(query, max_results=10, pause=delay)
        raw_results.extend(results)

    # Filter out our own domain and duplicates
    seen_urls = set()
    filtered = []
    for r in raw_results:
        url = r.get("url", "")
        if not url or target_domain in url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        filtered.append(r)

    console.print(f"  Found [green]{len(filtered)}[/green] unique candidate pages. Enriching...")

    opportunities = []
    for r in filtered[:max_results]:
        url = r["url"]
        title = r.get("title", "")
        snippet = r.get("snippet", "")

        opp = {
            "strategy": "Guest Post",
            "url": url,
            "site_name": get_site_name(url, title),
            "title": title,
            "snippet": snippet[:200],
            "contact_email": "",
            "contact_page": "",
            "score": score_opportunity(url, title, snippet, keywords),
            "status": "New",
            "notes": "",
        }

        # Try to enrich with contact info
        resp = fetch(url, timeout=timeout)
        if resp and resp.status_code == 200:
            soup = parse(resp.text, url)
            emails = extract_emails(soup)
            contact_page = extract_contact_page_url(soup, url)
            if emails:
                opp["contact_email"] = pick_best_email(emails)
            if contact_page and not opp["contact_email"]:
                # fetch contact page for email
                opp["contact_page"] = contact_page
                cresp = fetch(contact_page, timeout=timeout)
                if cresp and cresp.status_code == 200:
                    csoup = parse(cresp.text, contact_page)
                    cemails = extract_emails(csoup)
                    if cemails:
                        opp["contact_email"] = pick_best_email(cemails)

        opportunities.append(opp)
        console.print(
            f"  [green]✓[/green] {opp['site_name']:<30} score={opp['score']:>3}  "
            f"email={'✓' if opp['contact_email'] else '—'}"
        )
        time.sleep(delay)

    deduped = deduplicate_by_domain(opportunities)
    console.print(f"  [bold]Guest Post opportunities: {len(deduped)}[/bold]")
    return deduped
