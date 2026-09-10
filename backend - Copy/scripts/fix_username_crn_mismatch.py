"""One-off repair: find students where User.username no longer matches
StudentProfile.crn (happens when a CRN correction was approved before the
admin action was fixed to keep them in sync — this is the exact cause of
the "some students' password is wrong" report) and fix both the username
and password to match the current CRN.

Safe to run anytime — a no-op if nothing is mismatched.

cPanel Execute-python-script path: scripts/fix_username_crn_mismatch.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from accounts.models import StudentProfile

if __name__ == "__main__":
    fixed = 0
    for profile in StudentProfile.objects.select_related("user"):
        user = profile.user
        if user.username != profile.crn:
            print(f"Fixing: username {user.username!r} -> {profile.crn!r}")
            user.username = profile.crn
            user.set_password(profile.crn)
            user.save(update_fields=["username", "password"])
            fixed += 1
    print(f"Fixed {fixed} mismatched student account(s).")
