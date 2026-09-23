"""Find StudentProfile.photo rows pointing at a file that no longer exists on
disk (the browser shows those as a broken image) and clear them so the
student instead sees "Add photo" and can re-upload.

Read-only by default - prints what it would fix. Pass --fix to actually clear
the broken rows in the database.

cPanel Execute-python-script path: scripts/find_missing_photos.py
                                    scripts/find_missing_photos.py --fix
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from accounts.models import StudentProfile

if __name__ == "__main__":
    fix = "--fix" in sys.argv
    missing = []
    for profile in StudentProfile.objects.exclude(photo="").exclude(photo__isnull=True):
        if not profile.photo.storage.exists(profile.photo.name):
            missing.append(profile)

    if not missing:
        print("No broken photo references found.")
        sys.exit(0)

    print(f"{len(missing)} student(s) reference a photo file that is missing on disk:")
    for profile in missing:
        print(f"  {profile.crn} ({profile.user.get_full_name() or profile.user.username}) -> {profile.photo.name}")

    if fix:
        for profile in missing:
            profile.photo = None
            profile.save(update_fields=["photo"])
        print(f"\nCleared {len(missing)} broken photo reference(s). Ask these students to re-upload.")
    else:
        print("\nRun again with --fix to clear these so the profile shows \"Add photo\" instead of a broken image.")
