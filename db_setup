import sqlite3
import os

# 1. Create or connect to the new SQLite database in your current folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "nba_master.db")

def create_database():
    print("Connecting to SQLite database...")
    # This automatically creates 'nba_master.db' if it doesn't exist yet
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Create the PLAYERS table
    print("Creating Players table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Players (
            player_id INTEGER PRIMARY KEY,
            player_name TEXT NOT NULL,
            is_active BOOLEAN
        )
    ''')

    # 3. Create the TEAM GAME LOGS table (Used to find Elite vs Regular opponents)
    print("Creating Team Game Logs table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Team_Game_Logs (
            game_id TEXT,
            team_id INTEGER,
            season_id TEXT,
            game_date DATE,
            matchup TEXT,
            plus_minus REAL,
            PRIMARY KEY (game_id, team_id) 
        )
    ''')

    # 4. Create the PLAYER GAME LOGS table (Used for the actual LUNA Score math)
    print("Creating Player Game Logs table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Player_Game_Logs (
            game_id TEXT,
            player_id INTEGER,
            team_id INTEGER,
            season_id TEXT,
            game_date DATE,
            matchup TEXT,
            pts INTEGER,
            PRIMARY KEY (game_id, player_id)
        )
    ''')

    # Save the changes and close the connection
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print(" SUCCESS: 'nba_master.db' foundation has been built!")
    print("="*50)

if __name__ == "__main__":
    create_database()
