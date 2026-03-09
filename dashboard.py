import os, json, subprocess, threading, time
from datetime import datetime
from flask import Flask, jsonify, request, send_file, render_template_string
from dotenv import load_dotenv
load_dotenv()

from database import (get_snapshots, get_all_reports, get_accountability,
                       save_accountability, get_trend_data, get_keyword_positions)
from alerts import generate_alerts
import config

app = Flask(__name__)

def load_json(path):
    try:
        with open(path) as f: return json.load(f)
    except: return {}

def load_data():
    return load_json('data/gsc/data.json'), load_json('data/ga4/data.json')

def pct(cur, prev):
    if not prev: return None
    return round((cur - prev) / prev * 100, 1)

# ─── ROUTES ────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML,
        site_name=config.SITE_NAME,
        site_url=config.GSC_PROPERTY_URL or '')

@app.route('/api/overview')
def api_overview():
    days = int(request.args.get('days', 28))
    gsc, ga4 = load_data()
    s  = gsc.get('summary', {})
    ps = gsc.get('prev_summary', {})
    gs = ga4.get('summary', {})
    gp = ga4.get('prev_summary', {})

    return jsonify({
        'gsc': {
            'clicks':      s.get('total_clicks', 0),
            'impressions': s.get('total_impressions', 0),
            'ctr':         s.get('avg_ctr', 0),
            'position':    s.get('avg_position', 0),
            'keywords':    s.get('total_keywords', 0),
            'top10':       s.get('keywords_top10', 0),
            'top50':       s.get('keywords_top50', 0),
            'page2':       s.get('keywords_page2', 0),
        },
        'gsc_prev': {
            'clicks':      ps.get('total_clicks', 0),
            'impressions': ps.get('total_impressions', 0),
            'position':    ps.get('avg_position', 0),
            'keywords':    ps.get('total_keywords', 0),
        },
        'ga4': {
            'organic':  gs.get('organic_sessions', 0),
            'sessions': gs.get('total_sessions', 0),
            'users':    gs.get('total_users', 0),
            'bounce':   gs.get('avg_bounce_rate', 0),
        },
        'ga4_prev': {
            'organic':  gp.get('organic_sessions', 0),
            'sessions': gp.get('total_sessions', 0),
        },
        'alerts': generate_alerts(gsc, ga4),
        'period': gsc.get('period', {}),
        'fetched_at': gsc.get('fetched_at', ''),
        'baselines': config.BASELINES,
        'targets': config.KPI_TARGETS,
    })

@app.route('/api/keywords')
def api_keywords():
    gsc, _ = load_data()
    queries = gsc.get('queries', [])
    prev    = {(r.get('keys',[''])[0]): r for r in gsc.get('queries_prev', [])}

    result = []
    for r in queries:
        keys = r.get('keys', [])
        kw   = keys[0] if keys else ''
        pos  = r.get('position', 0)
        p    = prev.get(kw, {})
        prev_pos = p.get('position', 0)
        change   = round(prev_pos - pos, 1) if prev_pos else 0  # positive = improved

        result.append({
            'keyword':    kw,
            'position':   round(pos, 1),
            'prev_pos':   round(prev_pos, 1) if prev_pos else None,
            'change':     change,
            'clicks':     r.get('clicks', 0),
            'impressions':r.get('impressions', 0),
            'ctr':        round(r.get('ctr', 0) * 100, 2),
            'status': (
                'top3' if pos <= 3 else
                'top10' if pos <= 10 else
                'page2' if pos <= 20 else
                'page3' if pos <= 30 else
                'dying' if pos > 50 else 'ok'
            )
        })

    return jsonify({
        'keywords':   result,
        'page2':      [r for r in result if r['status'] == 'page2'],
        'dying':      [r for r in result if r['status'] == 'dying'],
        'top10':      [r for r in result if r['status'] in ('top3','top10')],
        'improved':   sorted([r for r in result if r['change'] > 0],
                              key=lambda x: x['change'], reverse=True)[:20],
        'declined':   sorted([r for r in result if r['change'] < 0],
                              key=lambda x: x['change'])[:20],
        'low_ctr':    [r for r in result if r['impressions'] > 50 and r['ctr'] < 1.0],
        'total': len(result),
    })

@app.route('/api/traffic')
def api_traffic():
    _, ga4 = load_data()
    channels      = ga4.get('channels', [])
    channels_prev = ga4.get('channels_prev', [])
    pages         = ga4.get('pages', [])
    daily         = ga4.get('daily', [])

    prev_map = {r.get('sessionDefaultChannelGroup',''): r for r in channels_prev}

    ch_result = []
    for ch in channels:
        name     = ch.get('sessionDefaultChannelGroup', '')
        sessions = int(ch.get('sessions', 0))
        p        = prev_map.get(name, {})
        prev_s   = int(p.get('sessions', 0)) if p else 0
        ch_result.append({
            'channel':  name,
            'sessions': sessions,
            'users':    int(ch.get('totalUsers', 0)),
            'bounce':   round(float(ch.get('bounceRate', 0)) * 100, 1),
            'duration': round(float(ch.get('averageSessionDuration', 0)), 0),
            'prev_sessions': prev_s,
            'change':   pct(sessions, prev_s),
        })

    page_result = []
    for p in pages[:50]:
        page_result.append({
            'page':     p.get('pagePath', ''),
            'sessions': int(p.get('sessions', 0)),
            'users':    int(p.get('totalUsers', 0)),
            'bounce':   round(float(p.get('bounceRate', 0)) * 100, 1),
            'duration': round(float(p.get('averageSessionDuration', 0)), 0),
        })

    daily_result = []
    for d in sorted(daily, key=lambda x: x.get('date','')):
        daily_result.append({
            'date':     d.get('date', ''),
            'sessions': int(d.get('sessions', 0)),
            'users':    int(d.get('totalUsers', 0)),
        })

    return jsonify({
        'channels': ch_result,
        'pages':    page_result,
        'daily':    daily_result,
        'summary':  ga4.get('summary', {}),
        'prev_summary': ga4.get('prev_summary', {}),
    })

@app.route('/api/compare')
def api_compare():
    gsc, ga4 = load_data()
    snapshots = get_snapshots(24)
    return jsonify({
        'snapshots': snapshots,
        'current_gsc': gsc.get('summary', {}),
        'current_ga4': ga4.get('summary', {}),
        'trend': get_trend_data(12),
    })

@app.route('/api/accountability', methods=['GET', 'POST'])
def api_accountability():
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    if request.method == 'POST':
        data = request.json
        save_accountability(month, data)
        return jsonify({'ok': True})
    acc = get_accountability(month)
    gsc, ga4 = load_data()
    s = gsc.get('summary', {})
    gs = ga4.get('summary', {})
    return jsonify({
        'accountability': acc,
        'month': month,
        'live': {
            'clicks':     s.get('total_clicks', 0),
            'keywords':   s.get('total_keywords', 0),
            'top10':      s.get('keywords_top10', 0),
            'impressions':s.get('total_impressions', 0),
            'organic':    gs.get('organic_sessions', 0),
            'sessions':   gs.get('total_sessions', 0),
        },
        'targets': config.KPI_TARGETS,
        'baselines': config.BASELINES,
    })

@app.route('/api/reports')
def api_reports():
    return jsonify({'reports': get_all_reports()})

@app.route('/api/generate-pdf', methods=['POST'])
def api_generate_pdf():
    try:
        from report_gen import generate_pdf
        gsc, ga4 = load_data()
        month = datetime.now().strftime('%Y-%m')
        acc   = get_accountability(month)
        days  = int(request.json.get('days', 28)) if request.json else 28
        title = request.json.get('title', f"SEO Report — {datetime.now().strftime('%B %Y')}") if request.json else None
        filepath, filename = generate_pdf(gsc, ga4, acc, title)
        return jsonify({'ok': True, 'filename': filename, 'filepath': filepath})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/download-report/<filename>')
def download_report(filename):
    path = f"data/reports/{filename}"
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/fetch-data', methods=['POST'])
def api_fetch_data():
    days = int(request.json.get('days', 28)) if request.json else 28
    def run():
        from main import run_fetch
        run_fetch(days)
    threading.Thread(target=run, daemon=True).start()
    return jsonify({'ok': True, 'message': f'Fetching {days} days of data in background...'})

# ─── DASHBOARD HTML ────────────────────────────────────────

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SEO Dashboard — {{ site_name }}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --blue:#1a73e8;--blue-light:#e8f0fe;--green:#34a853;--green-light:#e6f4ea;
  --red:#ea4335;--red-light:#fce8e6;--yellow:#fbbc04;--yellow-light:#fef7e0;
  --dark:#202124;--mid:#5f6368;--light:#9aa0a6;--border:#e8eaed;
  --bg:#f8f9fa;--white:#ffffff;--sidebar-w:240px;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--dark);font-size:14px}
/* SIDEBAR */
.sidebar{position:fixed;left:0;top:0;width:var(--sidebar-w);height:100vh;
  background:var(--white);border-right:1px solid var(--border);
  display:flex;flex-direction:column;z-index:100}
.sidebar-logo{padding:20px 20px 16px;border-bottom:1px solid var(--border)}
.logo-title{font-size:16px;font-weight:700;color:var(--dark)}
.logo-sub{font-size:11px;color:var(--light);margin-top:2px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sidebar-nav{flex:1;padding:12px 0;overflow-y:auto}
.nav-section{padding:16px 16px 6px;font-size:10px;font-weight:600;
  color:var(--light);text-transform:uppercase;letter-spacing:.8px}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 20px;
  cursor:pointer;color:var(--mid);font-size:13px;font-weight:500;
  transition:all .15s;border-left:3px solid transparent}
.nav-item:hover{background:var(--bg);color:var(--dark)}
.nav-item.active{background:var(--blue-light);color:var(--blue);
  border-left-color:var(--blue)}
.nav-item i{width:18px;height:18px;flex-shrink:0}
.sidebar-footer{padding:16px 20px;border-top:1px solid var(--border)}
.fetch-btn{width:100%;padding:10px;background:var(--blue);color:white;
  border:none;border-radius:8px;font-size:13px;font-weight:600;
  cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;
  transition:background .2s}
.fetch-btn:hover{background:#1557b0}
/* MAIN */
.main{margin-left:var(--sidebar-w);min-height:100vh}
/* TOPBAR */
.topbar{background:var(--white);border-bottom:1px solid var(--border);
  padding:0 28px;height:64px;display:flex;align-items:center;
  justify-content:space-between;position:sticky;top:0;z-index:50}
.topbar-left{display:flex;align-items:center;gap:12px}
.page-title{font-size:18px;font-weight:700}
.topbar-right{display:flex;align-items:center;gap:12px}
.filter-group{display:flex;gap:4px;background:var(--bg);
  padding:4px;border-radius:8px;border:1px solid var(--border)}
.filter-btn{padding:6px 14px;border:none;background:transparent;
  border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;
  color:var(--mid);transition:all .15s;font-family:inherit}
.filter-btn.active{background:var(--white);color:var(--blue);
  font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.last-updated{font-size:11px;color:var(--light)}
/* CONTENT */
.content{padding:24px 28px}
.section{display:none}
.section.active{display:block}
/* ALERTS */
.alert-bar{margin-bottom:20px}
.alert{display:flex;align-items:center;gap:10px;padding:12px 16px;
  border-radius:8px;margin-bottom:8px;font-size:13px;font-weight:500}
.alert i{width:16px;height:16px;flex-shrink:0}
.alert.critical{background:var(--red-light);color:var(--red)}
.alert.warning{background:var(--yellow-light);color:#b06000}
.alert.good{background:var(--green-light);color:#1e7e34}
/* CARDS */
.cards-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:16px;margin-bottom:24px}
.card{background:var(--white);border-radius:12px;padding:20px;
  border:1px solid var(--border);position:relative;overflow:hidden}
.card-icon{width:40px;height:40px;border-radius:10px;display:flex;
  align-items:center;justify-content:center;margin-bottom:12px}
.card-icon i{width:20px;height:20px}
.card-icon.blue{background:var(--blue-light);color:var(--blue)}
.card-icon.green{background:var(--green-light);color:var(--green)}
.card-icon.red{background:var(--red-light);color:var(--red)}
.card-icon.yellow{background:var(--yellow-light);color:#b06000}
.card-icon.purple{background:#f3e8ff;color:#7c3aed}
.card-label{font-size:12px;color:var(--light);font-weight:500;margin-bottom:4px}
.card-value{font-size:26px;font-weight:700;color:var(--dark);line-height:1}
.card-change{font-size:12px;margin-top:6px;display:flex;align-items:center;gap:4px}
.card-change i{width:13px;height:13px}
.card-change.up{color:var(--green)}
.card-change.down{color:var(--red)}
.card-change.neutral{color:var(--light)}
.card-sub{font-size:11px;color:var(--light);margin-top:4px}
/* CHARTS ROW */
.charts-row{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:24px}
.chart-card{background:var(--white);border:1px solid var(--border);
  border-radius:12px;padding:20px}
.chart-title{font-size:14px;font-weight:600;margin-bottom:16px;color:var(--dark)}
.chart-title span{font-size:12px;color:var(--light);font-weight:400}
/* TABLES */
.table-card{background:var(--white);border:1px solid var(--border);
  border-radius:12px;margin-bottom:16px;overflow:hidden}
.table-header{padding:16px 20px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between}
.table-header h3{font-size:14px;font-weight:600}
.table-header span{font-size:12px;color:var(--light)}
table{width:100%;border-collapse:collapse}
th{padding:10px 16px;text-align:left;font-size:11px;font-weight:600;
  color:var(--light);text-transform:uppercase;letter-spacing:.5px;
  background:var(--bg);border-bottom:1px solid var(--border)}
td{padding:10px 16px;border-bottom:1px solid var(--border);font-size:13px}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--bg)}
/* BADGES */
.badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.badge-green{background:var(--green-light);color:var(--green)}
.badge-red{background:var(--red-light);color:var(--red)}
.badge-yellow{background:var(--yellow-light);color:#b06000}
.badge-blue{background:var(--blue-light);color:var(--blue)}
.badge-gray{background:var(--bg);color:var(--light)}
/* CHANGE INDICATORS */
.chg{display:inline-flex;align-items:center;gap:3px;font-size:12px;font-weight:600}
.chg i{width:12px;height:12px}
.chg.up{color:var(--green)}
.chg.down{color:var(--red)}
.chg.flat{color:var(--light)}
/* PROGRESS BAR */
.progress-wrap{margin:8px 0}
.progress-label{display:flex;justify-content:space-between;
  font-size:12px;color:var(--mid);margin-bottom:4px}
.progress-bar{height:6px;background:var(--border);border-radius:3px;overflow:hidden}
.progress-fill{height:100%;border-radius:3px;transition:width .4s}
.progress-fill.blue{background:var(--blue)}
.progress-fill.green{background:var(--green)}
.progress-fill.red{background:var(--red)}
.progress-fill.yellow{background:var(--yellow)}
/* SECTION HEADER */
.section-header{display:flex;align-items:center;justify-content:space-between;
  margin-bottom:20px}
.section-header h2{font-size:16px;font-weight:700}
/* TABS */
.tabs{display:flex;gap:4px;background:var(--bg);padding:4px;
  border-radius:8px;border:1px solid var(--border);width:fit-content;margin-bottom:20px}
.tab{padding:7px 16px;border:none;background:transparent;border-radius:6px;
  font-size:13px;font-weight:500;cursor:pointer;color:var(--mid);
  transition:all .15s;font-family:inherit}
.tab.active{background:var(--white);color:var(--blue);font-weight:600;
  box-shadow:0 1px 3px rgba(0,0,0,.1)}
.sub-section{display:none}
.sub-section.active{display:block}
/* COMPARE */
.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px}
.compare-card{background:var(--white);border:1px solid var(--border);
  border-radius:12px;padding:20px}
.compare-card h3{font-size:13px;font-weight:600;color:var(--mid);margin-bottom:16px}
.compare-row{display:flex;justify-content:space-between;align-items:center;
  padding:10px 0;border-bottom:1px solid var(--border)}
.compare-row:last-child{border-bottom:none}
.compare-metric{font-size:13px;color:var(--mid)}
.compare-values{display:flex;align-items:center;gap:12px}
.compare-val{font-size:14px;font-weight:700}
.compare-val.period-a{color:var(--blue)}
.compare-val.period-b{color:var(--mid)}
/* ACCOUNTABILITY */
.acc-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.acc-card{background:var(--white);border:1px solid var(--border);
  border-radius:12px;padding:20px}
.acc-card h3{font-size:14px;font-weight:600;margin-bottom:16px}
.form-group{margin-bottom:14px}
.form-label{font-size:12px;font-weight:600;color:var(--mid);margin-bottom:6px;display:block}
.form-input{width:100%;padding:9px 12px;border:1px solid var(--border);
  border-radius:8px;font-size:13px;font-family:inherit;color:var(--dark);
  transition:border .15s}
.form-input:focus{outline:none;border-color:var(--blue)}
.form-textarea{width:100%;padding:9px 12px;border:1px solid var(--border);
  border-radius:8px;font-size:13px;font-family:inherit;color:var(--dark);
  resize:vertical;min-height:80px}
.save-btn{padding:10px 24px;background:var(--blue);color:white;border:none;
  border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;
  font-family:inherit;transition:background .2s}
.save-btn:hover{background:#1557b0}
/* REPORTS */
.report-list{display:grid;gap:12px}
.report-item{background:var(--white);border:1px solid var(--border);
  border-radius:12px;padding:16px 20px;display:flex;
  align-items:center;justify-content:space-between}
.report-item-left{display:flex;align-items:center;gap:14px}
.report-icon{width:40px;height:40px;background:var(--red-light);
  border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--red)}
.report-icon i{width:20px;height:20px}
.report-title{font-size:14px;font-weight:600}
.report-meta{font-size:12px;color:var(--light);margin-top:2px}
.report-actions{display:flex;gap:8px}
.btn-sm{padding:7px 14px;border-radius:7px;font-size:12px;font-weight:600;
  cursor:pointer;border:none;font-family:inherit;transition:all .15s;
  display:flex;align-items:center;gap:6px}
.btn-sm i{width:14px;height:14px}
.btn-outline{background:transparent;border:1px solid var(--border);color:var(--mid)}
.btn-outline:hover{border-color:var(--blue);color:var(--blue)}
.btn-primary{background:var(--blue);color:white}
.btn-primary:hover{background:#1557b0}
.btn-generate{padding:12px 24px;background:var(--blue);color:white;border:none;
  border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;
  font-family:inherit;display:flex;align-items:center;gap:8px;transition:background .2s}
.btn-generate:hover{background:#1557b0}
.btn-generate i{width:18px;height:18px}
/* KPI TARGET */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:16px;margin-bottom:24px}
.kpi-card{background:var(--white);border:1px solid var(--border);
  border-radius:12px;padding:18px 20px}
.kpi-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.kpi-label{font-size:13px;font-weight:600}
.kpi-current{font-size:22px;font-weight:700;color:var(--dark)}
.kpi-targets-row{display:flex;gap:12px;margin-top:8px}
.kpi-target{text-align:center}
.kpi-target-val{font-size:12px;font-weight:600}
.kpi-target-lbl{font-size:10px;color:var(--light)}
/* LOADING */
.loading{display:flex;align-items:center;justify-content:center;
  height:120px;color:var(--light);gap:10px;font-size:14px}
.spinner{width:20px;height:20px;border:2px solid var(--border);
  border-top-color:var(--blue);border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
/* EMPTY */
.empty{text-align:center;padding:40px;color:var(--light)}
.empty i{width:40px;height:40px;margin-bottom:12px;opacity:.4}
/* TOAST */
.toast{position:fixed;bottom:24px;right:24px;padding:14px 20px;
  background:var(--dark);color:white;border-radius:10px;font-size:13px;
  font-weight:500;z-index:9999;display:none;align-items:center;gap:10px}
.toast.show{display:flex}
.toast i{width:16px;height:16px}
/* RESPONSIVE */
@media(max-width:900px){
  .sidebar{transform:translateX(-100%)}
  .main{margin-left:0}
  .charts-row{grid-template-columns:1fr}
  .compare-grid,.acc-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>

<!-- SIDEBAR -->
<aside class="sidebar">
  <div class="sidebar-logo">
    <div class="logo-title">SEO Dashboard</div>
    <div class="logo-sub">{{ site_url }}</div>
  </div>
  <nav class="sidebar-nav">
    <div class="nav-section">Analytics</div>
    <div class="nav-item active" onclick="showSection('overview')">
      <i data-lucide="layout-dashboard"></i> Overview
    </div>
    <div class="nav-item" onclick="showSection('keywords')">
      <i data-lucide="search"></i> Keywords
    </div>
    <div class="nav-item" onclick="showSection('traffic')">
      <i data-lucide="bar-chart-2"></i> Traffic
    </div>
    <div class="nav-section">Tools</div>
    <div class="nav-item" onclick="showSection('compare')">
      <i data-lucide="git-compare"></i> Compare Periods
    </div>
    <div class="nav-item" onclick="showSection('accountability')">
      <i data-lucide="clipboard-check"></i> SEO Accountability
    </div>
    <div class="nav-item" onclick="showSection('reports')">
      <i data-lucide="file-text"></i> Reports & Archive
    </div>
  </nav>
  <div class="sidebar-footer">
    <button class="fetch-btn" onclick="fetchData()">
      <i data-lucide="refresh-cw" id="refresh-icon"></i> Refresh Data
    </button>
  </div>
</aside>

<!-- MAIN -->
<div class="main">
  <!-- TOPBAR -->
  <div class="topbar">
    <div class="topbar-left">
      <span class="page-title" id="page-title">Overview</span>
    </div>
    <div class="topbar-right">
      <div class="filter-group">
        <button class="filter-btn" onclick="setDays(3)">3D</button>
        <button class="filter-btn" onclick="setDays(7)">7D</button>
        <button class="filter-btn active" onclick="setDays(28)">28D</button>
        <button class="filter-btn" onclick="setDays(90)">90D</button>
      </div>
      <span class="last-updated" id="last-updated">—</span>
    </div>
  </div>

  <!-- CONTENT -->
  <div class="content">

    <!-- OVERVIEW -->
    <div class="section active" id="section-overview">
      <div class="alert-bar" id="alert-bar"></div>
      <div class="cards-grid" id="overview-cards">
        <div class="loading"><div class="spinner"></div> Loading...</div>
      </div>
      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-title">Clicks & Impressions <span id="clicks-period"></span></div>
          <div id="chart-clicks" style="height:240px"></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Traffic Sources</div>
          <div id="chart-channels" style="height:240px"></div>
        </div>
      </div>
      <div class="chart-card" style="margin-bottom:24px">
        <div class="chart-title">Keyword Position Distribution</div>
        <div id="chart-positions" style="height:200px"></div>
      </div>
      <div class="kpi-grid" id="kpi-targets"></div>
    </div>

    <!-- KEYWORDS -->
    <div class="section" id="section-keywords">
      <div class="tabs">
        <button class="tab active" onclick="showKwTab('all')">All Keywords</button>
        <button class="tab" onclick="showKwTab('improved')">Improved</button>
        <button class="tab" onclick="showKwTab('declined')">Declined</button>
        <button class="tab" onclick="showKwTab('page2')">Page 2 Wins</button>
        <button class="tab" onclick="showKwTab('dying')">Dying</button>
        <button class="tab" onclick="showKwTab('low_ctr')">Low CTR</button>
      </div>
      <div class="sub-section active" id="kw-all">
        <div class="table-card">
          <div class="table-header"><h3>All Keywords</h3><span id="kw-total"></span></div>
          <table><thead><tr>
            <th>Keyword</th><th>Position</th><th>Change</th>
            <th>Clicks</th><th>Impressions</th><th>CTR</th><th>Status</th>
          </tr></thead><tbody id="kw-all-body"></tbody></table>
        </div>
      </div>
      <div class="sub-section" id="kw-improved">
        <div class="table-card">
          <div class="table-header"><h3>Most Improved Keywords</h3><span>Position moved up vs last period</span></div>
          <table><thead><tr>
            <th>Keyword</th><th>Previous</th><th>Current</th><th>Improvement</th><th>Clicks</th>
          </tr></thead><tbody id="kw-improved-body"></tbody></table>
        </div>
      </div>
      <div class="sub-section" id="kw-declined">
        <div class="table-card">
          <div class="table-header"><h3>Declined Keywords</h3><span>Position dropped vs last period</span></div>
          <table><thead><tr>
            <th>Keyword</th><th>Previous</th><th>Current</th><th>Drop</th><th>Impressions</th>
          </tr></thead><tbody id="kw-declined-body"></tbody></table>
        </div>
      </div>
      <div class="sub-section" id="kw-page2">
        <div class="table-card">
          <div class="table-header">
            <h3>Page 2 Keywords — Quick Wins</h3>
            <span>Push these to page 1 for big traffic gains</span>
          </div>
          <table><thead><tr>
            <th>Keyword</th><th>Position</th><th>Impressions</th><th>Clicks</th><th>CTR</th>
          </tr></thead><tbody id="kw-page2-body"></tbody></table>
        </div>
      </div>
      <div class="sub-section" id="kw-dying">
        <div class="table-card">
          <div class="table-header">
            <h3>Dying Keywords</h3><span>Position below 50 — needs content work</span>
          </div>
          <table><thead><tr>
            <th>Keyword</th><th>Position</th><th>Impressions</th><th>Clicks</th>
          </tr></thead><tbody id="kw-dying-body"></tbody></table>
        </div>
      </div>
      <div class="sub-section" id="kw-low_ctr">
        <div class="table-card">
          <div class="table-header">
            <h3>High Impressions — Low CTR</h3><span>Fix meta titles to increase clicks</span>
          </div>
          <table><thead><tr>
            <th>Keyword</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th>Position</th>
          </tr></thead><tbody id="kw-low_ctr-body"></tbody></table>
        </div>
      </div>
    </div>

    <!-- TRAFFIC -->
    <div class="section" id="section-traffic">
      <div class="charts-row" style="margin-bottom:24px">
        <div class="chart-card">
          <div class="chart-title">Daily Sessions Trend</div>
          <div id="chart-daily" style="height:240px"></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Channel Breakdown</div>
          <div id="chart-channel-pie" style="height:240px"></div>
        </div>
      </div>
      <div class="table-card" style="margin-bottom:16px">
        <div class="table-header"><h3>Traffic by Channel</h3><span>vs previous period</span></div>
        <table><thead><tr>
          <th>Channel</th><th>Sessions</th><th>Users</th>
          <th>Bounce Rate</th><th>Avg Duration</th><th>vs Prev</th>
        </tr></thead><tbody id="channel-body"></tbody></table>
      </div>
      <div class="table-card">
        <div class="table-header"><h3>Top Pages by Traffic</h3></div>
        <table><thead><tr>
          <th>Page</th><th>Sessions</th><th>Users</th><th>Bounce Rate</th>
        </tr></thead><tbody id="pages-body"></tbody></table>
      </div>
    </div>

    <!-- COMPARE -->
    <div class="section" id="section-compare">
      <div class="section-header">
        <h2>Period Comparison</h2>
      </div>
      <div class="compare-grid">
        <div class="compare-card">
          <h3>Current Period vs Previous Period</h3>
          <div id="compare-live"></div>
        </div>
        <div class="compare-card">
          <h3>Progress vs Baseline (Feb 2026)</h3>
          <div id="compare-baseline"></div>
        </div>
      </div>
      <div class="chart-card" style="margin-bottom:24px">
        <div class="chart-title">Historical Trend — Clicks & Sessions</div>
        <div id="chart-trend" style="height:280px"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">Keyword Count Over Time</div>
        <div id="chart-kw-trend" style="height:220px"></div>
      </div>
    </div>

    <!-- ACCOUNTABILITY -->
    <div class="section" id="section-accountability">
      <div class="section-header">
        <h2>SEO Person Accountability Tracker</h2>
        <div style="display:flex;align-items:center;gap:10px">
          <input type="month" id="acc-month" class="form-input"
            style="width:160px" value="">
          <button class="save-btn" onclick="loadAccountability()">Load</button>
        </div>
      </div>
      <div class="acc-grid">
        <div class="acc-card">
          <h3>Live SEO Metrics This Period</h3>
          <div id="acc-live-metrics"></div>
        </div>
        <div class="acc-card">
          <h3>KPI Target Progress</h3>
          <div id="acc-targets"></div>
        </div>
      </div>
      <div class="acc-card" style="margin-bottom:16px">
        <h3>Monthly Deliverables — What Your SEO Person Did</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px">
          <div>
            <div class="form-group">
              <label class="form-label">Backlinks Built This Month</label>
              <input type="number" id="acc-backlinks" class="form-input" placeholder="0" min="0">
            </div>
            <div class="form-group">
              <label class="form-label">Backlink URLs (one per line)</label>
              <textarea id="acc-backlink-urls" class="form-textarea"
                placeholder="https://example.com&#10;https://another.com"></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">Blog Posts Published</label>
              <input type="number" id="acc-posts" class="form-input" placeholder="0" min="0">
            </div>
          </div>
          <div>
            <div class="form-group">
              <label class="form-label">Blog Post Titles (one per line)</label>
              <textarea id="acc-post-titles" class="form-textarea"
                placeholder="Title 1&#10;Title 2"></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">Domain Authority (check Semrush)</label>
              <input type="number" id="acc-da" class="form-input" placeholder="2" min="0" max="100">
            </div>
            <div class="form-group">
              <label class="form-label">Technical Fixes Done</label>
              <textarea id="acc-fixes" class="form-textarea"
                placeholder="Fixed broken links, updated sitemap..."></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">Additional Notes</label>
              <textarea id="acc-notes" class="form-textarea"
                placeholder="Any extra notes..."></textarea>
            </div>
          </div>
        </div>
        <button class="save-btn" onclick="saveAccountability()">Save Monthly Record</button>
      </div>
      <div class="table-card">
        <div class="table-header">
          <h3>Red Flags — Is Your SEO Person Working?</h3>
        </div>
        <div id="red-flags" style="padding:16px"></div>
      </div>
    </div>

    <!-- REPORTS -->
    <div class="section" id="section-reports">
      <div class="section-header">
        <h2>Reports & Archive</h2>
        <button class="btn-generate" onclick="generatePDF()">
          <i data-lucide="download"></i> Generate PDF Report
        </button>
      </div>
      <div id="report-list">
        <div class="loading"><div class="spinner"></div> Loading reports...</div>
      </div>
    </div>

  </div><!-- /content -->
</div><!-- /main -->

<div class="toast" id="toast">
  <i data-lucide="check-circle" id="toast-icon"></i>
  <span id="toast-msg"></span>
</div>

<script>
// ── STATE ──────────────────────────────────────────────
let currentDays = 28;
let currentSection = 'overview';
let kwData = null;
let trafficData = null;

// ── INIT ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  document.getElementById('acc-month').value =
    new Date().toISOString().slice(0,7);
  loadOverview();
  setActiveFilter(28);
});

// ── NAVIGATION ─────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('section-' + name).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => {
    if (n.textContent.trim().toLowerCase().includes(name.slice(0,4))) {
      n.classList.add('active');
    }
  });
  const titles = {
    overview:'Overview', keywords:'Keywords', traffic:'Traffic',
    compare:'Compare Periods', accountability:'SEO Accountability',
    reports:'Reports & Archive'
  };
  document.getElementById('page-title').textContent = titles[name] || name;
  currentSection = name;

  if (name === 'keywords' && !kwData) loadKeywords();
  if (name === 'traffic' && !trafficData) loadTraffic();
  if (name === 'compare') loadCompare();
  if (name === 'accountability') loadAccountability();
  if (name === 'reports') loadReports();
}

// ── DAYS FILTER ────────────────────────────────────────
function setDays(days) {
  currentDays = days;
  kwData = null; trafficData = null;
  setActiveFilter(days);
  if (currentSection === 'overview') loadOverview();
  else if (currentSection === 'keywords') loadKeywords();
  else if (currentSection === 'traffic') loadTraffic();
}

function setActiveFilter(days) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  const map = {3:'3D',7:'7D',28:'28D',90:'90D'};
  document.querySelectorAll('.filter-btn').forEach(b => {
    if (b.textContent === map[days]) b.classList.add('active');
  });
}

// ── FETCH DATA ─────────────────────────────────────────
async function fetchData() {
  const icon = document.getElementById('refresh-icon');
  icon.style.animation = 'spin .6s linear infinite';
  showToast('Fetching fresh data from Google...', 'loader');
  try {
    const res = await fetch('/api/fetch-data', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({days: currentDays})
    });
    showToast('Data fetching in background. Refresh in 30 seconds.', 'check-circle');
    setTimeout(() => { location.reload(); }, 35000);
  } catch(e) { showToast('Error: ' + e.message, 'alert-circle'); }
  setTimeout(() => { icon.style.animation = ''; }, 3000);
}

// ── OVERVIEW ───────────────────────────────────────────
async function loadOverview() {
  try {
    const r = await fetch(`/api/overview?days=${currentDays}`);
    const d = await r.json();
    renderAlerts(d.alerts);
    renderCards(d);
    renderKpiTargets(d);
    if (d.fetched_at) {
      const dt = new Date(d.fetched_at);
      document.getElementById('last-updated').textContent =
        'Updated: ' + dt.toLocaleDateString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
    }
    // Charts
    renderClicksChart(d);
    loadTrafficChartForOverview();
    renderPositionChart(d);
  } catch(e) { console.error(e); }
}

function renderAlerts(alerts) {
  const bar = document.getElementById('alert-bar');
  bar.innerHTML = alerts.map(a => `
    <div class="alert ${a.level}">
      <i data-lucide="${a.icon}"></i>
      ${a.msg}
    </div>`).join('');
  lucide.createIcons();
}

function renderCards(d) {
  const {gsc, gsc_prev, ga4, ga4_prev} = d;
  const cards = [
    {label:'Total Clicks',    val:fmt(gsc.clicks),     prev:gsc_prev.clicks,
     cur:gsc.clicks, icon:'mouse-pointer-click', color:'blue'},
    {label:'Impressions',     val:fmtK(gsc.impressions), prev:gsc_prev.impressions,
     cur:gsc.impressions, icon:'eye', color:'blue'},
    {label:'Avg CTR',         val:gsc.ctr+'%',         prev:null, icon:'percent', color:'blue'},
    {label:'Avg Position',    val:gsc.position,        prev:gsc_prev.position,
     cur:gsc.position, icon:'map-pin', color:'yellow', invert:true},
    {label:'Organic Sessions',val:fmt(ga4.organic),    prev:ga4_prev.organic,
     cur:ga4.organic, icon:'trending-up', color:'green'},
    {label:'Total Sessions',  val:fmt(ga4.sessions),   prev:ga4_prev.sessions,
     cur:ga4.sessions, icon:'users', color:'green'},
    {label:'Keywords Total',  val:fmt(gsc.keywords),   prev:gsc_prev.keywords,
     cur:gsc.keywords, icon:'search', color:'purple'},
    {label:'Keywords Top 10', val:gsc.top10,           prev:null, icon:'award', color:'green'},
    {label:'Page 2 Keywords', val:gsc.page2,           prev:null, icon:'layers', color:'yellow'},
  ];

  document.getElementById('overview-cards').innerHTML = cards.map(c => {
    let changeHtml = '';
    if (c.prev !== undefined && c.prev !== null && c.cur !== undefined) {
      const pct = c.prev > 0 ? ((c.cur - c.prev) / c.prev * 100).toFixed(1) : null;
      if (pct !== null) {
        const improved = c.invert ? parseFloat(pct) < 0 : parseFloat(pct) > 0;
        const cls = improved ? 'up' : parseFloat(pct) === 0 ? 'flat' : 'down';
        const arrow = improved ? 'trending-up' : parseFloat(pct) === 0 ? 'minus' : 'trending-down';
        changeHtml = `<div class="card-change ${cls}">
          <i data-lucide="${arrow}"></i> ${Math.abs(pct)}% vs prev period
        </div>`;
      }
    }
    return `<div class="card">
      <div class="card-icon ${c.color}"><i data-lucide="${c.icon}"></i></div>
      <div class="card-label">${c.label}</div>
      <div class="card-value">${c.val}</div>
      ${changeHtml}
    </div>`;
  }).join('');
  lucide.createIcons();
}

function renderKpiTargets(d) {
  const {gsc, ga4, baselines, targets} = d;
  const items = [
    {label:'Organic Traffic/Month', cur:ga4.organic, baseline:baselines.organic_traffic,
     m1:targets.organic_month1, m3:targets.organic_month3, m6:targets.organic_month6},
    {label:'Keywords Top 50', cur:gsc.top50, baseline:baselines.keywords_top50,
     m1:targets.keywords_top50_month1, m3:targets.keywords_top50_month3, m6:targets.keywords_top50_month6},
    {label:'Keywords Top 10', cur:gsc.top10, baseline:baselines.keywords_top10,
     m1:targets.keywords_top10_month1, m3:targets.keywords_top10_month3, m6:targets.keywords_top10_month6},
    {label:'GSC Clicks/28 Days', cur:gsc.clicks, baseline:baselines.clicks,
     m1:targets.clicks_month1, m3:targets.clicks_month3, m6:targets.clicks_month6},
    {label:'Total GA4 Sessions', cur:ga4.sessions, baseline:baselines.sessions,
     m1:targets.sessions_month1, m3:targets.sessions_month3, m6:targets.sessions_month6},
  ];

  document.getElementById('kpi-targets').innerHTML =
    '<div style="grid-column:1/-1"><h3 style="font-size:15px;font-weight:700;margin-bottom:16px">KPI Target Tracker — 6 Month Plan</h3></div>' +
    items.map(item => {
      const pct1 = Math.min(100, Math.round((item.cur / item.m1) * 100));
      const pct3 = Math.min(100, Math.round((item.cur / item.m3) * 100));
      const color = item.cur >= item.m1 ? 'green' : item.cur >= item.m1 * 0.7 ? 'yellow' : 'red';
      const status = item.cur >= item.m1 ? 'On Track' : item.cur >= item.m1 * 0.7 ? 'Behind' : 'Critical';
      const badgeCls = item.cur >= item.m1 ? 'badge-green' : item.cur >= item.m1 * 0.7 ? 'badge-yellow' : 'badge-red';
      return `<div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">${item.label}</span>
          <span class="badge ${badgeCls}">${status}</span>
        </div>
        <div class="kpi-current">${fmt(item.cur)}</div>
        <div class="progress-wrap">
          <div class="progress-label">
            <span>Baseline: ${fmt(item.baseline)}</span>
            <span>M1 Target: ${fmt(item.m1)}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill ${color}" style="width:${pct1}%"></div>
          </div>
        </div>
        <div class="kpi-targets-row">
          <div class="kpi-target">
            <div class="kpi-target-val">${fmt(item.m1)}</div>
            <div class="kpi-target-lbl">Month 1</div>
          </div>
          <div class="kpi-target">
            <div class="kpi-target-val">${fmt(item.m3)}</div>
            <div class="kpi-target-lbl">Month 3</div>
          </div>
          <div class="kpi-target">
            <div class="kpi-target-val">${fmt(item.m6)}</div>
            <div class="kpi-target-lbl">Month 6</div>
          </div>
        </div>
      </div>`;
    }).join('');
}

function renderClicksChart(d) {
  // Simple bar from snapshots — or just show a period summary
  const s = d.gsc;
  const p = d.gsc_prev;
  const trace1 = {x:['Previous Period','Current Period'], y:[p.clicks, s.clicks],
    type:'bar', name:'Clicks',
    marker:{color:['#e8eaed','#1a73e8']}, text:[p.clicks, s.clicks],
    textposition:'outside'};
  const trace2 = {x:['Previous Period','Current Period'],
    y:[p.impressions, s.impressions],
    type:'bar', name:'Impressions', yaxis:'y2',
    marker:{color:['#f1f3f4','#34a853']}, opacity:.7};
  Plotly.newPlot('chart-clicks', [trace1, trace2], {
    margin:{t:10,b:40,l:40,r:40},
    plot_bgcolor:'white', paper_bgcolor:'white',
    legend:{orientation:'h', y:-0.2},
    yaxis:{title:'Clicks', gridcolor:'#f1f3f4'},
    yaxis2:{title:'Impressions', overlaying:'y', side:'right', gridcolor:'#f1f3f4'},
    font:{family:'DM Sans',size:12, color:'#5f6368'},
    bargap:0.3
  }, {responsive:true, displayModeBar:false});
}

async function loadTrafficChartForOverview() {
  try {
    const r = await fetch('/api/traffic');
    const d = await r.json();
    const channels = d.channels || [];
    const labels = channels.map(c => c.channel);
    const values = channels.map(c => c.sessions);
    Plotly.newPlot('chart-channels', [{
      labels, values, type:'pie', hole:0.5,
      marker:{colors:['#1a73e8','#34a853','#fbbc04','#ea4335','#9aa0a6','#7c3aed']},
      textinfo:'label+percent', textfont:{size:11}
    }], {
      margin:{t:10,b:10,l:10,r:10},
      showlegend:false,
      paper_bgcolor:'white'
    }, {responsive:true, displayModeBar:false});
  } catch(e) {}
}

function renderPositionChart(d) {
  const {gsc} = d;
  Plotly.newPlot('chart-positions', [{
    x:['Top 3','4–10','11–20','21–50','50+'],
    y:[
      gsc.top10 > 3 ? 3 : gsc.top10,  // rough
      Math.max(0, gsc.top10 - 3),
      gsc.page2,
      Math.max(0, gsc.top50 - gsc.top10 - gsc.page2),
      Math.max(0, gsc.keywords - gsc.top50)
    ],
    type:'bar',
    marker:{color:['#34a853','#1a73e8','#fbbc04','#9aa0a6','#ea4335']},
    text:['Top 3','Page 1','Page 2','Page 3-5','Page 5+'],
    textposition:'outside'
  }], {
    margin:{t:10,b:40,l:40,r:10},
    plot_bgcolor:'white', paper_bgcolor:'white',
    font:{family:'DM Sans',size:12,color:'#5f6368'},
    yaxis:{gridcolor:'#f1f3f4'},
    xaxis:{gridcolor:'#f1f3f4'},
    bargap:.3
  }, {responsive:true, displayModeBar:false});
}

// ── KEYWORDS ───────────────────────────────────────────
async function loadKeywords() {
  try {
    const r = await fetch(`/api/keywords?days=${currentDays}`);
    kwData = await r.json();
    document.getElementById('kw-total').textContent = kwData.total + ' keywords';
    renderKwTable('all', kwData.keywords);
    renderImprovedTable(kwData.improved);
    renderDeclinedTable(kwData.declined);
    renderSimpleKwTable('page2', kwData.page2, ['keyword','position','impressions','clicks','ctr']);
    renderSimpleKwTable('dying', kwData.dying, ['keyword','position','impressions','clicks']);
    renderSimpleKwTable('low_ctr', kwData.low_ctr, ['keyword','impressions','clicks','ctr','position']);
  } catch(e) { console.error(e); }
}

function statusBadge(s) {
  const map = {
    top3:'<span class="badge badge-green">Top 3</span>',
    top10:'<span class="badge badge-blue">Top 10</span>',
    page2:'<span class="badge badge-yellow">Page 2</span>',
    ok:'<span class="badge badge-gray">OK</span>',
    dying:'<span class="badge badge-red">Dying</span>',
    page3:'<span class="badge badge-gray">Page 3+</span>',
  };
  return map[s] || '';
}

function changeCell(chg) {
  if (!chg || chg === 0) return '<span class="chg flat"><i data-lucide="minus"></i>—</span>';
  if (chg > 0) return `<span class="chg up"><i data-lucide="trending-up"></i>+${chg}</span>`;
  return `<span class="chg down"><i data-lucide="trending-down"></i>${chg}</span>`;
}

function renderKwTable(id, kws) {
  document.getElementById('kw-all-body').innerHTML = (kws||[]).slice(0,200).map(r => `
    <tr>
      <td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.keyword}</td>
      <td><strong>${r.position}</strong></td>
      <td>${changeCell(r.change)}</td>
      <td>${r.clicks}</td>
      <td>${fmtK(r.impressions)}</td>
      <td>${r.ctr}%</td>
      <td>${statusBadge(r.status)}</td>
    </tr>`).join('');
  lucide.createIcons();
}

function renderImprovedTable(kws) {
  document.getElementById('kw-improved-body').innerHTML = (kws||[]).map(r => `
    <tr>
      <td>${r.keyword}</td>
      <td style="color:#9aa0a6">${r.prev_pos || '—'}</td>
      <td><strong>${r.position}</strong></td>
      <td><span class="chg up"><i data-lucide="trending-up"></i>+${r.change} positions</span></td>
      <td>${r.clicks}</td>
    </tr>`).join('');
  lucide.createIcons();
}

function renderDeclinedTable(kws) {
  document.getElementById('kw-declined-body').innerHTML = (kws||[]).map(r => `
    <tr>
      <td>${r.keyword}</td>
      <td style="color:#9aa0a6">${r.prev_pos || '—'}</td>
      <td><strong>${r.position}</strong></td>
      <td><span class="chg down"><i data-lucide="trending-down"></i>${r.change} positions</span></td>
      <td>${fmtK(r.impressions)}</td>
    </tr>`).join('');
  lucide.createIcons();
}

function renderSimpleKwTable(id, kws, cols) {
  const colMap = {
    keyword: r => `<td style="max-width:260px;overflow:hidden;text-overflow:ellipsis">${r.keyword}</td>`,
    position: r => `<td><strong>${r.position}</strong></td>`,
    impressions: r => `<td>${fmtK(r.impressions)}</td>`,
    clicks: r => `<td>${r.clicks}</td>`,
    ctr: r => `<td>${r.ctr}%</td>`,
  };
  document.getElementById('kw-'+id+'-body').innerHTML = (kws||[]).slice(0,100).map(r =>
    '<tr>' + cols.map(c => colMap[c] ? colMap[c](r) : '<td>—</td>').join('') + '</tr>'
  ).join('');
}

function showKwTab(tab) {
  document.querySelectorAll('#section-keywords .tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#section-keywords .sub-section').forEach(s => s.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('kw-'+tab).classList.add('active');
}

// ── TRAFFIC ────────────────────────────────────────────
async function loadTraffic() {
  try {
    const r = await fetch(`/api/traffic?days=${currentDays}`);
    trafficData = await r.json();
    renderChannels(trafficData.channels);
    renderPages(trafficData.pages);
    renderDailyChart(trafficData.daily);
    renderChannelPie(trafficData.channels);
  } catch(e) { console.error(e); }
}

function renderChannels(channels) {
  document.getElementById('channel-body').innerHTML = (channels||[]).map(ch => {
    const chg = ch.change;
    const chgHtml = chg !== null
      ? `<span class="chg ${chg >= 0 ? 'up':'down'}">
          <i data-lucide="${chg >= 0 ? 'trending-up':'trending-down'}"></i>
          ${chg >= 0 ? '+':''}${chg}%
        </span>`
      : '—';
    return `<tr>
      <td><strong>${ch.channel}</strong></td>
      <td>${fmt(ch.sessions)}</td>
      <td>${fmt(ch.users)}</td>
      <td>${ch.bounce}%</td>
      <td>${fmtSec(ch.duration)}</td>
      <td>${chgHtml}</td>
    </tr>`;
  }).join('');
  lucide.createIcons();
}

function renderPages(pages) {
  document.getElementById('pages-body').innerHTML = (pages||[]).map(p => `
    <tr>
      <td style="max-width:320px;overflow:hidden;text-overflow:ellipsis;
        white-space:nowrap;color:#1a73e8">${p.page}</td>
      <td>${fmt(p.sessions)}</td>
      <td>${fmt(p.users)}</td>
      <td>${p.bounce}%</td>
    </tr>`).join('');
}

function renderDailyChart(daily) {
  const dates = (daily||[]).map(d => d.date);
  const sessions = (daily||[]).map(d => d.sessions);
  Plotly.newPlot('chart-daily', [{
    x: dates, y: sessions, type:'scatter', fill:'tozeroy',
    line:{color:'#1a73e8', width:2},
    fillcolor:'rgba(26,115,232,0.08)',
    name:'Sessions'
  }], {
    margin:{t:10,b:40,l:40,r:10},
    plot_bgcolor:'white', paper_bgcolor:'white',
    font:{family:'DM Sans',size:12,color:'#5f6368'},
    xaxis:{gridcolor:'#f1f3f4'},
    yaxis:{gridcolor:'#f1f3f4'},
  }, {responsive:true, displayModeBar:false});
}

function renderChannelPie(channels) {
  Plotly.newPlot('chart-channel-pie', [{
    labels: channels.map(c => c.channel),
    values: channels.map(c => c.sessions),
    type:'pie', hole:0.45,
    marker:{colors:['#1a73e8','#34a853','#fbbc04','#ea4335','#9aa0a6','#7c3aed']},
    textinfo:'label+percent'
  }], {
    margin:{t:10,b:10,l:10,r:10},
    showlegend:false, paper_bgcolor:'white'
  }, {responsive:true, displayModeBar:false});
}

// ── COMPARE ────────────────────────────────────────────
async function loadCompare() {
  try {
    const r = await fetch('/api/compare');
    const d = await r.json();
    renderCompareLive(d);
    renderCompareBaseline(d);
    renderTrendCharts(d.trend);
  } catch(e) { console.error(e); }
}

function renderCompareLive(d) {
  const s = d.current_gsc;
  const g = d.current_ga4;
  const snaps = d.snapshots;
  const prev = snaps && snaps.length > 1 ? snaps[1] : null;

  const rows = [
    ['Clicks', s.total_clicks, prev ? prev.clicks : null],
    ['Impressions', s.total_impressions, prev ? prev.impressions : null],
    ['Avg Position', s.avg_position, prev ? prev.avg_position : null],
    ['Total Keywords', s.total_keywords, prev ? prev.keywords_total : null],
    ['Keywords Top 10', s.keywords_top10, null],
    ['Organic Sessions', g.organic_sessions, prev ? prev.organic_sessions : null],
    ['Total Sessions', g.total_sessions, prev ? prev.total_sessions : null],
  ];

  document.getElementById('compare-live').innerHTML = rows.map(([label, cur, prev]) => {
    const chgHtml = (prev && prev > 0)
      ? (() => {
          const p = ((cur - prev) / prev * 100).toFixed(1);
          const up = parseFloat(p) > 0;
          return `<span class="chg ${up?'up':'down'}">
            <i data-lucide="${up?'trending-up':'trending-down'}"></i>
            ${up?'+':''}${p}%
          </span>`;
        })()
      : '';
    return `<div class="compare-row">
      <span class="compare-metric">${label}</span>
      <div class="compare-values">
        ${prev !== null ? `<span class="compare-val period-b">${fmt(prev)}</span><span style="color:#e8eaed">→</span>` : ''}
        <span class="compare-val period-a">${fmt(cur)}</span>
        ${chgHtml}
      </div>
    </div>`;
  }).join('');
  lucide.createIcons();
}

function renderCompareBaseline(d) {
  const s = d.current_gsc;
  const g = d.current_ga4;
  const base = {
    'Organic Traffic': [g.organic_sessions, 29],
    'Keywords Top 50': [s.keywords_top50, 103],
    'Keywords Top 10': [s.keywords_top10, 5],
    'GSC Clicks': [s.total_clicks, 51],
    'Total Sessions': [g.total_sessions, 70],
    'Avg Position': [s.avg_position, 30.5],
  };

  document.getElementById('compare-baseline').innerHTML = Object.entries(base).map(([label, [cur, baseline]]) => {
    const better = label === 'Avg Position' ? cur < baseline : cur > baseline;
    const pct = baseline > 0 ? ((cur - baseline) / baseline * 100).toFixed(1) : 0;
    return `<div class="compare-row">
      <span class="compare-metric">${label}</span>
      <div class="compare-values">
        <span class="compare-val period-b">${fmt(baseline)}</span>
        <span style="color:#e8eaed">→</span>
        <span class="compare-val period-a">${fmt(cur)}</span>
        <span class="chg ${better?'up':'down'}">
          <i data-lucide="${better?'trending-up':'trending-down'}"></i>
          ${pct > 0 ? '+':''}${pct}%
        </span>
      </div>
    </div>`;
  }).join('');
  lucide.createIcons();
}

function renderTrendCharts(trend) {
  if (!trend || !trend.length) return;
  const dates = trend.map(t => t.created_at ? t.created_at.slice(0,10) : '');
  Plotly.newPlot('chart-trend', [
    {x:dates, y:trend.map(t=>t.clicks), name:'Clicks',
     type:'scatter', line:{color:'#1a73e8',width:2}, mode:'lines+markers'},
    {x:dates, y:trend.map(t=>t.organic_sessions), name:'Organic Sessions',
     type:'scatter', line:{color:'#34a853',width:2}, mode:'lines+markers'},
    {x:dates, y:trend.map(t=>t.total_sessions), name:'Total Sessions',
     type:'scatter', line:{color:'#fbbc04',width:2}, mode:'lines+markers'},
  ], {
    margin:{t:10,b:40,l:40,r:10},
    plot_bgcolor:'white', paper_bgcolor:'white',
    legend:{orientation:'h', y:-0.2},
    font:{family:'DM Sans',size:12,color:'#5f6368'},
    xaxis:{gridcolor:'#f1f3f4'},
    yaxis:{gridcolor:'#f1f3f4'},
  }, {responsive:true, displayModeBar:false});

  Plotly.newPlot('chart-kw-trend', [
    {x:dates, y:trend.map(t=>t.keywords_total), name:'Total Keywords',
     type:'scatter', fill:'tozeroy', fillcolor:'rgba(26,115,232,.08)',
     line:{color:'#1a73e8',width:2}},
    {x:dates, y:trend.map(t=>t.keywords_top10), name:'Top 10',
     type:'scatter', line:{color:'#34a853',width:2}},
  ], {
    margin:{t:10,b:40,l:40,r:10},
    plot_bgcolor:'white', paper_bgcolor:'white',
    legend:{orientation:'h', y:-0.2},
    font:{family:'DM Sans',size:12,color:'#5f6368'},
    xaxis:{gridcolor:'#f1f3f4'},
    yaxis:{gridcolor:'#f1f3f4'},
  }, {responsive:true, displayModeBar:false});
}

// ── ACCOUNTABILITY ─────────────────────────────────────
async function loadAccountability() {
  const month = document.getElementById('acc-month').value;
  try {
    const r = await fetch(`/api/accountability?month=${month}`);
    const d = await r.json();
    const acc = d.accountability;
    const live = d.live;
    const targets = d.targets;
    const baselines = d.baselines;

    if (acc) {
      document.getElementById('acc-backlinks').value = acc.backlinks_built || '';
      document.getElementById('acc-backlink-urls').value = acc.backlink_urls || '';
      document.getElementById('acc-posts').value = acc.blog_posts || '';
      document.getElementById('acc-post-titles').value = acc.blog_titles || '';
      document.getElementById('acc-da').value = acc.da_score || '';
      document.getElementById('acc-fixes').value = acc.technical_fixes || '';
      document.getElementById('acc-notes').value = acc.notes || '';
    }

    // Live metrics
    document.getElementById('acc-live-metrics').innerHTML = [
      ['GSC Clicks (this period)', live.clicks, baselines.clicks, targets.clicks_month1],
      ['Total Keywords', live.keywords, baselines.keywords_top50, targets.keywords_top50_month1],
      ['Keywords Top 10', live.top10, baselines.keywords_top10, targets.keywords_top10_month1],
      ['Organic Sessions', live.organic, baselines.organic_traffic, targets.organic_month1],
      ['Total GA4 Sessions', live.sessions, baselines.sessions, targets.sessions_month1],
    ].map(([label, cur, base, target]) => {
      const pct = target > 0 ? Math.min(100, Math.round(cur / target * 100)) : 0;
      const color = pct >= 100 ? 'green' : pct >= 70 ? 'yellow' : 'red';
      return `<div class="progress-wrap">
        <div class="progress-label">
          <span>${label}: <strong>${fmt(cur)}</strong></span>
          <span>Target: ${fmt(target)}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill ${color}" style="width:${pct}%"></div>
        </div>
      </div>`;
    }).join('');

    // Target progress
    document.getElementById('acc-targets').innerHTML = `
      <div class="compare-row">
        <span class="compare-metric">Month 1 Organic Target</span>
        <span class="compare-val">${live.organic} / ${targets.organic_month1}</span>
      </div>
      <div class="compare-row">
        <span class="compare-metric">Month 1 Keywords Target</span>
        <span class="compare-val">${live.keywords} / ${targets.keywords_top50_month1}</span>
      </div>
      <div class="compare-row">
        <span class="compare-metric">Month 1 Sessions Target</span>
        <span class="compare-val">${live.sessions} / ${targets.sessions_month1}</span>
      </div>
      <div class="compare-row">
        <span class="compare-metric">Month 1 Clicks Target</span>
        <span class="compare-val">${live.clicks} / ${targets.clicks_month1}</span>
      </div>`;

    // Red flags
    const backlinks = acc ? (acc.backlinks_built || 0) : 0;
    const posts = acc ? (acc.blog_posts || 0) : 0;
    const flags = [];
    if (backlinks < 5) flags.push({bad:true, msg:`Only ${backlinks} backlinks built — target is 20-30/month`});
    if (posts < 2) flags.push({bad:true, msg:`Only ${posts} blog posts — target is 4+/month`});
    if (live.organic < 50) flags.push({bad:true, msg:'Organic traffic still critically low (under 50 sessions)'});
    if (live.top10 < 8) flags.push({bad:true, msg:`Only ${live.top10} keywords in Top 10 — needs to reach 8-12`});
    if (backlinks >= 15) flags.push({bad:false, msg:`${backlinks} backlinks built — good progress!`});
    if (posts >= 4) flags.push({bad:false, msg:`${posts} blog posts published — on track!`});
    if (live.organic >= 50) flags.push({bad:false, msg:`Organic traffic at ${live.organic} — moving in right direction`});

    document.getElementById('red-flags').innerHTML = flags.map(f => `
      <div class="alert ${f.bad ? 'critical' : 'good'}" style="margin-bottom:8px">
        <i data-lucide="${f.bad ? 'alert-triangle' : 'check-circle'}"></i>
        ${f.msg}
      </div>`).join('');
    lucide.createIcons();
  } catch(e) { console.error(e); }
}

async function saveAccountability() {
  const month = document.getElementById('acc-month').value;
  const data = {
    backlinks_built: parseInt(document.getElementById('acc-backlinks').value) || 0,
    backlink_urls:   document.getElementById('acc-backlink-urls').value,
    blog_posts:      parseInt(document.getElementById('acc-posts').value) || 0,
    blog_titles:     document.getElementById('acc-post-titles').value,
    da_score:        parseInt(document.getElementById('acc-da').value) || 0,
    technical_fixes: document.getElementById('acc-fixes').value,
    notes:           document.getElementById('acc-notes').value,
  };
  try {
    await fetch(`/api/accountability?month=${month}`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(data)
    });
    showToast('Monthly record saved!', 'check-circle');
  } catch(e) { showToast('Error saving: ' + e.message, 'alert-circle'); }
}

// ── REPORTS ────────────────────────────────────────────
async function loadReports() {
  try {
    const r = await fetch('/api/reports');
    const d = await r.json();
    const reports = d.reports || [];
    if (!reports.length) {
      document.getElementById('report-list').innerHTML = `
        <div class="empty">
          <i data-lucide="file-text" style="display:block;margin:0 auto 12px"></i>
          No reports yet. Generate your first report above.
        </div>`;
      lucide.createIcons();
      return;
    }
    document.getElementById('report-list').innerHTML =
      '<div class="report-list">' +
      reports.map(rep => {
        const dt = new Date(rep.created_at);
        return `<div class="report-item">
          <div class="report-item-left">
            <div class="report-icon"><i data-lucide="file-text"></i></div>
            <div>
              <div class="report-title">${rep.title || 'SEO Report'}</div>
              <div class="report-meta">
                ${dt.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'})}
                &nbsp;·&nbsp; ${rep.period || '28d'}
              </div>
            </div>
          </div>
          <div class="report-actions">
            <button class="btn-sm btn-primary" onclick="downloadReport('${rep.filename}')">
              <i data-lucide="download"></i> Download
            </button>
          </div>
        </div>`;
      }).join('') + '</div>';
    lucide.createIcons();
  } catch(e) { console.error(e); }
}

async function generatePDF() {
  showToast('Generating PDF report...', 'loader');
  try {
    const r = await fetch('/api/generate-pdf', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({days: currentDays})
    });
    const d = await r.json();
    if (d.ok) {
      showToast('PDF ready! Downloading...', 'check-circle');
      setTimeout(() => downloadReport(d.filename), 500);
      setTimeout(loadReports, 1000);
    } else {
      showToast('Error: ' + d.error, 'alert-circle');
    }
  } catch(e) { showToast('Error: ' + e.message, 'alert-circle'); }
}

function downloadReport(filename) {
  window.open('/api/download-report/' + filename, '_blank');
}

// ── HELPERS ────────────────────────────────────────────
function fmt(n) {
  if (n === null || n === undefined) return '—';
  if (typeof n === 'string') n = parseFloat(n);
  if (isNaN(n)) return '—';
  return n.toLocaleString('en-US');
}
function fmtK(n) {
  if (!n) return '0';
  n = parseInt(n);
  if (n >= 1000) return (n/1000).toFixed(1) + 'K';
  return n.toString();
}
function fmtSec(s) {
  s = Math.round(s);
  const m = Math.floor(s / 60), sec = s % 60;
  return m + 'm ' + sec + 's';
}

function showToast(msg, icon) {
  const t = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  const iconEl = document.getElementById('toast-icon');
  iconEl.setAttribute('data-lucide', icon || 'info');
  t.classList.add('show');
  lucide.createIcons();
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
}
</script>
</body>
</html>'''

if __name__ == '__main__':
    print("=" * 50)
    print("  SEO DASHBOARD STARTING")
    print("  Open: http://localhost:5000")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=False, port=5000, host='0.0.0.0')
