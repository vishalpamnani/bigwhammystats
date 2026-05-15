from pathlib import Path

LEAGUE_ID = 1124151
IRON_MAN_BASE_GW = 19

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DB_PATH = DATA_DIR / "big_whammy_snapshots.sqlite3"
