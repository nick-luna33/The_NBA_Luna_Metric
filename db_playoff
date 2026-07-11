import sqlite3
import pandas as pd
import time
import os
from nba_api.stats.endpoints import leaguegamelog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "nba_master.db")

def backfill_playoffs(start_year, end_year):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("="*50)
    print("       NBA PLAYOFFS DATABASE BACKFILL")
    print("="*50)
    
    for year in range(start_year, end_year + 1):
        season_str = f"{year}-{str(year+1)[-2:]}"
        print(f"\n--- Downloading {season_str} PLAYOFFS ---")
        
        # 1. Fetch and Insert ALL Team Playoff Logs
        try:
            print("Fetching team playoff logs...")
            # We explicitly pass season_type_all_star='Playoffs'
            team_log = leaguegamelog.LeagueGameLog(
                season=season_str, 
                player_or_team_abbreviation='T', 
                season_type_all_star='Playoffs'
            )
            team_df = team_log.get_data_frames()[0]
            
            for _, row in team_df.iterrows():
                cursor.execute('''
                    INSERT OR IGNORE INTO Team_Game_Logs (game_id, team_id, season_id, game_date, matchup, plus_minus)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (row['GAME_ID'], row['TEAM_ID'], row['SEASON_ID'], row['GAME_DATE'], row['MATCHUP'], row['PLUS_MINUS']))
            conn.commit()
            print(f"Loaded {len(team_df)} team playoff rows.")
        except Exception as e:
            print(f"No team playoff data or error for {season_str}: {e}")
            
        time.sleep(2.5) # Server safety pause
        
        # 2. Fetch and Insert ALL Player Playoff Logs
        try:
            print("Fetching player playoff box scores...")
            player_log = leaguegamelog.LeagueGameLog(
                season=season_str, 
                player_or_team_abbreviation='P', 
                season_type_all_star='Playoffs'
            )
            player_df = player_log.get_data_frames()[0]
            
            for _, row in player_df.iterrows():
                cursor.execute('''
                    INSERT OR IGNORE INTO Player_Game_Logs (game_id, player_id, team_id, season_id, game_date, matchup, pts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (row['GAME_ID'], row['PLAYER_ID'], row['TEAM_ID'], row['SEASON_ID'], row['GAME_DATE'], row['MATCHUP'], row['PTS']))
            conn.commit()
            print(f"Loaded {len(player_df)} player playoff box score rows.")
        except Exception as e:
            print(f"No player playoff data or error for {season_str}: {e}")
            
        time.sleep(2.5) # Server safety pause

    conn.close()
    print("\n" + "="*50)
    print(" SUCCESS: Playoff history backfill complete!")
    print("="*50)

if __name__ == "__main__":
    # Gather playoff data for the entire modern era
    backfill_playoffs(1996, 2025)
