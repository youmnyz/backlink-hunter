"""
Domain analysis and opportunity scoring utilities.
"""
import re
from urllib.parse import urlparse
from typing import Optional
import tldextract


def score_opportunity(url: str, title: str, snippet: str, niche_keywords: list[str]) -> int:
    """
    Heuristic 0–100 score for how valuable a backlink opportunity is.
    Higher = better prospect.
    """
    score = 0
    text = (url + " " + title + " " + snippet).lower()

    # Domain quality signals
    ext = tldextract.extract(url)
    tld = ext.suffix.lower()
    if tld in ("edu", "gov", "org"):
        score += 20
    elif tld == "com":
        score += 10

    # Keyword relevance
    for kw in niche_keywords:
        if kw.lower() in text:
            score += 8
    score = min(score, 40)  # cap keyword bonus

    # Page type signals (resource / roundup pages link out often)
    resource_signals = [
        "resource", "tools", "links", "recommended", "best",
        "top", "list", "guide", "roundup", "collection",
    ]
    for sig in resource_signals:
        if sig in text:
            score += 3
    score = min(score, 70)

    # Guest post / contributor signals
    guest_signals = ["write for us", "guest post", "submit", "contributor", "guidelines"]
    for sig in guest_signals:
        if sig in text:
            score += 10

    # Bonus: physical security industry relevance
    physical_signals = [
        "cctv", "surveillance", "access control", "fire safety", "fire alarm",
        "intrusion", "security camera", "physical security", "guard", "perimeter",
        "security system", "safety solution", "alarm system", "video surveillance",
        "ip camera", "biometric", "security installation",
    ]
    physical_hits = sum(1 for s in physical_signals if s in text)
    score += min(physical_hits * 6, 24)

    # Bonus: MENA / Lebanon / regional relevance
    regional_signals = [
        "lebanon", "beirut", "middle east", "mena", "arab", "levant",
        "gulf", "gcc", "saudi", "uae", "dubai", "jordan", "egypt", "africa",
    ]
    regional_hits = sum(1 for s in regional_signals if s in text)
    score += min(regional_hits * 5, 15)

    # Penalty: cybersecurity / IT-only sites (not physical security)
    cyber_signals = [
        "cybersecurity", "penetration testing", "malware", "ransomware",
        "phishing", "data breach", "infosec", "soc analyst", "zero day",
        "exploit", "vulnerability", "patch management", "devsecops",
    ]
    cyber_hits = sum(1 for s in cyber_signals if s in text)
    if cyber_hits > 0 and physical_hits == 0:
        score -= 30   # cyber-only — irrelevant to a physical security company

    # Penalty: social, aggregators, major platforms (not niche blogs)
    low_value = [
        "reddit.com", "quora.com", "twitter.com", "x.com", "linkedin.com",
        "facebook.com", "youtube.com", "pinterest.com", "instagram.com",
        "tiktok.com", "google.com", "google.co", "bing.com", "yahoo.com",
        "amazon.com", "wikipedia.org", "microsoft.com", "apple.com",
        "github.com", "stackoverflow.com", "medium.com", "substack.com",
        "tumblr.com", "wordpress.com", "blogspot.com", "seznam.cz",
        "meet.google", "maps.google", "play.google", "docs.google",
    ]
    for lv in low_value:
        if lv in url.lower():
            score -= 40

    return max(0, min(100, score))


def classify_opportunity(url: str, title: str, snippet: str) -> str:
    """Return a human-readable type label for the opportunity."""
    text = (url + " " + title + " " + snippet).lower()
    if any(kw in text for kw in ["write for us", "guest post", "contributor", "submit article"]):
        return "Guest Post"
    if any(kw in text for kw in ["resource", "useful links", "recommended", "further reading"]):
        return "Resource Page"
    if any(kw in text for kw in ["broken link", "404", "dead link"]):
        return "Broken Link"
    if any(kw in text for kw in ["alternative", "vs ", "review", "comparison"]):
        return "Competitor Mention"
    return "General"


def is_same_domain(url1: str, url2: str) -> bool:
    d1 = tldextract.extract(url1)
    d2 = tldextract.extract(url2)
    return (d1.domain == d2.domain) and (d1.suffix == d2.suffix)


def deduplicate_by_domain(opportunities: list[dict]) -> list[dict]:
    """Keep at most one opportunity per root domain."""
    seen_domains = set()
    result = []
    for opp in opportunities:
        ext = tldextract.extract(opp.get("url", ""))
        root = f"{ext.domain}.{ext.suffix}"
        if root not in seen_domains:
            seen_domains.add(root)
            result.append(opp)
    return result


def get_site_name(url: str, title: str) -> str:
    """Derive a friendly site name from URL or title."""
    ext = tldextract.extract(url)
    if ext.domain:
        return ext.domain.replace("-", " ").title()
    return title.split("|")[0].split("–")[0].split("-")[0].strip()
