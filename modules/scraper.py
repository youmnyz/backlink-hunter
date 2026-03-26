"""
HTTP fetching and HTML parsing utilities.
"""
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional
from rich.console import Console

console = Console()

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


def fetch(url: str, timeout: int = 10, headers: dict = None) -> Optional[requests.Response]:
    """Fetch a URL and return the Response, or None on failure."""
    hdrs = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        resp = requests.get(url, headers=hdrs, timeout=timeout, allow_redirects=True)
        return resp
    except requests.exceptions.RequestException as exc:
        console.print(f"[dim]Fetch failed for {url}: {exc}[/dim]")
        return None


def parse(html: str, base_url: str = "") -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def extract_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Return all anchor links as {text, href} dicts with resolved absolute URLs."""
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        abs_url = urljoin(base_url, href)
        links.append({
            "text": tag.get_text(strip=True),
            "href": abs_url,
        })
    return links


def extract_emails(soup: BeautifulSoup) -> list[str]:
    """Extract email addresses from visible text and mailto links."""
    import re
    emails = set()
    # mailto links
    for tag in soup.find_all("a", href=True):
        if tag["href"].startswith("mailto:"):
            email = tag["href"].replace("mailto:", "").split("?")[0].strip()
            if email:
                emails.add(email.lower())
    # plain text
    text = soup.get_text(" ")
    found = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    for e in found:
        emails.add(e.lower())
    return list(emails)


def extract_contact_page_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Try to find a contact page link on the page."""
    for tag in soup.find_all("a", href=True):
        text = tag.get_text(strip=True).lower()
        href = tag["href"].lower()
        if any(kw in text or kw in href for kw in ["contact", "get in touch", "reach us", "write for us"]):
            return urljoin(base_url, tag["href"])
    return None


def get_page_title(soup: BeautifulSoup) -> str:
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def get_meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def check_url_status(url: str, timeout: int = 8) -> int:
    """Return HTTP status code for a URL (0 on connection error)."""
    try:
        resp = requests.head(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        return resp.status_code
    except requests.exceptions.RequestException:
        return 0


def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "")


def pick_best_email(emails: list[str]) -> str:
    """
    From a list of discovered email addresses, return the most contact-appropriate one.
    Prefers addresses containing contact/info/hello/hi/team keywords.
    Falls back to the first email in the list.
    """
    if not emails:
        return ""
    preferred_prefixes = ("contact", "info", "hello", "hi@", "team", "reach", "enquir", "inquir")
    for e in emails:
        if any(p in e.lower() for p in preferred_prefixes):
            return e
    return emails[0]
