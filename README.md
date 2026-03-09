# SEO AI Dashboard — best4juniors.nl

Professional SEO monitoring dashboard built for Markitpapa.
Pulls 100% real data from Google Search Console + Google Analytics 4.

---

## Quick Start (3 Steps)

### Step 1 — Setup your .env file
Copy `.env.example` → rename to `.env`
Fill in your real values:
```
GOOGLE_SERVICE_ACCOUNT_KEY=service-account-key.json
GSC_PROPERTY_URL=https://best4juniors.nl/
GA4_PROPERTY_ID=500557472
ANTHROPIC_API_KEY=your-key-here
SITE_NAME=best4juniors.nl
```

### Step 2 — Add your Google key file
Place your `service-account-key.json` in the same folder.

### Step 3 — Double click START_DASHBOARD.bat
That's it. Dashboard opens in your browser automatically.

---

## Files Explained

| File | What it does |
|------|-------------|
| `START_DASHBOARD.bat` | **Double click this** — launches everything |
| `FETCH_DATA.bat` | Manually refresh data from Google |
| `STOP_DASHBOARD.bat` | Stop the dashboard |
| `dashboard.py` | Main dashboard web app |
| `main.py` | Fetches data from GSC + GA4 |
| `report_gen.py` | Generates PDF reports |
| `database.py` | SQLite database for history |
| `alerts.py` | Detects problems automatically |

---

## Dashboard Sections

- **Overview** — All KPI cards, alerts, charts, target tracker
- **Keywords** — All keywords with positions, changes, dying/improved
- **Traffic** — Sessions, channels, daily trend, top pages
- **Compare Periods** — Any period vs any period, baseline comparison
- **SEO Accountability** — Track what your SEO person actually did
- **Reports** — Generate PDF, download, compare archived reports

---

## Security

- `.env` and `service-account-key.json` are in `.gitignore`
- Never push these to GitHub
- Data stays on your computer

---

Built by Markitpapa | March 2026
