"""
ISOLATED CONNECTION TEST - does not touch your database or Flask app.
This makes exactly ONE request to stats.nba.com to check if it's reachable
from your computer right now. Run it with:

    python test_connection.py
"""

import time
from nba_api.stats.endpoints import commonplayerinfo

CUSTOM_HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.nba.com',
    'Referer': 'https://www.nba.com/',
    'Connection': 'keep-alive'
}

print("Testing ONE isolated request to stats.nba.com...")
print("(Give it up to 30 seconds - the site can be slow.)\n")

start = time.time()
try:
    # 203999 = Nikola Jokic's player ID, just used as a reliable test subject
    info = commonplayerinfo.CommonPlayerInfo(player_id=203999, headers=CUSTOM_HEADERS, timeout=30)
    df = info.get_data_frames()[0]
    elapsed = round(time.time() - start, 1)

    print(f"SUCCESS in {elapsed} seconds!")
    print(f"Player found: {df['DISPLAY_FIRST_LAST'].iloc[0]}")
    print("\n--> Your connection to stats.nba.com IS working right now.")
    print("--> If your main app still fails, it's likely getting blocked")
    print("    partway through because it sends MANY requests in a row,")
    print("    not because the connection is fully blocked.")

except Exception as e:
    elapsed = round(time.time() - start, 1)
    print(f"FAILED after {elapsed} seconds.")
    print(f"Error: {e}")
    print("\n--> stats.nba.com is not responding to your machine AT ALL")
    print("    right now, regardless of what code runs. This usually")
    print("    means it's temporarily rate-limiting or blocking your")
    print("    IP address, or the site itself is having issues.")
