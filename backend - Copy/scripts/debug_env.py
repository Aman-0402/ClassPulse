"""One-off diagnostic: prints what Django actually sees for DB settings,
password masked to length only. Delete after use — not meant to stay.
cPanel Execute-python-script path: scripts/debug_env.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.conf import settings

if __name__ == "__main__":
    db = settings.DATABASES["default"]
    pw = db["PASSWORD"]
    print(f"NAME={db['NAME']!r}")
    print(f"USER={db['USER']!r}")
    print(f"HOST={db['HOST']!r}")
    print(f"PORT={db['PORT']!r}")
    print(f"PASSWORD length={len(pw)} first={pw[:1]!r} last={pw[-1:]!r}")
    print(f"BASE_DIR={settings.BASE_DIR}")
    print(f".env exists at BASE_DIR? {(settings.BASE_DIR / '.env').is_file()}")
