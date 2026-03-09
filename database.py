import sqlite3
import json
import os
from datetime import datetime

DB_PATH = 'data/seo_history.db'

def get_connection():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        period TEXT NOT NULL,
        date_from TEXT, date_to TEXT,
        clicks INTEGER DEFAULT 0,
        impressions INTEGER DEFAULT 0,
        ctr REAL DEFAULT 0,
        avg_position REAL DEFAULT 0,
        keywords_total INTEGER DEFAULT 0,
        keywords_top10 INTEGER DEFAULT 0,
        keywords_top50 INTEGER DEFAULT 0,
        organic_sessions INTEGER DEFAULT 0,
        total_sessions INTEGER DEFAULT 0,
        backlinks INTEGER DEFAULT 0,
        da_score INTEGER DEFAULT 0,
        blog_posts INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS keyword_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date TEXT NOT NULL,
        keyword TEXT NOT NULL,
        position REAL DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        impressions INTEGER DEFAULT 0,
        ctr REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        title TEXT,
        period TEXT,
        filename TEXT,
        filepath TEXT,
        data_json TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS accountability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT UNIQUE,
        backlinks_built INTEGER DEFAULT 0,
        backlink_urls TEXT DEFAULT '',
        blog_posts INTEGER DEFAULT 0,
        blog_titles TEXT DEFAULT '',
        da_score INTEGER DEFAULT 0,
        technical_fixes TEXT DEFAULT '',
        notes TEXT DEFAULT ''
    )''')
    conn.commit()
    conn.close()

def save_snapshot(data):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO snapshots
        (created_at,period,date_from,date_to,clicks,impressions,ctr,avg_position,
         keywords_total,keywords_top10,keywords_top50,organic_sessions,total_sessions)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (now, data.get('period','28d'), data.get('date_from'), data.get('date_to'),
         data.get('clicks',0), data.get('impressions',0), data.get('ctr',0),
         data.get('avg_position',0), data.get('keywords_total',0),
         data.get('keywords_top10',0), data.get('keywords_top50',0),
         data.get('organic_sessions',0), data.get('total_sessions',0)))
    conn.commit()
    conn.close()

def save_keyword_history(keywords, snapshot_date=None):
    if not snapshot_date:
        snapshot_date = datetime.now().strftime('%Y-%m-%d')
    conn = get_connection()
    c = conn.cursor()
    for kw in keywords[:500]:
        keys = kw.get('keys', [])
        keyword = keys[0] if keys else ''
        if keyword:
            c.execute('''INSERT INTO keyword_history
                (snapshot_date,keyword,position,clicks,impressions,ctr)
                VALUES (?,?,?,?,?,?)''',
                (snapshot_date, keyword,
                 kw.get('position',0), kw.get('clicks',0),
                 kw.get('impressions',0), kw.get('ctr',0)))
    conn.commit()
    conn.close()

def get_snapshots(limit=12):
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM snapshots ORDER BY created_at DESC LIMIT ?', (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_keyword_positions(keyword, limit=12):
    conn = get_connection()
    rows = conn.execute(
        '''SELECT snapshot_date, position, clicks, impressions
           FROM keyword_history WHERE keyword=?
           ORDER BY snapshot_date DESC LIMIT ?''',
        (keyword, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_reports():
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM reports ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_report(title, period, filename, filepath, data):
    conn = get_connection()
    conn.execute('''INSERT INTO reports
        (created_at,title,period,filename,filepath,data_json)
        VALUES (?,?,?,?,?,?)''',
        (datetime.now().isoformat(), title, period,
         filename, filepath, json.dumps(data)))
    conn.commit()
    conn.close()

def get_accountability(month=None):
    if not month:
        month = datetime.now().strftime('%Y-%m')
    conn = get_connection()
    row = conn.execute(
        'SELECT * FROM accountability WHERE month=?', (month,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}

def save_accountability(month, data):
    conn = get_connection()
    conn.execute('''INSERT OR REPLACE INTO accountability
        (month,backlinks_built,backlink_urls,blog_posts,blog_titles,
         da_score,technical_fixes,notes)
        VALUES (?,?,?,?,?,?,?,?)''',
        (month, data.get('backlinks_built',0), data.get('backlink_urls',''),
         data.get('blog_posts',0), data.get('blog_titles',''),
         data.get('da_score',0), data.get('technical_fixes',''),
         data.get('notes','')))
    conn.commit()
    conn.close()

def get_trend_data(months=6):
    conn = get_connection()
    rows = conn.execute(
        '''SELECT * FROM snapshots
           ORDER BY created_at DESC LIMIT ?''', (months,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

init_database()
