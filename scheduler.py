import schedule, time, threading
from datetime import datetime

def fetch_job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Auto-fetching data...")
    try:
        from main import run_fetch
        run_fetch(28)
        print("Auto-fetch complete.")
    except Exception as e:
        print(f"Auto-fetch error: {e}")

# Run every day at 08:00
schedule.every().day.at("08:00").do(fetch_job)

print("Scheduler running — auto-fetch at 08:00 daily.")
print("Press Ctrl+C to stop.")

while True:
    schedule.run_pending()
    time.sleep(60)
