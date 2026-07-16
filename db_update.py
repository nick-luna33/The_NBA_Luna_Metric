import sqlite3
import pandas as pd
import os
import time
from nba_api.stats.endpoints import leaguegamelog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "nba_master.db")

# Set this to whatever the current ongoing NBA season is
CURRENT_SEASON = "2025-26" 

def run_daily_update():
    print(f"Connecting to database to update the {CURRENT_SEASON} season...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_team_games = 0
    new_player_games = 0

    # 1. Update Team Logs
    try:
        print("Fetching latest team game logs...")
        team_log = leaguegamelog.LeagueGameLog(season=CURRENT_SEASON, player_or_team_abbreviation='T')
        team_df = team_log.get_data_frames()[0]
        
        for _, row in team_df.iterrows():
            cursor.execute('''
                INSERT OR IGNORE INTO Team_Game_Logs (game_id, team_id, season_id, game_date, matchup, plus_minus)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (row['GAME_ID'], row['TEAM_ID'], row['SEASON_ID'], row['GAME_DATE'], row['MATCHUP'], row['PLUS_MINUS']))
            # If rowcount is 1, it means a new row was actually added!
            if cursor.rowcount == 1:
                new_team_games += 1
        conn.commit()
    except Exception as e:
        print(f"Error updating team logs: {e}")

    time.sleep(2) # Server safety pause

    # 2. Update Player Logs
    try:
        print("Fetching latest player box scores...")
        player_log = leaguegamelog.LeagueGameLog(season=CURRENT_SEASON, player_or_team_abbreviation='P')
        player_df = player_log.get_data_frames()[0]
        
        for _, row in player_df.iterrows():
            cursor.execute('''
                INSERT OR IGNORE INTO Player_Game_Logs (game_id, player_id, team_id, season_id, game_date, matchup, pts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row['GAME_ID'], row['PLAYER_ID'], row['TEAM_ID'], row['SEASON_ID'], row['GAME_DATE'], row['MATCHUP'], row['PTS']))
            if cursor.rowcount == 1:
                new_player_games += 1
        conn.commit()
    except Exception as e:
        print(f"Error updating player logs: {e}")

    conn.close()
    
    print("\n" + "="*50)
    print(" DAILY DATABASE UPDATE COMPLETE ")
    print("="*50)
    print(f" New Team Box Scores Added:   {new_team_games}")
    print(f" New Player Box Scores Added: {new_player_games}")
    print("="*50)

if __name__ == "__main__":
    run_daily_update()
