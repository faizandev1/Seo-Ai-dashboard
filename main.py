import os, json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from database import save_snapshot, save_keyword_history

def run_fetch(days=28):
    print("=" * 55)
    print("  SEO AI DASHBOARD — DATA FETCH")
    print("=" * 55)
    print(f"  Site   : {os.getenv('GSC_PROPERTY_URL')}")
    print(f"  Period : Last {days} days")
    print(f"  Time   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    gsc_ok, ga4_ok = False, False
    gsc_data, ga4_data = {}, {}

    print("\n[1/2] Google Search Console...")
    try:
        from fetchers.fetch_gsc import fetch_gsc_data
        gsc_data = fetch_gsc_data(days)
        gsc_ok = True
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[2/2] Google Analytics 4...")
    try:
        from fetchers.fetch_ga4 import fetch_ga4_data
        ga4_data = fetch_ga4_data(days)
        ga4_ok = True
    except Exception as e:
        print(f"  ERROR: {e}")

    # Save snapshot to database
    if gsc_ok or ga4_ok:
        s  = gsc_data.get('summary', {})
        gs = ga4_data.get('summary', {})
        p  = gsc_data.get('period', {})
        save_snapshot({
            'period': f"{days}d",
            'date_from': p.get('start'),
            'date_to': p.get('end'),
            'clicks': s.get('total_clicks', 0),
            'impressions': s.get('total_impressions', 0),
            'ctr': s.get('avg_ctr', 0),
            'avg_position': s.get('avg_position', 0),
            'keywords_total': s.get('total_keywords', 0),
            'keywords_top10': s.get('keywords_top10', 0),
            'keywords_top50': s.get('keywords_top50', 0),
            'organic_sessions': gs.get('organic_sessions', 0),
            'total_sessions': gs.get('total_sessions', 0),
        })
        if gsc_ok:
            save_keyword_history(gsc_data.get('queries', []))

    print("\n" + "=" * 55)
    print("  FETCH COMPLETE")
    print("=" * 55)
    if gsc_ok:
        s = gsc_data.get('summary', {})
        print(f"  GSC Keywords   : {s.get('total_keywords', 0)}")
        print(f"  GSC Clicks     : {s.get('total_clicks', 0)}")
        print(f"  GSC Impressions: {s.get('total_impressions', 0):,}")
        print(f"  Avg Position   : {s.get('avg_position', 0)}")
    if ga4_ok:
        gs = ga4_data.get('summary', {})
        print(f"  GA4 Sessions   : {gs.get('total_sessions', 0)}")
        print(f"  Organic Traffic: {gs.get('organic_sessions', 0)}")
    if not gsc_ok: print("  GSC            : FAILED")
    if not ga4_ok: print("  GA4            : FAILED")
    print("=" * 55)
    print("  Data saved. Run dashboard.py to view.")
    print()
    return gsc_data, ga4_data

if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    run_fetch(days)
