import os
from dotenv import load_dotenv
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY', 'service-account-key.json')
GSC_PROPERTY_URL     = os.getenv('GSC_PROPERTY_URL')
GA4_PROPERTY_ID      = os.getenv('GA4_PROPERTY_ID')
ANTHROPIC_API_KEY    = os.getenv('ANTHROPIC_API_KEY')
SITE_NAME            = os.getenv('SITE_NAME', 'My Website')

# KPI Targets from your 6-month plan
KPI_TARGETS = {
    'organic_month1': 65,   'organic_month3': 200,  'organic_month6': 500,
    'da_month1': 3,          'da_month3': 6,          'da_month6': 12,
    'backlinks_month1': 25,  'backlinks_month3': 50,  'backlinks_month6': 100,
    'keywords_top50_month1': 115, 'keywords_top50_month3': 145, 'keywords_top50_month6': 225,
    'keywords_top10_month1': 10,  'keywords_top10_month3': 20,  'keywords_top10_month6': 40,
    'sessions_month1': 140,  'sessions_month3': 350,  'sessions_month6': 850,
    'clicks_month1': 90,     'clicks_month3': 250,    'clicks_month6': 600,
}

# Baselines (Feb 2026 — your starting point)
BASELINES = {
    'organic_traffic': 29,
    'da_score': 2,
    'backlinks': 11,
    'keywords_top50': 103,
    'keywords_top10': 5,
    'sessions': 70,
    'clicks': 51,
    'impressions': 2850,
    'avg_position': 30.5,
}

DEFAULT_DAYS = 28

def validate():
    ok = True
    if not os.path.exists(SERVICE_ACCOUNT_FILE or ''):
        print(f'MISSING: {SERVICE_ACCOUNT_FILE}'); ok = False
    if not GSC_PROPERTY_URL:
        print('MISSING: GSC_PROPERTY_URL'); ok = False
    if not GA4_PROPERTY_ID:
        print('MISSING: GA4_PROPERTY_ID'); ok = False
    return ok

if __name__ == '__main__':
    print('Config OK' if validate() else 'Config has errors')
