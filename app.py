"""
Flask web frontend for Backlink Hunter.
Run with: python app.py
Then open: http://localhost:5000
"""

import os, sys, csv, json, re, subprocess, threading, queue, time, io
from pathlib import Path
import yaml
from flask import Flask, render_template, jsonify, request, Response, stream_with_context

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
OUTPUT_DIR  = BASE_DIR / "output"

app = Flask(__name__)

# ── Global run state ──────────────────────────────────────
_run_queue: queue.Queue = queue.Queue()
_run_active = False
_run_lock   = threading.Lock()

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07')

def strip_ansi(text: str) -> str:
    text = ANSI_ESCAPE.sub('', text)
    # Replace emoji / non-ASCII that Windows cp1252 can't handle
    return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')


# ── Config helpers ─────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(data: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ── CSV helpers ────────────────────────────────────────────

def read_csv(filename: str) -> list[dict]:
    path = OUTPUT_DIR / filename
    if not path.exists():
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def write_csv(filename: str, rows: list[dict], fieldnames: list[str]):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── API Routes ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/discover-competitors", methods=["POST"])
def discover_competitors():
    """
    Use DuckDuckGo to discover competitor domains for the configured niche.
    Returns a list of {domain, name} dicts, deduped and filtered.
    Industry signals are derived dynamically from the configured niche + keywords.
    """
    cfg = load_config()
    niche    = (cfg.get("niche") or {}).get("primary", "")
    domain   = (cfg.get("target") or {}).get("domain", "")
    keywords = (cfg.get("niche") or {}).get("keywords", [])

    if not niche:
        return jsonify({"ok": False, "error": "Configure your niche first"}), 400

    try:
        sys.path.insert(0, str(BASE_DIR))
        from modules.searcher import search
        import tldextract

        # ── Build industry signals from configured niche + keywords ──
        def _extract_signals(niche_str: str, kws: list) -> list[str]:
            """Extract meaningful words from niche + keywords to use as signals."""
            stop = {"and","the","for","with","your","from","that","this","are",
                    "has","have","been","will","can","our","also","more","into"}
            signals: set[str] = set()
            for text in [niche_str] + kws[:8]:
                for word in text.lower().split():
                    w = word.strip(".,;:-")
                    if len(w) > 3 and w not in stop:
                        signals.add(w)
            return list(signals)[:15]

        industry_signals = _extract_signals(niche, keywords)
        if not industry_signals:
            industry_signals = [niche.lower()]

        # ── Strip trailing geo / location words before building queries ──
        def _strip_geo(kw: str) -> str:
            """Remove trailing capitalised geo words (e.g. 'CCTV Lebanon' → 'CCTV')."""
            words = kw.split()
            while len(words) > 1 and words[-1][0].isupper():
                words = words[:-1]
            return " ".join(words).strip(", ")

        queries = []
        for kw in (keywords or [niche])[:8]:
            base = _strip_geo(kw).strip()
            if base:
                queries.append(f'{base} company')

        # ── Skip list: directories, listicles, media, social ──
        skip_parts = {
            "thetoptens","ranktopten","top10","safesmartliving","safewise",
            "yellowpages","yelp","tripadvisor","trustpilot","clutch","g2.",
            "capterra","softwareadvice","reddit","quora","linkedin","facebook",
            "twitter","youtube","wikipedia","amazon","forbes","businessinsider",
            "techcrunch","reuters","bbc.","cnn.","aljazeera","theguardian",
        }

        import requests as _req

        def _is_niche_match(d: str) -> bool:
            """Fetch homepage and confirm it matches the configured niche."""
            try:
                r = _req.get(
                    f"https://{d}", timeout=7,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; BacklinkHunter/1.0)"},
                    allow_redirects=True,
                )
                text = r.text.lower()
                hits = sum(1 for s in industry_signals if s in text)
                return hits >= 2
            except Exception:
                return False   # can't reach — exclude

        seen_domains = {domain.lower().replace("www.", ""), ""}
        existing = {c.get("domain", "").lower() for c in cfg.get("competitors", [])}
        seen_domains |= existing

        candidates = []
        for query in queries:
            if len(candidates) >= 20:
                break
            results = search(query, max_results=6, pause=1.0)
            for r in results:
                url   = r.get("url", "")
                title = r.get("title", "")
                snip  = r.get("snippet", "").lower()
                if not url:
                    continue
                ext  = tldextract.extract(url)
                d    = f"{ext.domain}.{ext.suffix}".lower() if ext.suffix else ""
                bare = ext.domain.lower()
                if not d or bare in seen_domains or d in seen_domains:
                    continue
                if any(p in d for p in skip_parts):
                    continue
                # Quick snippet/title relevance check before fetching homepage
                combined = snip + " " + title.lower()
                if not any(s in combined for s in industry_signals):
                    continue
                seen_domains.add(d)
                candidates.append({"domain": d, "title": title})

        # ── Verify each candidate by fetching its homepage ────
        found = []
        for c in candidates:
            if len(found) >= 8:
                break
            d     = c["domain"]
            title = c["title"]
            if _is_niche_match(d):
                name = title.split("—")[0].split("|")[0].split("-")[0].strip()
                if len(name) > 50 or not name:
                    name = d.split(".")[0].replace("-", " ").title()
                found.append({"domain": d, "name": name})
                time.sleep(0.5)

        return jsonify({"ok": True, "competitors": found})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/analyse-site", methods=["POST"])
def analyse_site():
    """
    Scrape a homepage and deduce: brand name, description, niche, keywords,
    contact email, and sender name — so the user only has to type a domain.
    """
    body = request.get_json(force=True) or {}
    raw  = body.get("domain", "").strip().lower()
    if not raw:
        return jsonify({"ok": False, "error": "No domain provided"}), 400

    raw = raw.replace("https://","").replace("http://","").rstrip("/")
    url = f"https://{raw}"

    try:
        import requests as req
        from bs4 import BeautifulSoup
        import tldextract
        import re as _re

        _browser_headers = {
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
        timeout = 15

        def fetch(u):
            try:
                r = req.get(u, headers=_browser_headers, timeout=timeout,
                            allow_redirects=True)
                if r.status_code < 400:
                    return r.text
                # Some sites return 406 for bots — retry without Accept-Encoding
                if r.status_code == 406:
                    r2 = req.get(u, headers={**_browser_headers,
                                             "Accept": "text/html,*/*;q=0.9",
                                             "Accept-Encoding": "identity"},
                                 timeout=timeout, allow_redirects=True)
                    return r2.text if r2.status_code < 400 else None
                return None
            except Exception:
                return None

        def meta(soup, *names):
            for n in names:
                tag = soup.find("meta", attrs={"name": n}) or \
                      soup.find("meta", attrs={"property": n})
                if tag and tag.get("content","").strip():
                    return tag["content"].strip()
            return ""

        def clean_emails(text):
            return list({e.lower() for e in
                         _re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
                         if not e.startswith("example") and "sentry" not in e})

        # ── Fetch homepage ───────────────────────────────────
        html = fetch(url)
        if not html:
            html = fetch(url.replace("https://","http://"))
        if not html:
            return jsonify({"ok": False, "error": f"Could not reach {raw}"}), 502

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script","style","noscript"]): tag.decompose()

        # ── Brand name ───────────────────────────────────────
        brand = (meta(soup, "og:site_name") or
                 meta(soup, "application-name") or
                 (soup.find("title").get_text(strip=True).split("|")[0].split("–")[0].split("-")[0].strip()
                  if soup.find("title") else "") or
                 tldextract.extract(raw).domain.replace("-"," ").title())

        # ── Description ──────────────────────────────────────
        desc = (meta(soup, "og:description") or
                meta(soup, "description") or
                meta(soup, "twitter:description") or "")
        if len(desc) > 300:
            desc = desc[:300].rsplit(".", 1)[0] + "."

        # ── Keywords / niche ─────────────────────────────────
        kw_str  = meta(soup, "keywords")
        raw_kws = [k.strip() for k in kw_str.split(",") if k.strip()][:12] if kw_str else []

        # Keep keywords WITH their location suffix (e.g. "CCTV Lebanon") — these
        # are needed for geo-targeted competitor discovery later.
        # Only deduplicate and length-filter.
        kw_list = []
        seen_kw = set()
        for kw in raw_kws:
            low = kw.lower()
            if kw and low not in seen_kw and len(kw) < 60:
                seen_kw.add(low)
                kw_list.append(kw)
        kw_list = kw_list[:8]

        # For the primary niche hint, strip trailing geo words so it's clean
        # e.g. "CCTV Lebanon" → "CCTV", "fire safety Beirut" → "fire safety"
        def strip_geo_for_niche(kw):
            words = kw.split()
            while len(words) > 1 and words[-1][0].isupper():
                words = words[:-1]
            return " ".join(words)

        # Pick niche: prefer 2-3 word non-geo keyword over a long tagline
        def best_niche(keywords):
            stripped = [strip_geo_for_niche(k) for k in keywords]
            by_len   = sorted(stripped, key=lambda k: abs(len(k.split()) - 2))
            return by_len[0] if by_len else stripped[0]

        if kw_list:
            niche_hint = best_niche(kw_list)
        else:
            h1 = soup.find("h1")
            raw_hint = (h1.get_text(strip=True) if h1 else "") or brand
            words = raw_hint.split()
            niche_hint = " ".join(words[:3]) if len(words) > 3 else raw_hint

        # ── Contact email ─────────────────────────────────────
        emails = clean_emails(html)
        # Prefer contact/hello/info addresses
        preferred = [e for e in emails if any(p in e for p in ("contact","hello","info","hi","team"))]
        sender_email = preferred[0] if preferred else (emails[0] if emails else f"hello@{raw}")

        # Try /contact page for better email
        for slug in ("/contact", "/about", "/contact-us"):
            if sender_email.startswith("hello@"):   # only if we have a fallback so far
                c_html = fetch(url.rstrip("/") + slug)
                if c_html:
                    c_emails = clean_emails(c_html)
                    pref = [e for e in c_emails if any(p in e for p in ("contact","hello","info","hi","team"))]
                    if pref:
                        sender_email = pref[0]; break
                    elif c_emails:
                        sender_email = c_emails[0]; break

        # ── Sender name (from about page or brand) ────────────
        sender_name = brand

        result = {
            "brand_name":   brand[:80],
            "description":  desc,
            "niche":        niche_hint[:80],
            "keywords":     kw_list,
            "sender_email": sender_email,
            "sender_name":  sender_name,
            "url":          url,
        }
        return jsonify({"ok": True, **result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def post_config():
    data = request.get_json(force=True)
    try:
        save_config(data)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/opportunities", methods=["GET"])
def get_opportunities():
    rows = read_csv("backlink_opportunities.csv")
    return jsonify(rows)


@app.route("/api/opportunities/update", methods=["POST"])
def update_opportunity():
    """Update status/notes for a row identified by url."""
    body = request.get_json(force=True)
    url = body.get("url")
    field = body.get("field")   # "status" or "notes"
    value = body.get("value", "")

    ALLOWED_FIELDS = {"status", "notes"}
    if field not in ALLOWED_FIELDS:
        return jsonify({"ok": False, "error": "invalid field"}), 400

    rows = read_csv("backlink_opportunities.csv")
    if not rows:
        return jsonify({"ok": False, "error": "no data"}), 404

    fieldnames = list(rows[0].keys())
    updated = False
    for row in rows:
        if row.get("url") == url:
            row[field] = value
            updated = True
            break

    if not updated:
        return jsonify({"ok": False, "error": "url not found"}), 404

    write_csv("backlink_opportunities.csv", rows, fieldnames)
    return jsonify({"ok": True})


@app.route("/api/emails", methods=["GET"])
def get_emails():
    rows = read_csv("outreach_emails.csv")
    return jsonify(rows)


@app.route("/api/stats", methods=["GET"])
def get_stats():
    opps = read_csv("backlink_opportunities.csv")
    emails = read_csv("outreach_emails.csv")

    total = len(opps)
    with_email = sum(1 for o in opps if o.get("contact_email"))
    top_score = max((int(o.get("score", 0)) for o in opps), default=0)
    won = sum(1 for o in opps if o.get("status", "").lower() == "won")

    by_strategy = {}
    for o in opps:
        s = o.get("strategy", "Unknown")
        by_strategy[s] = by_strategy.get(s, 0) + 1

    by_status = {}
    for o in opps:
        s = o.get("status", "New") or "New"
        by_status[s] = by_status.get(s, 0) + 1

    return jsonify({
        "total": total,
        "with_email": with_email,
        "top_score": top_score,
        "won": won,
        "email_drafts": len(emails),
        "by_strategy": by_strategy,
        "by_status": by_status,
    })


# ── Run endpoint with SSE streaming ───────────────────────

@app.route("/api/run", methods=["POST"])
def start_run():
    global _run_active
    with _run_lock:
        if _run_active:
            return jsonify({"ok": False, "error": "A run is already in progress"}), 409
        _run_active = True

    body = request.get_json(force=True) or {}
    strategies = body.get("strategies", ["all"])
    max_results = body.get("max_results", 20)
    skip_emails = body.get("skip_emails", False)

    # Build CLI args
    cmd = [sys.executable, str(BASE_DIR / "backlink_hunter.py"), "run",
           "--config", str(CONFIG_PATH),
           "--max", str(max_results)]
    for s in strategies:
        cmd += ["--strategy", s]
    if skip_emails:
        cmd.append("--skip-emails")

    def run_process():
        global _run_active
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            # Force Rich to use ANSI mode instead of Win32 legacy console API,
            # which can't encode Unicode characters on Windows cp1252 terminals
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"
            env["NO_COLOR"] = "0"
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=str(BASE_DIR), text=True, encoding="utf-8", errors="replace",
                env=env
            )
            for line in proc.stdout:
                clean = strip_ansi(line).rstrip()
                if clean:
                    _run_queue.put({"type": "log", "text": clean})
            proc.wait()
            code = proc.returncode
            _run_queue.put({"type": "done", "code": code})
        except Exception as e:
            _run_queue.put({"type": "error", "text": str(e)})
            _run_queue.put({"type": "done", "code": 1})
        finally:
            with _run_lock:
                _run_active = False

    t = threading.Thread(target=run_process, daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/run/stream")
def stream_run():
    """SSE endpoint — client connects and receives run logs line by line."""
    def generate():
        yield "data: {\"type\":\"connected\"}\n\n"
        while True:
            try:
                msg = _run_queue.get(timeout=30)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("type") == "done":
                    break
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/api/run/status")
def run_status():
    return jsonify({"active": _run_active})


# ── Authority Directories ──────────────────────────────────

DIRECTORIES = [
    # ── Local / Map listings ─────────────────────────────────
    {"id":"google_biz",   "name":"Google Business Profile", "domain":"business.google.com",  "submit_url":"https://business.google.com/add",                             "category":"Local",          "authority":"Essential","skip_check":True},
    {"id":"bing_places",  "name":"Bing Places",             "domain":"bingplaces.com",        "submit_url":"https://www.bingplaces.com/",                                 "category":"Local",          "authority":"High",     "skip_check":True},
    {"id":"apple_maps",   "name":"Apple Maps",              "domain":"mapsconnect.apple.com", "submit_url":"https://mapsconnect.apple.com/",                              "category":"Local",          "authority":"High",     "skip_check":True},
    # ── Reviews ──────────────────────────────────────────────
    {"id":"trustpilot",   "name":"Trustpilot",              "domain":"trustpilot.com",        "submit_url":"https://business.trustpilot.com/",                            "category":"Reviews",        "authority":"High"},
    {"id":"g2",           "name":"G2",                      "domain":"g2.com",                "submit_url":"https://sell.g2.com/",                                        "category":"Reviews",        "authority":"High"},
    # ── B2B Directories ──────────────────────────────────────
    {"id":"clutch",       "name":"Clutch",                  "domain":"clutch.co",             "submit_url":"https://clutch.co/get-listed",                                "category":"B2B Directory",  "authority":"High"},
    {"id":"goodfirms",    "name":"GoodFirms",               "domain":"goodfirms.co",          "submit_url":"https://www.goodfirms.co/directory/get-listed",               "category":"B2B Directory",  "authority":"High"},
    {"id":"designrush",   "name":"DesignRush",              "domain":"designrush.com",        "submit_url":"https://www.designrush.com/agency/profile/new",               "category":"B2B Directory",  "authority":"High"},
    {"id":"kompass",      "name":"Kompass",                 "domain":"kompass.com",           "submit_url":"https://solutions.kompass.com/",                              "category":"B2B Directory",  "authority":"High"},
    # ── Business Registries ──────────────────────────────────
    {"id":"crunchbase",   "name":"Crunchbase",              "domain":"crunchbase.com",        "submit_url":"https://www.crunchbase.com/add-new-company",                  "category":"Business Reg.",  "authority":"High"},
    {"id":"dnb",          "name":"Dun & Bradstreet",        "domain":"dnb.com",               "submit_url":"https://www.dnb.com/duns-number/get-a-duns.html",             "category":"Business Reg.",  "authority":"High"},
    {"id":"manta",        "name":"Manta",                   "domain":"manta.com",             "submit_url":"https://www.manta.com/add-your-business",                     "category":"Business Reg.",  "authority":"Medium"},
    {"id":"hotfrog",      "name":"Hotfrog",                 "domain":"hotfrog.com",           "submit_url":"https://www.hotfrog.com/AddBusiness.aspx",                    "category":"Business Reg.",  "authority":"Medium"},
]


@app.route("/api/directory-scan")
def directory_scan():
    """
    SSE stream — checks each authority directory to see if the brand is listed.
    Uses DuckDuckGo site: searches. Skippable entries (Google, Bing, Apple) are
    marked 'manual' immediately since they aren't DDG-searchable.
    """
    cfg    = load_config()
    brand  = (cfg.get("target") or {}).get("name", "")
    domain = (cfg.get("target") or {}).get("domain", "")

    if not domain:
        return Response(
            'data: {"type":"error","text":"Configure your domain in Settings first"}\n\n',
            mimetype="text/event-stream"
        )

    # Pre-import once — not inside the per-directory loop
    sys.path.insert(0, str(BASE_DIR))
    from modules.searcher import search as _ddg_search

    bare = domain.replace("www.", "")

    def check(d):
        if d.get("skip_check"):
            return "manual"
        try:
            # Build query: use domain always; include brand name only when non-empty
            if brand:
                query = f'site:{d["domain"]} "{brand}" OR "{bare}"'
            else:
                query = f'site:{d["domain"]} "{bare}"'
            results = _ddg_search(query, max_results=3, pause=0.5)
            return "listed" if results else "not_listed"
        except Exception:
            return "unknown"

    def generate():
        yield f"data: {json.dumps({'type':'start','total':len(DIRECTORIES)})}\n\n"
        for d in DIRECTORIES:
            yield f"data: {json.dumps({'type':'checking','id':d['id']})}\n\n"
            status = check(d)
            payload = {**d, "status": status}
            yield f"data: {json.dumps({'type':'result','directory':payload})}\n\n"
            if not d.get("skip_check"):
                time.sleep(1.4)   # avoid DDG rate-limiting
        yield f"data: {json.dumps({'type':'done'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    print("\n  Backlink Hunter UI")
    print("  Open: http://localhost:5002\n")
    app.run(debug=False, port=5002, threaded=True)
