import os, json
from datetime import datetime, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
from google.oauth2 import service_account
from dotenv import load_dotenv
load_dotenv()

def get_client():
    creds = service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY', 'service-account-key.json'),
        scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    return BetaAnalyticsDataClient(credentials=creds)

def fetch_ga4_data(days=28):
    print(f"Connecting to Google Analytics 4 ({days} days)...")
    client = BetaAnalyticsDataClient(credentials=service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY', 'service-account-key.json'),
        scopes=['https://www.googleapis.com/auth/analytics.readonly']))

    prop = f"properties/{os.getenv('GA4_PROPERTY_ID')}"
    end   = datetime.now()
    start = end - timedelta(days=days)
    prev_end   = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days)

    end_str        = end.strftime('%Y-%m-%d')
    start_str      = start.strftime('%Y-%m-%d')
    prev_end_str   = prev_end.strftime('%Y-%m-%d')
    prev_start_str = prev_start.strftime('%Y-%m-%d')

    def run(dims, metrics, start_d, end_d, limit=100):
        req = RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=start_d, end_date=end_d)],
            dimensions=[Dimension(name=d) for d in dims],
            metrics=[Metric(name=m) for m in metrics],
            limit=limit)
        resp = client.run_report(req)
        rows = []
        for row in resp.rows:
            r = {}
            for i, d in enumerate(dims):
                r[d] = row.dimension_values[i].value
            for i, m in enumerate(metrics):
                r[m] = row.metric_values[i].value
            rows.append(r)
        return rows

    print("Fetching channel data...")
    channels_cur  = run(['sessionDefaultChannelGroup'],
                        ['sessions','totalUsers','bounceRate','averageSessionDuration'],
                        start_str, end_str)
    channels_prev = run(['sessionDefaultChannelGroup'],
                        ['sessions','totalUsers'],
                        prev_start_str, prev_end_str)

    print("Fetching page data...")
    pages_cur = run(['pagePath'],
                    ['sessions','totalUsers','bounceRate','averageSessionDuration'],
                    start_str, end_str, limit=200)

    print("Fetching daily trend...")
    daily = run(['date'], ['sessions','totalUsers'],
                start_str, end_str, limit=90)

    organic_cur  = next((int(r['sessions']) for r in channels_cur
                         if 'organic' in r.get('sessionDefaultChannelGroup','').lower()), 0)
    organic_prev = next((int(r['sessions']) for r in channels_prev
                         if 'organic' in r.get('sessionDefaultChannelGroup','').lower()), 0)
    total_cur    = sum(int(r.get('sessions',0)) for r in channels_cur)
    total_prev   = sum(int(r.get('sessions',0)) for r in channels_prev)

    ga4_data = {
        'fetched_at': datetime.now().isoformat(),
        'period': {'days': days, 'start': start_str, 'end': end_str},
        'channels': channels_cur,
        'channels_prev': channels_prev,
        'pages': pages_cur,
        'daily': daily,
        'summary': {
            'organic_sessions': organic_cur,
            'total_sessions':   total_cur,
            'total_users':      sum(int(r.get('totalUsers',0)) for r in channels_cur),
            'avg_bounce_rate':  round(sum(float(r.get('bounceRate',0)) for r in channels_cur) /
                                      max(len(channels_cur),1) * 100, 1),
        },
        'prev_summary': {
            'organic_sessions': organic_prev,
            'total_sessions':   total_prev,
        }
    }

    os.makedirs('data/ga4', exist_ok=True)
    with open('data/ga4/data.json', 'w') as f:
        json.dump(ga4_data, f, indent=2)

    print(f"Saved: {len(channels_cur)} channels, {len(pages_cur)} pages, {len(daily)} daily points")
    return ga4_data

if __name__ == '__main__':
    fetch_ga4_data()
