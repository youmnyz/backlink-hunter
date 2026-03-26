"""
DuckDuckGo-backed search module.
Returns a list of {title, url, snippet} dicts.
"""
import time
from rich.console import Console

console = Console()


def search(query: str, max_results: int = 20, pause: float = 2.0) -> list[dict]:
    """
    Run a DuckDuckGo text search and return up to max_results results.
    Falls back gracefully if the library or network is unavailable.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
    except ImportError:
        console.print("[red]ddgs not installed. Run: pip install ddgs[/red]")
        return []

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url":   r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        time.sleep(pause)
    except Exception as exc:
        console.print(f"[yellow]Search warning for '{query[:60]}': {exc}[/yellow]")

    return results


# ── Location words to strip before building opportunity queries ────────────────
_GEO_WORDS = {
    "lebanon","beirut","middle","east","mena","arab","gulf","gcc",
    "saudi","uae","dubai","jordan","africa","west","north","south",
    "levant","region","regional",
}


def _opportunity_terms(niche: str, keywords: list[str]) -> list[str]:
    """
    Derive clean, geo-free physical-security search terms from the config.
    e.g. "CCTV Lebanon" → "CCTV",  "fire safety systems" stays as-is,
         "security company" → kept,  "security industry specialists" → skipped (too long)
    Returns up to 5 unique terms, 1–4 words each.
    """
    seen, result = set(), []
    for kw in [niche] + keywords:
        words = [w for w in kw.split() if w.lower() not in _GEO_WORDS and len(w) > 1]
        clean = " ".join(words).strip()
        low   = clean.lower()
        if clean and 1 <= len(clean.split()) <= 4 and low not in seen:
            seen.add(low)
            result.append(clean)
        if len(result) >= 5:
            break
    return result or [niche]


def build_guest_post_queries(niche: str, keywords: list[str]) -> list[str]:
    terms = _opportunity_terms(niche, keywords)
    templates = [
        '"{kw}" "write for us"',
        '"{kw}" "guest post"',
        '"{kw}" "submit an article"',
        '"{kw}" "become a contributor"',
        '"{kw}" "accepting guest posts"',
        '"{kw}" blog "contribute"',
    ]
    queries = []
    for kw in terms:
        for tpl in templates:
            queries.append(tpl.format(kw=kw))
    return queries


def build_resource_page_queries(niche: str, keywords: list[str]) -> list[str]:
    terms = _opportunity_terms(niche, keywords)
    templates = [
        '"{kw}" "useful resources"',
        '"{kw}" "recommended resources"',
        '"{kw}" inurl:resources',
        '"{kw}" "resource page"',
        '"{kw}" "helpful links"',
        '"{kw}" site:.org resources',
    ]
    queries = []
    for kw in terms:
        for tpl in templates:
            queries.append(tpl.format(kw=kw))
    return queries


def build_competitor_mention_queries(competitor_domain: str, niche: str) -> list[str]:
    """Find pages mentioning a competitor — good link targets for us too."""
    bare = competitor_domain.replace("www.", "")
    core = " ".join(niche.split()[:3])
    return [
        f'"{bare}" {core} -site:{bare}',
        f'"{bare}" "alternative" {core}',
        f'"{bare}" review {core}',
    ]


def build_broken_link_queries(niche: str, keywords: list[str]) -> list[str]:
    terms = _opportunity_terms(niche, keywords)[:3]
    templates = [
        '"{kw}" "useful links" site:.edu',
        '"{kw}" resources site:.org',
        '"{kw}" "further reading" blog',
        '"{kw}" inurl:links resources',
    ]
    queries = []
    for kw in terms:
        for tpl in templates:
            queries.append(tpl.format(kw=kw))
    return queries
