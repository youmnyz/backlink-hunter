# Backlink Hunter

An AI-assisted backlink building tool with a full web UI. It scrapes the web for link-building opportunities across four strategies, scores them, finds contact emails, and generates personalised outreach drafts — all automatically.

---

## Strategies

| Strategy | What it does |
|---|---|
| **Guest Post** | Finds blogs in your niche that accept guest contributions |
| **Broken Links** | Finds pages with dead outbound links you can replace |
| **Resource Pages** | Finds curated "resources" pages where your site can be listed |
| **Competitor Backlinks** | Finds sites already linking to competitors — warm prospects |

---

## Quick Start (local)

### 1. Clone & install

```bash
git clone https://github.com/your-username/backlink-hunter.git
cd backlink-hunter
pip install -r requirements.txt
```

### 2. Configure

Copy the example config and edit it:

```bash
cp config.yaml.example config.yaml
```

Open `config.yaml` and fill in your domain, niche, and outreach details.
Or skip this step and configure everything inside the web UI (Settings tab).

### 3. Launch the web UI

```bash
python app.py
```

Open **http://localhost:5002** in your browser.

The web UI lets you:
- **Settings** — enter your domain, niche, keywords, competitors, and sender info. Click *Analyse Site* to auto-fill most fields from your homepage.
- **Run** — choose strategies, set result limits, and watch live output stream in.
- **Opportunities** — browse, filter, sort, and update status on every lead found.
- **Email Drafts** — view and copy personalised outreach emails for each opportunity.
- **Directories** — scan 14 authority directories to see where your brand is missing.
- **Dashboard** — summary stats and charts.

### 4. CLI (optional)

```bash
# Run all strategies
python backlink_hunter.py run

# Run one strategy, limit results
python backlink_hunter.py run --strategy guest_post --max 15

# Skip email generation
python backlink_hunter.py run --skip-emails

# Preview email templates
python backlink_hunter.py preview-emails --strategy broken_links

# Validate config
python backlink_hunter.py validate-config
```

---

## Output

Two CSV files are written to `output/`:

| File | Contents |
|---|---|
| `backlink_opportunities.csv` | All prospects — score, contact info, notes, status |
| `outreach_emails.csv` | Personalised email draft for each opportunity |

### Opportunity columns

| Column | Description |
|---|---|
| `strategy` | Which tactic found it |
| `site_name` / `url` | The target site |
| `score` | 0–100 quality score (higher = better) |
| `contact_email` | Extracted automatically; blank = manual lookup needed |
| `contact_page` | URL of the site's contact page |
| `status` | Update to `Emailed / Replied / Won / Lost / Skipped` as you work |
| `notes` | Context on why this is an opportunity |

---

## Deployment

### Option A — Render.com (free, permanent URL)

1. Push this repo to GitHub (make sure `config.yaml` and `output/` are in `.gitignore` — they are by default).
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo.
3. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   - **Environment:** Python 3
4. Deploy. Your app gets a permanent `https://your-app.onrender.com` URL.

> **Note:** Render's free tier uses ephemeral storage — `config.yaml` and CSVs reset on each deploy. Configure your settings through the web UI after each deploy, or upgrade to a paid plan with a persistent disk.

### Option B — Railway

1. Push to GitHub.
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
3. Railway auto-detects the `Procfile`. Deploy.
4. Add a **Volume** (Volumes tab) mounted at `/app/output` to persist your CSV data between deploys.

### Option C — Docker (self-host anywhere)

```bash
docker build -t backlink-hunter .
docker run -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/output:/app/output \
  backlink-hunter
```

Open **http://localhost:8000**.

### Option D — Quick share with ngrok

While running locally:

```bash
pip install ngrok
ngrok http 5002
```

Share the `https://xxxx.ngrok.io` URL. Whoever has the link can use the tool while your machine is on.

---

## Tips

- Start with `--max 15` for a quick test run, then increase to 30+.
- The `score` column sorts the best opportunities to the top — focus there first.
- For **Broken Links**, keep `check_broken_links: true` in config — it actively verifies each outbound URL returns 4xx/5xx before flagging it.
- Run weekly; the tracker appends new opportunities without duplicating existing ones.
- Use the **Directories** tab to find quick wins — getting listed on Clutch, Crunchbase, or Google Business Profile is low-effort high-authority.
