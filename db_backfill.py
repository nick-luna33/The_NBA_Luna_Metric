import sqlite3
import pandas as pd
import time
import os
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamelog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "nba_master.db")

def backfill_players(conn):
    print("Populating Players master list...")
    cursor = conn.cursor()
    # Get every player in NBA history instantly from local library metadata
    all_players = players.get_players()
    
    for p in all_players:
        cursor.execute('''
            INSERT OR IGNORE INTO Players (player_id, player_name, is_active)
            VALUES (?, ?, ?)
        ''', (p['id'], p['full_name'], p['is_active']))
    conn.commit()
    print(f"Loaded {len(all_players)} players into the database.")

def backfill_seasons(conn, start_year, end_year):
    cursor = conn.cursor()
    
    for year in range(start_year, end_year + 1):
        season_str = f"{year}-{str(year+1)[-2:]}"
        print(f"\n--- Downloading the {season_str} Season ---")
        
        # 1. Fetch and Insert ALL Team Game Logs for this season
        try:
            print("Fetching team logs...")
            team_log = leaguegamelog.LeagueGameLog(season=season_str, player_or_team_abbreviation='T')
            team_df = team_log.get_data_frames()[0]
            
            for _, row in team_df.iterrows():
                cursor.execute('''
                    INSERT OR IGNORE INTO Team_Game_Logs (game_id, team_id, season_id, game_date, matchup, plus_minus)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (row['GAME_ID'], row['TEAM_ID'], row['SEASON_ID'], row['GAME_DATE'], row['MATCHUP'], row['PLUS_MINUS']))
            conn.commit()
            print(f"Successfully loaded {len(team_df)} team game rows.")
        except Exception as e:
            print(f"Error loading team logs for {season_str}: {e}")
            
        time.sleep(2.5) # Server safety pause
        
        # 2. Fetch and Insert ALL Player Game Logs for this season
        try:
            print("Fetching player logs (this is a massive download, give it a second)...")
            player_log = leaguegamelog.LeagueGameLog(season=season_str, player_or_team_abbreviation='P')
            player_df = player_log.get_data_frames()[0]
            
            for _, row in player_df.iterrows():
                cursor.execute('''
                    INSERT OR IGNORE INTO Player_Game_Logs (game_id, player_id, team_id, season_id, game_date, matchup, pts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (row['GAME_ID'], row['PLAYER_ID'], row['TEAM_ID'], row['SEASON_ID'], row['GAME_DATE'], row['MATCHUP'], row['PTS']))
            conn.commit()
            print(f"Successfully loaded {len(player_df)} player box score rows.")
        except Exception as e:
            print(f"Error loading player logs for {season_str}: {e}")
            
        time.sleep(2.5) # Server safety pause

if __name__ == "__main__":
    print("="*50)
    print("       NBA MEGA-DATABASE BACKFILL")
    print("="*50)
    
    connection = sqlite3.connect(DB_PATH)
    
    # We already have the player list, so we can skip checking it again
    # backfill_players(connection) 
    
    # 1. Pull the historical data (1996 through 2019)
    backfill_seasons(connection, 1996, 2019)
    
    # 2. Pull the most recently completed season (2025-26)
    backfill_seasons(connection, 2025, 2025)
    
    connection.close()
    print("\n" + "="*50)
    print(" SUCCESS: Database historical backfill complete!")
    print("="*50)
