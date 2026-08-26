"""Run after every deploy: migrate + collectstatic.
cPanel Execute-python-script path: scripts/post_deploy.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.core.management import call_command

if __name__ == "__main__":
    print("Running migrations...")
    call_command("migrate", interactive=False)
    print("Collecting static files...")
    call_command("collectstatic", interactive=False, verbosity=0)
    print("post_deploy done.")
