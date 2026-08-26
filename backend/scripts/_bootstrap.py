"""Shared Django bootstrap for standalone scripts run outside `manage.py`.

cPanel's "Execute python script" box runs a .py file directly with the app's
venv interpreter — it does not go through manage.py, so Django has to be set
up manually before any model/ORM code can run. Every script in this folder
starts with `from _bootstrap import setup_django; setup_django()`.
"""
import os
import sys
from pathlib import Path


def setup_django():
    backend_dir = Path(__file__).resolve().parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "classpulse.settings")
    import django
    django.setup()
