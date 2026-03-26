#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║         Backlink Hunter — CLI Entrypoint             ║
║  Scrape the web for backlink opportunities &         ║
║  generate personalised outreach emails               ║
╚══════════════════════════════════════════════════════╝

Usage:
  python backlink_hunter.py run
  python backlink_hunter.py run --strategy guest_post
  python backlink_hunter.py run --strategy broken_links --strategy resource_pages
  python backlink_hunter.py run --config my_config.yaml
  python backlink_hunter.py preview-emails
  python backlink_hunter.py validate-config
"""

import os
import sys
import yaml
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# ─────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        console.print(f"[red]Config file not found: {config_path}[/red]")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_config(config: dict) -> list[str]:
    """Return a list of validation errors (empty = OK)."""
    errors = []
    if not config.get("target", {}).get("domain"):
        errors.append("target.domain is required")
    if not config.get("target", {}).get("url"):
        errors.append("target.url is required")
    if not config.get("niche", {}).get("primary"):
        errors.append("niche.primary is required")
    if not config.get("outreach", {}).get("sender_email"):
        errors.append("outreach.sender_email is required for email drafts")
    return errors


ALL_STRATEGIES = ["guest_post", "broken_links", "resource_pages", "competitor"]

STRATEGY_MAP = {
    "guest_post":    ("modules.strategies.guest_post",    "run"),
    "broken_links":  ("modules.strategies.broken_links",  "run"),
    "resource_pages":("modules.strategies.resource_pages","run"),
    "competitor":    ("modules.strategies.competitor",    "run"),
}


def _import_strategy(name: str):
    import importlib
    module_path, fn_name = STRATEGY_MAP[name]
    mod = importlib.import_module(module_path)
    return getattr(mod, fn_name)


# ─────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────

@click.group()
def cli():
    """Backlink Hunter — find and pitch backlink opportunities."""
    pass


@cli.command()
@click.option("--config", "config_path", default="config.yaml",
              show_default=True, help="Path to YAML config file")
@click.option("--strategy", "strategies", multiple=True,
              type=click.Choice(ALL_STRATEGIES + ["all"]),
              default=["all"],
              show_default=True,
              help="Which strategy/strategies to run (can repeat)")
@click.option("--skip-emails", is_flag=True, default=False,
              help="Skip generating outreach email drafts")
@click.option("--max", "max_results", default=None, type=int,
              help="Override max_results_per_strategy from config")
def run(config_path, strategies, skip_emails, max_results):
    """
    Run backlink prospecting and generate outreach emails.

    Examples:\n
      python backlink_hunter.py run\n
      python backlink_hunter.py run --strategy guest_post --strategy broken_links\n
      python backlink_hunter.py run --max 20 --skip-emails
    """
    console.print(Panel.fit(
        Text("Backlink Hunter", style="bold white"),
        subtitle="[dim]starting prospecting run[/dim]",
        border_style="cyan",
    ))

    config = load_config(config_path)
    if max_results:
        config["scraper"]["max_results_per_strategy"] = max_results

    # Validate
    errors = validate_config(config)
    if errors:
        console.print("[red]Config errors:[/red]")
        for e in errors:
            console.print(f"  • {e}")
        console.print("\nEdit [cyan]config.yaml[/cyan] and try again.")
        sys.exit(1)

    console.print(f"  Target: [bold]{config['target']['url']}[/bold]")
    console.print(f"  Niche:  [bold]{config['niche']['primary']}[/bold]")
    console.print(f"  Max results / strategy: [bold]{config['scraper']['max_results_per_strategy']}[/bold]\n")

    # Resolve which strategies to run
    to_run = ALL_STRATEGIES if ("all" in strategies or not strategies) else list(strategies)

    all_opportunities: list[dict] = []

    for strategy_name in to_run:
        fn = _import_strategy(strategy_name)
        results = fn(config)
        all_opportunities.extend(results)

    if not all_opportunities:
        console.print("[yellow]No opportunities found. Try broadening your niche keywords.[/yellow]")
        return

    # Filter out low-relevance results (generic/off-topic pages)
    MIN_SCORE = 15
    before = len(all_opportunities)
    all_opportunities = [o for o in all_opportunities if o.get("score", 0) >= MIN_SCORE]
    dropped = before - len(all_opportunities)
    if dropped:
        console.print(f"  [dim]Filtered out {dropped} low-relevance results (score < {MIN_SCORE})[/dim]")

    if not all_opportunities:
        console.print("[yellow]All results scored below threshold. Try more specific niche keywords.[/yellow]")
        return

    # Sort by score descending
    all_opportunities.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Generate emails
    if not skip_emails:
        from modules.outreach import generate_all_emails
        all_opportunities = generate_all_emails(all_opportunities, config)

    # Save outputs
    from modules.tracker import save_opportunities, save_email_drafts, print_summary_table
    opps_path = save_opportunities(all_opportunities, config)

    if not skip_emails:
        email_path = save_email_drafts(all_opportunities, config)

    # Print summary table
    print_summary_table(all_opportunities)

    console.print(f"\n[bold green]Done![/bold green] Found [bold]{len(all_opportunities)}[/bold] total opportunities.")
    console.print(f"  Opportunities CSV : [cyan]{opps_path}[/cyan]")
    if not skip_emails:
        console.print(f"  Email drafts CSV  : [cyan]{email_path}[/cyan]")

    # Print how many have contact emails
    with_email = sum(1 for o in all_opportunities if o.get("contact_email"))
    console.print(
        f"\n  [green]{with_email}[/green] / {len(all_opportunities)} opportunities have a contact email found automatically."
    )
    console.print("  For the rest, check the 'contact_page' column or visit the site manually.\n")


@cli.command("validate-config")
@click.option("--config", "config_path", default="config.yaml", show_default=True)
def validate_config_cmd(config_path):
    """Check config.yaml for missing required fields."""
    config = load_config(config_path)
    errors = validate_config(config)
    if errors:
        console.print("[red]Config has errors:[/red]")
        for e in errors:
            console.print(f"  ✗ {e}")
    else:
        console.print("[green]✓ Config looks good![/green]")
        console.print(f"  Target : {config['target']['url']}")
        console.print(f"  Niche  : {config['niche']['primary']}")
        console.print(f"  Sender : {config['outreach'].get('sender_name')} <{config['outreach'].get('sender_email')}>")
        n_competitors = len(config.get("competitors", []))
        console.print(f"  Competitors configured: {n_competitors}")


@cli.command("preview-emails")
@click.option("--config", "config_path", default="config.yaml", show_default=True)
@click.option("--strategy", "strategy",
              type=click.Choice(ALL_STRATEGIES),
              default="guest_post",
              show_default=True,
              help="Which strategy email template to preview")
def preview_emails(config_path, strategy):
    """Preview the outreach email template for a given strategy."""
    config = load_config(config_path)
    from modules.outreach import generate_email

    # Build a dummy opportunity for preview
    dummy = {
        "strategy": {
            "guest_post":    "Guest Post",
            "broken_links":  "Broken Link",
            "resource_pages":"Resource Page",
            "competitor":    "Competitor Mention",
        }[strategy],
        "site_name": "Example Blog",
        "url": "https://example.com/resources",
        "broken_link_url": "https://example.com/old-article",
        "broken_link_text": "The Ultimate Guide to Content Marketing",
        "competitor_mentioned": "Competitor Site",
    }

    email = generate_email(dummy, config)
    console.print(Panel(
        email,
        title=f"[bold cyan]{dummy['strategy']} — Email Preview[/bold cyan]",
        border_style="dim",
    ))


@cli.command("list-strategies")
def list_strategies():
    """List all available prospecting strategies."""
    strategies = {
        "guest_post":     "Find blogs/sites accepting guest contributions",
        "broken_links":   "Find pages with broken outbound links to replace",
        "resource_pages": "Find curated resource pages to get listed on",
        "competitor":     "Mine sites that link to competitors",
    }
    console.print("\n[bold]Available strategies:[/bold]\n")
    for name, desc in strategies.items():
        console.print(f"  [cyan]{name:<18}[/cyan] {desc}")
    console.print()


if __name__ == "__main__":
    cli()
