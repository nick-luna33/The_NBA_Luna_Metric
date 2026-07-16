import sqlite3
conn = sqlite3.connect("nba_master.db")
conn.cursor().execute("DROP TABLE IF EXISTS Player_Game_Logs")
conn.commit()
conn.close()
