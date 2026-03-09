import os, json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

def get_service():
    creds = service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY', 'service-account-key.json'), scopes=SCOPES)
    return build('searchconsole', 'v1', credentials=creds)

def get_site_url(service):
    configured = os.getenv('GSC_PROPERTY_URL', '')
    sites = service.sites().list().execute()
    available = [s['siteUrl'] for s in sites.get('siteEntry', [])]
    if not available:
        raise Exception("No GSC properties found. Add service account email to Search Console.")
    if configured in available:
        return configured
    for v in [configured,
              configured.replace('http://','https://'),
              configured.replace('https://','http://'),
              configured.rstrip('/'),
              configured.rstrip('/')+'/']:
        if v in available:
            return v
    return available[0]

def fetch_gsc_data(days=28):
    print(f"Connecting to Google Search Console ({days} days)...")
    service = get_service()
    site_url = get_site_url(service)
    print(f"Property: {site_url}")

    end   = datetime.now()
    start = end - timedelta(days=days)
    end_str   = end.strftime('%Y-%m-%d')
    start_str = start.strftime('%Y-%m-%d')

    # Previous period for comparison
    prev_end   = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days)

    def query(start_d, end_d, dimension, limit=1000):
        resp = service.searchanalytics().query(
            siteUrl=site_url,
            body={'startDate': start_d, 'endDate': end_d,
                  'dimensions': [dimension], 'rowLimit': limit}
        ).execute()
        return resp.get('rows', [])

    print("Fetching current period data...")
    queries_cur = query(start_str, end_str, 'query')
    pages_cur   = query(start_str, end_str, 'page')

    print("Fetching previous period for comparison...")
    queries_prev = query(prev_start.strftime('%Y-%m-%d'),
                         prev_end.strftime('%Y-%m-%d'), 'query')

    os.makedirs('data/gsc', exist_ok=True)

    gsc_data = {
        'fetched_at': datetime.now().isoformat(),
        'site': site_url,
        'period': {'days': days, 'start': start_str, 'end': end_str},
        'prev_period': {
            'start': prev_start.strftime('%Y-%m-%d'),
            'end': prev_end.strftime('%Y-%m-%d')
        },
        'queries': queries_cur,
        'queries_prev': queries_prev,
        'pages': pages_cur,
        'summary': {
            'total_clicks':      sum(r.get('clicks',0) for r in queries_cur),
            'total_impressions':  sum(r.get('impressions',0) for r in queries_cur),
            'avg_ctr':           round(sum(r.get('ctr',0) for r in queries_cur) / max(len(queries_cur),1) * 100, 2),
            'avg_position':      round(sum(r.get('position',0) for r in queries_cur) / max(len(queries_cur),1), 1),
            'total_keywords':    len(queries_cur),
            'keywords_top10':    sum(1 for r in queries_cur if r.get('position',99) <= 10),
            'keywords_top50':    sum(1 for r in queries_cur if r.get('position',99) <= 50),
            'keywords_page2':    sum(1 for r in queries_cur if 10 < r.get('position',99) <= 20),
        },
        'prev_summary': {
            'total_clicks':      sum(r.get('clicks',0) for r in queries_prev),
            'total_impressions':  sum(r.get('impressions',0) for r in queries_prev),
            'avg_position':      round(sum(r.get('position',0) for r in queries_prev) / max(len(queries_prev),1), 1),
            'total_keywords':    len(queries_prev),
        }
    }

    with open('data/gsc/data.json', 'w') as f:
        json.dump(gsc_data, f, indent=2)

    print(f"Saved: {len(queries_cur)} keywords, {len(pages_cur)} pages")
    return gsc_data

if __name__ == '__main__':
    fetch_gsc_data()
