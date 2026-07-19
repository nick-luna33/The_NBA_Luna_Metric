import sqlite3
import pandas as pd
import os
import warnings
import time
import unicodedata
import math
from datetime import datetime

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, leaguegamelog, commonplayerinfo

warnings.filterwarnings('ignore')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "nba_master.db")

CUSTOM_HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.nba.com',
    'Referer': 'https://www.nba.com/',
    'Connection': 'keep-alive'
}

OFFLINE_MODE = True

# LUNA v2.0: Historical League Average True Shooting %
# Used to dynamically normalize efficiency across different eras
LEAGUE_TS_MAP = {
    1996: 53.6, 1997: 52.4, 1998: 51.1, 1999: 52.3, 2000: 51.8,
    2001: 52.0, 2002: 51.9, 2003: 51.6, 2004: 52.9, 2005: 53.6,
    2006: 54.1, 2007: 54.0, 2008: 54.4, 2009: 54.3, 2010: 54.1,
    2011: 52.7, 2012: 53.5, 2013: 54.1, 2014: 53.4, 2015: 54.1,
    2016: 55.2, 2017: 55.6, 2018: 56.0, 2019: 56.5, 2020: 57.2,
    2021: 56.6, 2022: 58.1, 2023: 58.0, 2024: 58.0
}

TEAM_COLORS = {
    1610612737: "#E03A3E", 1610612738: "#007A33", 1610612751: "#000000",
    1610612766: "#1D1160", 1610612741: "#CE1141", 1610612739: "#860038",
    1610612742: "#00538C", 1610612743: "#0E2240", 1610612765: "#C8102E",
    1610612744: "#1D428A", 1610612745: "#CE1141", 1610612754: "#002D62",
    1610612746: "#C8102E", 1610612747: "#552583", 1610612763: "#5D76A9",
    1610612748: "#98002E", 1610612749: "#00471B", 1610612750: "#0C2340",
    1610612740: "#0C2340", 1610612752: "#006BB6", 1610612760: "#007AC1",
    1610612753: "#0077C0", 1610612755: "#006BB6", 1610612756: "#E56020",
    1610612757: "#E03A3E", 1610612758: "#5A2D81", 1610612759: "#000000",
    1610612761: "#CE1141", 1610612762: "#002B5C", 1610612764: "#002B5C",
}
DEFAULT_TEAM_COLOR = "#1a1a1a"

def generate_modern_seasons():
    seasons = []
    for year in range(1996, 2026):
        seasons.append((str(year), f"{year}-{str(year+1)[-2:]}"))
    return seasons

def remove_accents(input_str):
    return unicodedata.normalize('NFKD', input_str).encode('ASCII', 'ignore').decode('utf-8')

def calculate_advanced(games_list):
    if not games_list:
        return 0, 0, 0

    total_pts = sum(g['pts'] for g in games_list)
    total_assist_pts = sum(g.get('assist_pts', 0) or 0 for g in games_list)
    total_fga = sum(g['fga'] for g in games_list)
    total_fta = sum(g['fta'] for g in games_list)
    games_count = len(games_list)

    ppg = total_pts / games_count
    points_created = ppg + (total_assist_pts / games_count)

    ts_denom = 2 * (total_fga + 0.44 * total_fta)
    ts_pct = (total_pts / ts_denom * 100) if ts_denom > 0 else 0

    return round(ppg, 1), round(points_created, 1), round(ts_pct, 1)

def run_local_luna(player_name, selected_year=None, selected_season_name="All Career", season_type="Regular", elite_threshold=4.0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Assist_Points_Created (
            game_id TEXT, player_id INTEGER, assist_pts INTEGER,
            PRIMARY KEY (game_id, player_id)
        )
    ''')
    conn.commit()

    nba_players = players.get_players()
    clean_search = remove_accents(player_name).lower()
    match = [p for p in nba_players if clean_search in remove_accents(p['full_name']).lower()]

    if not match:
        conn.close()
        return f"Could not find '{player_name}' in the NBA registry."

    player_id = match[0]['id']
    exact_name = match[0]['full_name']

    print(f"\n[LUNA ENGINE] Evaluating data state for: {exact_name} (ID: {player_id})")

    if OFFLINE_MODE:
        print("  -> Offline mode: skipping live NBA API calls, reading only from your local database.")
    else:
        if selected_year:
            target_year_int = int(selected_year)
            active_seasons = [f"{target_year_int}-{str(target_year_int+1)[-2:]}"]
            print(f"  -> Speed Mode: Only pulling selected target season: {active_seasons[0]}")
        else:
            print("  -> Querying NBA registry for exact career timeframe...")
            try:
                info = commonplayerinfo.CommonPlayerInfo(player_id=player_id, headers=CUSTOM_HEADERS, timeout=30)
                info_df = info.get_data_frames()[0]
                from_year = int(info_df['FROM_YEAR'].iloc[0])
                to_year = int(info_df['TO_YEAR'].iloc[0])
                active_seasons = [f"{y}-{str(y+1)[-2:]}" for y in range(from_year, to_year + 1)]
                print(f"  -> Career mapped successfully: {from_year} to {to_year} ({len(active_seasons)} seasons).")
            except Exception as e:
                print(f"  -> [!] Registry fetch failed: {e}")
                print(f"  -> Falling back to recent decade.")
                active_seasons = [f"{y}-{str(y+1)[-2:]}" for y in range(2016, 2026)]

        try:
            for season_str in active_seasons:
                target_types = [('2', 'Regular Season')] if season_type == "Regular" else [('4', 'Playoffs')]

                for s_prefix, s_type in target_types:
                    full_season_id = f"{s_prefix}{season_str.split('-')[0]}"
                    cursor.execute("SELECT COUNT(*) FROM Player_Game_Logs WHERE player_id = ? AND season_id = ?", (player_id, full_season_id))
                    has_games = cursor.fetchone()[0]

                    if has_games == 0:
                        success = False
                        attempts = 0
                        while not success and attempts < 2:
                            try:
                                log = playergamelog.PlayerGameLog(
                                    player_id=player_id, season=season_str,
                                    season_type_all_star=s_type, headers=CUSTOM_HEADERS, timeout=30
                                )
                                df = log.get_data_frames()[0]
                                success = True
                            except Exception as e:
                                attempts += 1
                                print(f"     [!] Attempt {attempts} failed for {season_str} ({s_type}): {e}")
                                time.sleep(2)

                        if success and df.empty:
                            print(f"     [!] Fetch succeeded but returned 0 rows for {season_str} ({s_type}) - no game data for this player/season.")
                        elif not success:
                            print(f"     [!] Giving up on {season_str} ({s_type}) after {attempts} failed attempts.")

                        if success and not df.empty:
                            print(f"     [Syncing] Downloaded logs for: {season_str} ({s_type})")
                            for _, row in df.iterrows():
                                try:
                                    clean_date = datetime.strptime(row['GAME_DATE'], "%b %d, %Y").strftime("%Y-%m-%d")
                                except:
                                    clean_date = row['GAME_DATE']

                                cursor.execute('''
                                    INSERT OR IGNORE INTO Player_Game_Logs
                                    (game_id, player_id, player_name, team_id, season_id, game_date, matchup, pts, ast, fga, fta)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (row['Game_ID'], player_id, exact_name, 0, row['SEASON_ID'],
                                      clean_date, row['MATCHUP'], row['PTS'], row['AST'], row['FGA'], row['FTA']))
                            conn.commit()
                            time.sleep(0.4)
        except Exception as e:
            print(f"  -> Network pause handled: {e}")

    prefix = "2" if season_type == "Regular" else "4"

    if selected_year:
        query = """
            SELECT p.game_date, p.matchup, p.pts, p.ast, p.fga, p.fta, p.season_id, p.team_id,
                   COALESCE(a.assist_pts, 0) AS assist_pts
            FROM Player_Game_Logs p
            LEFT JOIN Assist_Points_Created a
                ON a.game_id = p.game_id AND a.player_id = p.player_id
            WHERE p.player_id = ? AND p.season_id = ?
            ORDER BY p.game_date ASC
        """
        df = pd.read_sql_query(query, conn, params=(player_id, f"{prefix}{selected_year}"))
    else:
        query = """
            SELECT p.game_date, p.matchup, p.pts, p.ast, p.fga, p.fta, p.season_id, p.team_id,
                   COALESCE(a.assist_pts, 0) AS assist_pts
            FROM Player_Game_Logs p
            LEFT JOIN Assist_Points_Created a
                ON a.game_id = p.game_id AND a.player_id = p.player_id
            WHERE p.player_id = ? AND p.season_id LIKE ?
            ORDER BY p.game_date ASC
        """
        df = pd.read_sql_query(query, conn, params=(player_id, f"{prefix}%"))

    if df.empty:
        conn.close()
        return f"No local logs available for {exact_name} ({selected_season_name}). Please ensure your network is connected and click Analyze again."

    unique_seasons = df['season_id'].unique()
    for sid in unique_seasons:
        cursor.execute("SELECT COUNT(*) FROM Team_Game_Logs WHERE season_id = ?", (sid,))
        count = cursor.fetchone()[0]
        is_missing_or_corrupt = (sid.startswith('2') and count < 1000) or (sid.startswith('4') and count < 50)

        if is_missing_or_corrupt:
            if OFFLINE_MODE:
                print(f"  -> Offline mode: season {sid} has limited team data locally, using what's available.")
            else:
                print(f"  -> Baseline context matrix missing for season {sid}. Rebuilding environment logs...")
                cursor.execute("DELETE FROM Team_Game_Logs WHERE season_id = ?", (sid,))
                conn.commit()

                try:
                    year_str = sid[1:5]
                    year_int = int(year_str)
                    season_str = f"{year_int}-{str(year_int+1)[-2:]}"
                    t_type = 'Regular Season' if sid.startswith('2') else 'Playoffs'

                    log = leaguegamelog.LeagueGameLog(
                        season=season_str, player_or_team_abbreviation='T',
                        season_type_all_star=t_type, headers=CUSTOM_HEADERS, timeout=25
                    )
                    team_df = log.get_data_frames()[0]
                    if not team_df.empty:
                        for _, row in team_df.iterrows():
                            cursor.execute('''
                                INSERT OR IGNORE INTO Team_Game_Logs (season_id, team_id, game_id, game_date, matchup, plus_minus)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (row['SEASON_ID'], row['TEAM_ID'], row['GAME_ID'], row['GAME_DATE'], row['MATCHUP'], row['PLUS_MINUS']))
                        conn.commit()
                    time.sleep(1.0)
                except Exception as e:
                    print(f"  -> [!] Team log rebuild failed for season {sid}: {e}")

    elite_games = []
    reg_games = []

    print("  -> Splitting stats across team strength matrix slices...")
    for _, game in df.iterrows():
        p_date = game['game_date']
        opp_abbr = game['matchup'].split(' ')[-1]

        opp_query = """
            SELECT plus_minus FROM Team_Game_Logs
            WHERE team_id = (SELECT team_id FROM Team_Game_Logs WHERE matchup LIKE ? LIMIT 1)
              AND season_id = ? AND game_date < ?
        """
        opp_games = pd.read_sql_query(opp_query, conn, params=(f"{opp_abbr} %", game['season_id'], p_date))

        if season_type == "Regular" and len(opp_games) < 5:
            reg_games.append(game)
            continue

        rolling_diff = opp_games['plus_minus'].mean() if not opp_games.empty else 0

        game_dict = {
            'date': p_date, 'opp': opp_abbr, 'pts': game['pts'],
            'ast': game['ast'], 'fga': game['fga'], 'fta': game['fta'],
            'assist_pts': game['assist_pts'], 'opp_net': round(rolling_diff, 1)
        }

        if rolling_diff >= elite_threshold:
            elite_games.append(game_dict)
        else:
            reg_games.append(game_dict)

    conn.close()
    print("[LUNA ENGINE] Computation cycle completed successfully.\n")

    if not elite_games or not reg_games:
        return f"Calculated {len(elite_games) + len(reg_games)} total games, but 0 met context parameters. Try refreshing to settle background processes."

    reg_ppg, reg_pc, reg_ts = calculate_advanced(reg_games)
    elite_ppg, elite_pc, elite_ts = calculate_advanced(elite_games)

    # =====================================================================
    # --- LUNA v2.0: UNBIASED POSSESSION-TERMINATION SCORE CALCULATION ---
    # =====================================================================
    total_elite_fga = sum(g['fga'] for g in elite_games)
    total_elite_fta = sum(g['fta'] for g in elite_games)
    total_elite_ast = sum(g['ast'] for g in elite_games)
    elite_count = len(elite_games)

    indiv_poss_per_game = (total_elite_fga + (0.44 * total_elite_fta) + total_elite_ast) / elite_count

    if indiv_poss_per_game > 0:
        # 1. LOGARITHMIC VOLUME STABILIZATION
        # Rewards players who handle massive loads without artificially inflating low-minute role players.
        volume_stabilizer = math.log(indiv_poss_per_game + 1) / math.log(21)
        pc_scaled = (elite_pc / indiv_poss_per_game) * 20.0 * volume_stabilizer
    else:
        pc_scaled = 0.0

    # 2. ERA NORMALIZATION
    # Find the dominant year from the player's dataset to look up the correct historical TS%
    try:
        primary_season_str = str(df['season_id'].mode()[0])
        # '22023' -> 2023
        year_int = int(primary_season_str[1:5])
    except:
        year_int = 2024
        
    era_avg_ts = LEAGUE_TS_MAP.get(year_int, 56.0)
    delta_ts = (elite_ts - era_avg_ts) / 100.0

    # 3. SMOOTHED CUBIC EXPONENT
    # Reduced from 3.0 to 2.5. Still violently punishes chuckers, but doesn't mathematically obliterate star players.
    master_luna_score = pc_scaled * ((1.0 + delta_ts) ** 2.5)
    master_luna_score = round(master_luna_score, 1)

    receipts = sorted(elite_games, key=lambda x: x['date'], reverse=True)

    most_recent_team_id = df.sort_values('game_date').iloc[-1]['team_id']
    team_color = TEAM_COLORS.get(int(most_recent_team_id), DEFAULT_TEAM_COLOR)

    return {
        "name": exact_name, "time_frame": selected_season_name, "type": season_type,
        "luna_score": master_luna_score,
        "reg": {"ppg": reg_ppg, "pc": reg_pc, "ts": reg_ts, "count": len(reg_games)},
        "elite": {"ppg": elite_ppg, "pc": elite_pc, "ts": elite_ts, "count": len(elite_games)},
        "receipts": receipts,
        "team_color": team_color,
    }
