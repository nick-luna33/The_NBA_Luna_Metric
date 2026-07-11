import pandas as pd
import time
from nba_api.stats.endpoints import leaguegamelog

def build_local_database(start_year, end_year):
    all_seasons_data = []
    
    for year in range(start_year, end_year + 1):
        # The NBA API requires seasons formatted like '2023-24'
        season_str = f"{year}-{str(year+1)[-2:]}"
        print(f"Downloading data for the {season_str} season...")
        
        try:
            # Fetch EVERY team's game log for the entire season in one shot
            game_log = leaguegamelog.LeagueGameLog(
                season=season_str,
                player_or_team_abbreviation='T' # 'T' tells the API we want Team data, not Player data
            )
            df = game_log.get_data_frames()[0]
            all_seasons_data.append(df)
            
            # Pause for 2 seconds between seasons so the NBA servers don't block us
            time.sleep(2)
            
        except Exception as e:
            print(f"Failed to fetch data for {season_str}: {e}")
            
    # Combine all the individual seasons into one massive master table
    master_df = pd.concat(all_seasons_data, ignore_index=True)
    
    # Save the master table to your local hard drive as a CSV file
    master_df.to_csv("luna_master_db.csv", index=False)
    print("\n" + "="*50)
    print(" SUCCESS! Saved to 'luna_master_db.csv'")
    print("="*50)

if __name__ == "__main__":
    print("="*50)
    print("   LUNA MASTER DATABASE BUILDER")
    print("="*50)
    
    # We are starting with a 5-year pull to test the system
    build_local_database(2019, 2023)
