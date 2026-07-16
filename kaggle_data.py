import sqlite3
import pandas as pd
import os

# ==== SETTINGS - CHANGE THESE IF NEEDED ====
# Folder where TeamStatistics.csv and PlayerStatistics.csv live
FOLDER = r"C:\Users\nicho\Downloads\archive"
# Path to your existing database (this script should sit in your LUNA_project folder)
DB_PATH = "nba_master.db"
# Only import seasons from this year onward (matches your app's 1996-2026 range)
MIN_YEAR = 1996

# Standard NBA team ID -> abbreviation (these IDs stay the same even through relocations)
TEAM_ID_TO_ABBR = {
    1610612737: "ATL", 1610612738: "BOS", 1610612751: "BKN", 1610612766: "CHA",
    1610612741: "CHI", 1610612739: "CLE", 1610612742: "DAL", 1610612743: "DEN",
    1610612765: "DET", 1610612744: "GSW", 1610612745: "HOU", 1610612754: "IND",
    1610612746: "LAC", 1610612747: "LAL", 1610612763: "MEM", 1610612748: "MIA",
    1610612749: "MIL", 1610612750: "MIN", 1610612740: "NOP", 1610612752: "NYK",
    1610612760: "OKC", 1610612753: "ORL", 1610612755: "PHI", 1610612756: "PHX",
    1610612757: "POR", 1610612758: "SAC", 1610612759: "SAS", 1610612761: "TOR",
    1610612762: "UTA", 1610612764: "WAS",
}

# Your app only understands these two game types (matches season_id prefixes
# already used by luna_engine.py: '2' = Regular Season, '4' = Playoffs)
GAME_TYPE_PREFIX = {"Regular Season": "2", "Playoffs": "4"}


def season_start_year(dt):
    # NBA seasons run roughly August through June, so a game in Nov 2016
    # and a game in Apr 2017 both belong to the "2016-17" season.
    return dt.year if dt.month >= 8 else dt.year - 1


def build_season_id(game_date, game_type):
    prefix = GAME_TYPE_PREFIX.get(game_type)
    if prefix is None:
        return None
    return f"{prefix}{season_start_year(game_date)}"


def build_matchup(team_id, opp_team_id, is_home):
    if pd.isna(team_id) or pd.isna(opp_team_id):
        return None
    team_abbr = TEAM_ID_TO_ABBR.get(int(team_id), "UNK")
    opp_abbr = TEAM_ID_TO_ABBR.get(int(opp_team_id), "UNK")
    return f"{team_abbr} vs. {opp_abbr}" if is_home else f"{team_abbr} @ {opp_abbr}"


def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def import_team_stats(conn):
    path = os.path.join(FOLDER, "TeamStatistics.csv")
    print(f"\nReading {path} ...")
    cursor = conn.cursor()
    total = 0

    for chunk in pd.read_csv(path, chunksize=50000, low_memory=False):
        chunk["gameDate"] = pd.to_datetime(chunk["gameDate"], errors="coerce")
        chunk = chunk.dropna(subset=["gameDate"])
        chunk = chunk[chunk["gameDate"].dt.year >= MIN_YEAR]
        chunk = chunk[chunk["gameType"].isin(GAME_TYPE_PREFIX.keys())]
        chunk = chunk.dropna(subset=["teamId", "opponentTeamId", "gameId"])

        rows = []
        for _, row in chunk.iterrows():
            season_id = build_season_id(row["gameDate"], row["gameType"])
            if season_id is None:
                continue
            matchup = build_matchup(row["teamId"], row["opponentTeamId"], row["home"] == 1)
            if matchup is None:
                continue
            rows.append((
                season_id,
                safe_int(row["teamId"]),
                str(row["gameId"]),
                row["gameDate"].strftime("%Y-%m-%d"),
                matchup,
                row["plusMinusPoints"],
            ))

        cursor.executemany('''
            INSERT OR IGNORE INTO Team_Game_Logs (season_id, team_id, game_id, game_date, matchup, plus_minus)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', rows)
        conn.commit()
        total += len(rows)
        print(f"  ... {total} team-game rows imported so far")

    print(f"Done. Total Team_Game_Logs rows inserted: {total}")


def import_player_stats(conn):
    path = os.path.join(FOLDER, "PlayerStatistics.csv")
    print(f"\nReading {path} ...")
    cursor = conn.cursor()
    total = 0

    for chunk in pd.read_csv(path, chunksize=50000, low_memory=False):
        chunk["gameDate"] = pd.to_datetime(chunk["gameDate"], errors="coerce")
        chunk = chunk.dropna(subset=["gameDate"])
        chunk = chunk[chunk["gameDate"].dt.year >= MIN_YEAR]
        chunk = chunk[chunk["gameType"].isin(GAME_TYPE_PREFIX.keys())]
        chunk = chunk.dropna(subset=["playerteamId", "opponentteamId", "personId", "gameId"])

        rows = []
        for _, row in chunk.iterrows():
            season_id = build_season_id(row["gameDate"], row["gameType"])
            if season_id is None:
                continue
            full_name = f"{row['firstName']} {row['lastName']}"
            matchup = build_matchup(row["playerteamId"], row["opponentteamId"], row["home"] == 1)
            if matchup is None:
                continue

            rows.append((
                str(row["gameId"]),
                safe_int(row["personId"]),
                full_name,
                safe_int(row["playerteamId"]),
                season_id,
                row["gameDate"].strftime("%Y-%m-%d"),
                matchup,
                safe_int(row["points"]),
                safe_int(row["assists"]),
                safe_int(row["fieldGoalsAttempted"]),
                safe_int(row["freeThrowsAttempted"]),
            ))

        cursor.executemany('''
            INSERT OR IGNORE INTO Player_Game_Logs
            (game_id, player_id, player_name, team_id, season_id, game_date, matchup, pts, ast, fga, fta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rows)
        conn.commit()
        total += len(rows)
        print(f"  ... {total} player-game rows imported so far")

    print(f"Done. Total Player_Game_Logs rows inserted: {total}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Make sure the tables exist with the same shape luna_engine.py expects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Player_Game_Logs (
            game_id TEXT, player_id INTEGER, player_name TEXT, team_id INTEGER,
            season_id TEXT, game_date TEXT, matchup TEXT, pts INTEGER, ast INTEGER,
            fga INTEGER, fta INTEGER, PRIMARY KEY (game_id, player_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Team_Game_Logs (
            season_id TEXT, team_id INTEGER, game_id TEXT, game_date TEXT,
            matchup TEXT, plus_minus REAL, PRIMARY KEY (game_id, team_id)
        )
    ''')
    conn.commit()

    import_team_stats(conn)
    import_player_stats(conn)

    conn.close()
    print("\nAll done! nba_master.db is now populated from local files - no NBA API calls needed.")
