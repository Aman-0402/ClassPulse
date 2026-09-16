"""Run a cPanel-friendly backend health check.

Use from Setup Python App > Execute Python Script:

    scripts/health_check.py

This checks Django, database connectivity, pending migrations, and a few API
paths internally, without needing browser/HTTPS access.
"""
import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.core.management import call_command
from django.db import connection
from django.test import Client


def run_command(name, *args):
    output = StringIO()
    call_command(name, *args, stdout=output, stderr=output)
    return output.getvalue().strip()


if __name__ == "__main__":
    print("== ClassPulse health check ==")

    print("\n[1] Django system check")
    print(run_command("check") or "OK")

    print("\n[2] Database connection")
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print(f"OK: SELECT 1 -> {cursor.fetchone()[0]}")

    print("\n[3] Pending migrations")
    migration_output = run_command("migrate", "--check")
    print(migration_output or "OK: no pending migrations")

    print("\n[4] Internal API checks")
    client = Client(HTTP_HOST="arxinfo.info")
    for path in ("/api/attendance/schedule/today/", "/api/student/login/"):
        response = client.get(path)
        print(f"{path} -> {response.status_code}")

    print("\nHealth check finished.")
