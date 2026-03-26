"""
Tracker: save opportunities and email drafts to CSV files.
Also supports loading/merging with existing CSV to avoid losing prior outreach status.
"""
import os
import csv
from datetime import datetime
from pathlib import Path
from rich.console import Console

console = Console()

# Column order for the main opportunities CSV
OPPORTUNITY_COLUMNS = [
    "date_found",
    "strategy",
    "site_name",
    "url",
    "score",
    "contact_email",
    "contact_page",
    "status",           # New / Emailed / Replied / Won / Lost / Skipped
    "title",
    "snippet",
    "broken_link_url",
    "broken_link_text",
    "competitor_mentioned",
    "notes",
]

EMAIL_COLUMNS = [
    "site_name",
    "url",
    "strategy",
    "contact_email",
    "score",
    "status",
    "email_draft",
]


def _ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


def _load_existing_urls(filepath: str) -> set:
    """Return a set of URLs already in the CSV (to avoid duplicates)."""
    if not os.path.exists(filepath):
        return set()
    urls = set()
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "url" in row:
                urls.add(row["url"])
    return urls


def save_opportunities(opportunities: list[dict], config: dict) -> str:
    """Write opportunities to CSV. Merges with any existing file."""
    out_dir = config.get("output", {}).get("directory", "output")
    filename = config.get("output", {}).get("csv_filename", "backlink_opportunities.csv")
    filepath = os.path.join(out_dir, filename)

    _ensure_dir(out_dir)
    existing_urls = _load_existing_urls(filepath)

    new_rows = []
    today = datetime.today().strftime("%Y-%m-%d")
    for opp in opportunities:
        if opp.get("url") in existing_urls:
            continue  # skip duplicates
        row = {col: opp.get(col, "") for col in OPPORTUNITY_COLUMNS}
        row["date_found"] = today
        new_rows.append(row)

    # Append mode — preserve existing rows
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OPPORTUNITY_COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    console.print(
        f"\n[green]✓[/green] Saved [bold]{len(new_rows)}[/bold] new opportunities → [cyan]{filepath}[/cyan]"
    )
    return filepath


def save_email_drafts(opportunities: list[dict], config: dict) -> str:
    """Write outreach email drafts to a separate CSV."""
    out_dir = config.get("output", {}).get("directory", "output")
    filename = config.get("output", {}).get("email_drafts_filename", "outreach_emails.csv")
    filepath = os.path.join(out_dir, filename)

    _ensure_dir(out_dir)
    existing_urls = _load_existing_urls(filepath)

    new_rows = []
    for opp in opportunities:
        if opp.get("url") in existing_urls or not opp.get("email_draft"):
            continue
        row = {col: opp.get(col, "") for col in EMAIL_COLUMNS}
        new_rows.append(row)

    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EMAIL_COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    console.print(
        f"[green]✓[/green] Saved [bold]{len(new_rows)}[/bold] email drafts → [cyan]{filepath}[/cyan]"
    )
    return filepath


def print_summary_table(opportunities: list[dict]):
    """Print a Rich summary table to the console."""
    from rich.table import Table

    table = Table(title="Backlink Opportunities Summary", show_lines=False)
    table.add_column("Strategy", style="cyan", no_wrap=True)
    table.add_column("Site", style="white")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Email", justify="center")
    table.add_column("URL", style="dim", max_width=55)

    sorted_opps = sorted(opportunities, key=lambda x: x.get("score", 0), reverse=True)
    for opp in sorted_opps[:50]:  # show top 50
        table.add_row(
            opp.get("strategy", ""),
            opp.get("site_name", ""),
            str(opp.get("score", 0)),
            "✓" if opp.get("contact_email") else "—",
            opp.get("url", ""),
        )

    console.print(table)
