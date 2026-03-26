"""
Strategy: Competitor Backlink Mining
Find sites that mention / link to competitors but not our site.
These are warm prospects — they already link in our niche.
"""
import time
from rich.console import Console
from modules.searcher import search, build_competitor_mention_queries
from modules.scraper import fetch, parse, extract_emails, extract_contact_page_url, get_domain, pick_best_email
from modules.analyzer import score_opportunity, get_site_name, deduplicate_by_domain, is_same_domain

console = Console()


def run(config: dict) -> list[dict]:
    competitors = config.get("competitors", [])
    niche = config["niche"]["primary"]
    keywords = config["niche"].get("keywords", [])
    max_results = config["scraper"].get("max_results_per_strategy", 30)
    delay = config["scraper"].get("request_delay_seconds", 2)
    timeout = config["scraper"].get("timeout_seconds", 10)
    target_domain = config["target"]["domain"]
    target_url = config["target"]["url"]

    console.print("\n[bold cyan]🕵️  Strategy: Competitor Backlink Mining[/bold cyan]")

    if not competitors:
        console.print("  [yellow]No competitors configured — skipping this strategy.[/yellow]")
        return []

    all_raw: list[dict] = []
    for comp in competitors:
        cdomain = comp.get("domain", "")
        cname = comp.get("name", cdomain)
        if not cdomain:
            continue
        console.print(f"  Mining competitor: [bold]{cname}[/bold] ({cdomain})")
        queries = build_competitor_mention_queries(cdomain, niche)
        for query in queries:
            if len(all_raw) >= max_results * 3:
                break
            console.print(f"    [dim]Searching: {query}[/dim]")
            results = search(query, max_results=10, pause=delay)
            for r in results:
                r["_competitor"] = cname  # tag which competitor was found
            all_raw.extend(results)

    # Deduplicate and filter
    seen_urls = set()
    candidates = []
    for r in all_raw:
        url = r.get("url", "")
        if not url or url in seen_urls:
            continue
        # Skip if it IS a competitor page or our own
        is_competitor_page = any(
            comp.get("domain", "") in url for comp in competitors
        )
        if is_competitor_page or target_domain in url:
            continue
        seen_urls.add(url)
        candidates.append(r)

    console.print(
        f"  Found [green]{min(len(candidates), max_results)}[/green] pages linking to competitors. Enriching..."
    )

    opportunities = []
    for r in candidates[:max_results]:
        url = r["url"]
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        competitor_mentioned = r.get("_competitor", "a competitor")

        base_score = score_opportunity(url, title, snippet, keywords)
        # Bonus: already links in niche, so it's a warm prospect
        boosted_score = min(100, base_score + 20)

        opp = {
            "strategy": "Competitor Mention",
            "url": url,
            "site_name": get_site_name(url, title),
            "title": title,
            "snippet": snippet[:200],
            "contact_email": "",
            "contact_page": "",
            "competitor_mentioned": competitor_mentioned,
            "score": boosted_score,
            "status": "New",
            "notes": f"Links to {competitor_mentioned} — pitch your site as an alternative/addition",
        }

        resp = fetch(url, timeout=timeout)
        if resp and resp.status_code == 200:
            soup = parse(resp.text, url)
            emails = extract_emails(soup)
            contact_page = extract_contact_page_url(soup, url) or ""
            if emails:
                opp["contact_email"] = pick_best_email(emails)
            opp["contact_page"] = contact_page
            if not opp["contact_email"] and contact_page:
                cresp = fetch(contact_page, timeout=timeout)
                if cresp and cresp.status_code == 200:
                    csoup = parse(cresp.text, contact_page)
                    cemails = extract_emails(csoup)
                    if cemails:
                        opp["contact_email"] = pick_best_email(cemails)

        console.print(
            f"  [green]✓[/green] {opp['site_name']:<30} score={opp['score']:>3}  "
            f"email={'✓' if opp['contact_email'] else '—'}  "
            f"[dim](via {competitor_mentioned})[/dim]"
        )
        opportunities.append(opp)
        time.sleep(delay)

    deduped = deduplicate_by_domain(opportunities)
    console.print(f"  [bold]Competitor Mention opportunities: {len(deduped)}[/bold]")
    return deduped
