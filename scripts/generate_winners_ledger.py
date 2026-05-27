import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.winners_ledger import LEDGER_PATH, save_winners_ledger


def main() -> None:
    ledger = save_winners_ledger()
    print(f"Saved {len(ledger.get('entries', []))} ledger entries to {LEDGER_PATH}")


if __name__ == "__main__":
    main()
