import sqlite3
import pandas as pd
import time
import os
from nba_api.stats.endpoints import leaguegamelog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "nba_master.db")

# Custom headers to trick the NBA API into thinking we are a normal Google Chrome browser
CUSTOM_HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.nba.com',
    'Referer': 'https://www.nba.com/',
    'Connection': 'keep-alive'
}

def upgrade_player_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Dropping old Player_Game_Logs table...")
    cursor.execute("DROP TABLE IF EXISTS Player_Game_Logs")
    
    print("Creating self-contained Player_Game_Logs table...")
    cursor.execute('''
        CREATE TABLE Player_Game_Logs (
            game_id TEXT,
            player_id INTEGER,
            player_name TEXT,
            team_id INTEGER,
            season_id TEXT,
            game_date TEXT,
            matchup TEXT,
            pts INTEGER,
            ast INTEGER,
            fga INTEGER,
            fta INTEGER,
            PRIMARY KEY (game_id, player_id)
        )
    ''')
    conn.commit()

    print("="*50)
    print(" FETCHING ADVANCED STATS WITH BROWSER HEADERS")
    print("="*50)

    # We will prioritize modern years first so you can test Jokic immediately!
    for year in range(2025, 1995, -1):
        season_str = f"{year}-{str(year+1)[-2:]}"
        print(f"\n--- Downloading {season_str} ---")
        
        for season_type in ['Regular Season', 'Playoffs']:
            try:
                log = leaguegamelog.LeagueGameLog(
                    season=season_str, 
                    player_or_team_abbreviation='P', 
                    season_type_all_star=season_type,
                    headers=CUSTOM_HEADERS, # Force browser headers
                    timeout=30
                )
                df = log.get_data_frames()[0]
                
                if df.empty:
                    print(f"  [!] No data found for {season_type}")
                    continue
                    
                for _, row in df.iterrows():
                    cursor.execute('''
                        INSERT OR IGNORE INTO Player_Game_Logs 
                        (game_id, player_id, player_name, team_id, season_id, game_date, matchup, pts, ast, fga, fta)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row['GAME_ID'], row['PLAYER_ID'], row['PLAYER_NAME'], row['TEAM_ID'], row['SEASON_ID'], 
                          row['GAME_DATE'], row['MATCHUP'], row['PTS'], row['AST'], row['FGA'], row['FTA']))
                conn.commit()
                print(f"  ✓ Loaded {len(df)} rows for {season_type}")
                
            except Exception as e:
                print(f"  ❌ Error downloading {season_type}: {e}")
                
            time.sleep(2.0) # Safety buffer between requests

    conn.close()
    print("\nDatabase Rebuild Complete!")

if __name__ == "__main__":
    upgrade_player_database()
