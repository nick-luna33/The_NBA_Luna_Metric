import sqlite3
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "nba_master.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("SELECT COUNT(*) FROM Team_Game_Logs")
    team_count = cursor.fetchone()[0]
    print(f"Total rows in Team_Game_Logs: {team_count}")
    
    if team_count > 0:
        cursor.execute("SELECT season_id, matchup, plus_minus FROM Team_Game_Logs LIMIT 3")
        print("Sample Team Data:", cursor.fetchall())
except Exception as e:
    print(f"Error checking Team table: {e}")

conn.close()
