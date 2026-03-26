"""
Outreach email generator.
Produces personalised email drafts for each opportunity type.
"""
from jinja2 import Template

# ─────────────────────────────────────────────────────────────
#  Email templates (Jinja2)
# ─────────────────────────────────────────────────────────────

TEMPLATES = {
    "Guest Post": Template("""\
Subject: Guest Post Pitch for {{ site_name }} — {{ niche }} Expertise

Hi {{ site_name }} Team,

I've been following {{ site_name }} for a while and love the quality of content you publish around {{ niche }}.

I'd love to contribute a guest post to your blog. Here are a few topic ideas that I think would resonate with your readers:

  1. [Topic idea 1 — based on their audience]
  2. [Topic idea 2 — data-driven or actionable angle]
  3. [Topic idea 3 — contrarian or fresh perspective]

A bit about me: I run {{ sender_site_name }} ({{ sender_site_url }}), where we cover {{ niche }} in depth. {{ sender_site_description }}

I can deliver a well-researched, original article (1,500–2,500 words) complete with images and internal links to your existing content.

Would any of these topics interest you? Happy to tailor ideas to your editorial calendar.

Thanks for your time,
{{ sender_name }}{% if sender_title %}
{{ sender_title }}{% endif %}
{{ sender_email }}
{{ sender_site_url }}
"""),

    "Resource Page": Template("""\
Subject: Addition to Your {{ niche }} Resources Page

Hi {{ site_name }} Team,

I came across your resources page at {{ opportunity_url }} and noticed it's a great collection of {{ niche }} tools and references.

I wanted to suggest adding {{ sender_site_name }} ({{ sender_site_url }}) — {{ sender_site_description }}

It would complement the resources you've already listed and give your readers another valuable reference.

If you think it's a good fit, I'd be grateful for the inclusion. Happy to return the favour in any way I can.

Thanks,
{{ sender_name }}{% if sender_title %}
{{ sender_title }} @ {{ sender_site_name }}{% endif %}
{{ sender_email }}
"""),

    "Broken Link": Template("""\
Subject: Broken Link Found on {{ site_name }} + a Replacement

Hi {{ site_name }} Team,

I was reading your page at {{ opportunity_url }} and noticed a broken link:

  Link text: "{{ broken_link_text }}"
  Broken URL: {{ broken_link_url }}

I thought you'd want to know — broken links hurt the reader experience and SEO.

As a relevant replacement, I'd like to suggest {{ sender_site_name }} ({{ sender_site_url }}): {{ sender_site_description }}

It covers a similar topic and should be a natural fit for your readers.

Either way, hope this heads-up is useful!

Best,
{{ sender_name }}{% if sender_title %}
{{ sender_title }} @ {{ sender_site_name }}{% endif %}
{{ sender_email }}
"""),

    "Competitor Mention": Template("""\
Subject: You Might Also Want to Mention {{ sender_site_name }}

Hi {{ site_name }} Team,

I noticed your article at {{ opportunity_url }} mentions {{ competitor_mentioned }} — great piece!

I wanted to reach out because {{ sender_site_name }} ({{ sender_site_url }}) offers a similar (and in some ways complementary) perspective on {{ niche }}: {{ sender_site_description }}

Your readers might find it useful alongside what you've already linked to. If you think it's a good fit, I'd love to be included.

Thanks for considering it,
{{ sender_name }}{% if sender_title %}
{{ sender_title }} @ {{ sender_site_name }}{% endif %}
{{ sender_email }}
"""),

    "General": Template("""\
Subject: Link Collaboration Opportunity — {{ sender_site_name }}

Hi {{ site_name }} Team,

I came across {{ site_name }} and think there's a great opportunity for us to collaborate on a link.

We run {{ sender_site_name }} ({{ sender_site_url }}): {{ sender_site_description }}

Given your focus on {{ niche }}, I believe our content would be genuinely useful to your audience.

Would love to explore whether there's a natural way to work together — whether that's a guest post, a resource mention, or something else.

Open to ideas!

{{ sender_name }}{% if sender_title %}
{{ sender_title }} @ {{ sender_site_name }}{% endif %}
{{ sender_email }}
"""),
}


def generate_email(opportunity: dict, config: dict) -> str:
    """Return a rendered outreach email string for the given opportunity."""
    strategy = opportunity.get("strategy", "General")
    template = TEMPLATES.get(strategy, TEMPLATES["General"])

    context = {
        # Opportunity info
        "site_name": opportunity.get("site_name", ""),
        "opportunity_url": opportunity.get("url", ""),
        "broken_link_url": opportunity.get("broken_link_url", ""),
        "broken_link_text": opportunity.get("broken_link_text", ""),
        "competitor_mentioned": opportunity.get("competitor_mentioned", "a competitor"),
        # Our site info
        "sender_site_name": config["target"].get("name", config["target"]["domain"]),
        "sender_site_url": config["target"]["url"],
        "sender_site_description": config["target"].get("description", "").strip(),
        "niche": config["niche"]["primary"],
        # Sender personal info
        "sender_name": config["outreach"].get("sender_name", ""),
        "sender_title": config["outreach"].get("sender_title", ""),
        "sender_email": config["outreach"].get("sender_email", ""),
    }

    return template.render(**context)


def generate_all_emails(opportunities: list[dict], config: dict) -> list[dict]:
    """Add an 'email_draft' field to each opportunity dict and return them."""
    enriched = []
    for opp in opportunities:
        opp_copy = dict(opp)
        opp_copy["email_draft"] = generate_email(opp, config)
        enriched.append(opp_copy)
    return enriched
