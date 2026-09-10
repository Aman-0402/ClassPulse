"""Create (or reset) the teacher/admin account used to log into the app.

Reads credentials from environment variables — never hardcode a password
here, this file is committed to git. Set these first, e.g. via cPanel's
Setup Python App > Environment Variables, or inline for one run:

    ADMIN_USERNAME=admin ADMIN_PASSWORD=... ADMIN_EMAIL=admin@arxinfo.info

cPanel Execute-python-script path: scripts/create_superadmin.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.contrib.auth import get_user_model

if __name__ == "__main__":
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    email = os.environ.get("ADMIN_EMAIL", "")

    if not username or not password:
        sys.exit(
            "ADMIN_USERNAME and ADMIN_PASSWORD env vars are required — "
            "set them (Setup Python App > Environment Variables) and re-run."
        )

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "role": User.ROLE_TEACHER},
    )
    user.role = User.ROLE_TEACHER
    user.is_staff = True
    user.is_superuser = True
    user.email = email or user.email
    user.set_password(password)
    user.save()

    print(f"{'Created' if created else 'Updated'} teacher/admin account: {username}")
    print(f"role={user.role!r} is_staff={user.is_staff} is_superuser={user.is_superuser} is_active={user.is_active}")
