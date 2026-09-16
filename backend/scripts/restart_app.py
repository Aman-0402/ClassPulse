"""Restart the cPanel Passenger app by touching tmp/restart.txt.

cPanel's Restart button can fail with a UI/server-response error even when the
Python app itself is fine. Run this from Setup Python App > Execute Python
Script as:

    scripts/restart_app.py
"""
from pathlib import Path


if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parent.parent
    restart_file = backend_dir / "tmp" / "restart.txt"
    restart_file.parent.mkdir(parents=True, exist_ok=True)
    restart_file.touch()
    print(f"Restart signal written: {restart_file}")
