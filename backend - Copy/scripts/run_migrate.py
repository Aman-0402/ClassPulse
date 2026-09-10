"""Run pending migrations. cPanel Execute-python-script path: scripts/run_migrate.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.core.management import call_command

if __name__ == "__main__":
    call_command("migrate", interactive=False)
