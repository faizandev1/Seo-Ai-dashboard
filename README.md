# 📊 SEO AI Dashboard

A professional, fully automated SEO monitoring dashboard built with Python and Flask.
Pulls real-time data from Google Search Console and Google Analytics 4 — no manual exports needed.

---
<img width="1278" height="863" alt="Capture" src="https://github.com/user-attachments/assets/a4f1536c-f08e-4915-909b-144f2256cee3" />
<img width="1269" height="869" alt="3" src="https://github.com/user-attachments/assets/bf9a9326-3eba-4402-96dc-f64c3000b5f9" />
<img width="1275" height="868" alt="2" src="https://github.com/user-attachments/assets/9dea8459-2703-492f-8ee8-aef03f3f543f" />
<img width="1279" height="866" alt="2322" src="https://github.com/user-attachments/assets/20ce0d1d-dbf3-40a4-9921-4012bb0a17bb" />

 
## ✨ Features

- **Live GSC Data** — Clicks, impressions, CTR, average position, all keywords
- **Live GA4 Data** — Sessions, users, organic traffic, all channels
- **Keyword Health Monitor** — Position changes, improved, declined, dying, page 2 wins
- **Period Comparison** — Any date range vs any date range with % change
- **KPI Target Tracker** — Compare current numbers vs your 6-month growth targets
- **Red Flag Alerts** — Auto-detects traffic drops, keyword declines, low CTR
- **SEO Accountability Panel** — Track backlinks built, blog posts published, monthly deliverables
- **PDF Report Generator** — One click professional PDF with all metrics
- **Report Archive** — Every PDF saved to SQLite database for historical comparison
- **Historical Trend Charts** — See growth over weeks and months
- **Advanced Graphs** — Plotly powered interactive charts
- **Professional UI** — Clean white Google-style interface with Lucide icons
- **Mobile Responsive** — Works on any screen size
- **One Click Launch** — Double click `.bat` file, browser opens automatically

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/seo-ai-dashboard.git
cd seo-ai-dashboard
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
```
Fill in your credentials in `.env`

### 4. Add Google Service Account Key
Place your `service-account-key.json` in the root folder.

### 5. Launch dashboard
**Windows:** Double click `START_DASHBOARD.bat`

**Manual:**
```bash
python main.py      # fetch data
python dashboard.py # start server
```
Open `http://localhost:5000`

---

## ⚙️ Configuration

Edit `.env` file:
```env
GOOGLE_SERVICE_ACCOUNT_KEY=service-account-key.json
GSC_PROPERTY_URL=https://www.yourwebsite.com/
GA4_PROPERTY_ID=YOUR_GA4_PROPERTY_ID
ANTHROPIC_API_KEY=your_anthropic_key
SITE_NAME=Your Site Name
```

---

## 📁 Project Structure
```
seo-ai-dashboard/
├── START_DASHBOARD.bat     ← Double click to launch
├── FETCH_DATA.bat          ← Manually refresh data
├── STOP_DASHBOARD.bat      ← Stop the dashboard
├── dashboard.py            ← Main Flask dashboard
├── main.py                 ← Data fetcher
├── database.py             ← SQLite history & reports
├── alerts.py               ← Auto alert detection
├── report_gen.py           ← PDF report generator
├── config.py               ← Settings & KPI targets
├── scheduler.py            ← Auto daily refresh
├── fetchers/
│   ├── fetch_gsc.py        ← Google Search Console
│   └── fetch_ga4.py        ← Google Analytics 4
├── data/                   ← Saved data (gitignored)
└── .env.example            ← Environment template
```

---

## 📊 Dashboard Sections

| Section | Description |
|---------|-------------|
| Overview | KPI cards, alerts, charts, target tracker |
| Keywords | All keywords with position changes and filters |
| Traffic | Sessions, channels, daily trend, top pages |
| Compare | Period vs period and baseline comparison |
| Accountability | Track SEO team monthly deliverables |
| Reports | Generate and download PDF reports |

---

## 🔒 Security

- `.env` and `service-account-key.json` are in `.gitignore`
- Never commit real credentials to GitHub
- All data stored locally on your machine

---

## 🛠 Tech Stack

- **Backend** — Python, Flask
- **Data** — Google Search Console API, Google Analytics Data API
- **Database** — SQLite
- **Charts** — Plotly
- **PDF** — ReportLab
- **Icons** — Lucide
- **AI** — Anthropic Claude API

---
## 📄 License & Ownership

Copyright (c) 2026 Faizan. All Rights Reserved.

This software and all associated source code, documentation, and files are the
exclusive proprietary property of Faizan.

**You may NOT:**
- Copy, modify, or distribute this software
- Use this software for commercial purposes without written permission
- Share, sublicense, or sell any part of this codebase
- Reverse engineer or reuse any portion of this project

**To request permission:**
Contact the developer directly before using any part of this project.

Unauthorized use of this software is strictly prohibited and may result in legal action.
```

---
 
