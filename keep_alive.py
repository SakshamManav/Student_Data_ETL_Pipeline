import time
import urllib.request

URL = "https://student-data-etl-pipeline.onrender.com/"
INTERVAL = 5 * 60

while True:
    try:
        with urllib.request.urlopen(URL, timeout=90) as response:
            print(response.status, time.strftime("%H:%M:%S"), flush=True)
    except Exception as exc:
        print("Ping failed:", exc, flush=True)
    time.sleep(INTERVAL)
