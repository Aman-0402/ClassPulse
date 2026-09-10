"""One-off: reset every existing student's password to match their CRN
(username is already their CRN). Run once after switching the credential
scheme — new imports via import_students.py already use this scheme, this
just catches everyone imported before the switch.

cPanel Execute-python-script path: scripts/reset_student_passwords_to_crn.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.contrib.auth import get_user_model
from accounts.models import StudentProfile

if __name__ == "__main__":
    User = get_user_model()
    updated = 0
    for profile in StudentProfile.objects.select_related("user"):
        user = profile.user
        user.set_password(profile.crn)
        user.save(update_fields=["password"])
        updated += 1
    print(f"Reset {updated} student passwords to match their CRN.")
