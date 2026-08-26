"""Bulk-import students from the per-section CSV roster files.

Expects CSVs named "Section <X>.csv" (e.g. "Section D.csv") with columns
"Registration Code (CRN)", "Roll No. (URN)", "Student Name" — the exact
format the real rosters come in. `Data/` holds real student PII and is
gitignored, so it has to be uploaded separately (cPanel File Manager) —
this script never ships with student data baked in.

Credential scheme (matches the original import, see Agent.md):
  username = CRN (e.g. "25BBA015")
  password = first 4 letters of first name, uppercase, + CRN with its
             leading 2-digit year prefix stripped
             e.g. "Divyanshi Gautam" + "25BBA015" -> "DIVYBBA015"

Existing CRNs are skipped, not overwritten — re-running is safe.

cPanel Execute-python-script path: scripts/import_students.py
Optional env var: DATA_DIR (default "Data", relative to backend/)
"""
import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.contrib.auth import get_user_model
from accounts.models import StudentProfile

COURSE = "BBA"
SEMESTER = 3


def derive_credentials(crn: str, full_name: str) -> tuple[str, str]:
    first_name = full_name.strip().split()[0]
    name_part = re.sub(r"[^A-Za-z]", "", first_name).upper()[:4]
    crn_suffix = re.sub(r"^\d{2}", "", crn.strip(), count=1)
    return crn.strip(), f"{name_part}{crn_suffix}"


def section_from_filename(path: Path) -> str:
    match = re.search(r"Section\s+([A-Za-z0-9]+)", path.stem)
    if not match:
        raise ValueError(f"Can't derive section from filename: {path.name}")
    return match.group(1).upper()


def import_file(path: Path):
    User = get_user_model()
    section = section_from_filename(path)
    created, skipped = 0, 0

    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            crn = row["Registration Code (CRN)"].strip()
            urn = row["Roll No. (URN)"].strip()
            name = row["Student Name"].strip().title()

            if StudentProfile.objects.filter(crn=crn).exists():
                skipped += 1
                continue

            username, password = derive_credentials(crn, name)
            user = User.objects.create_user(
                username=username,
                password=password,
                email=f"{urn}@bba.local",
                first_name=name,
                role=User.ROLE_STUDENT,
            )
            StudentProfile.objects.create(
                user=user,
                crn=crn,
                urn=urn,
                course=COURSE,
                semester=SEMESTER,
                section=section,
            )
            created += 1

    print(f"{path.name}: {created} created, {skipped} skipped (already existed)")


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / os.environ.get("DATA_DIR", "Data")
    if not data_dir.is_dir():
        sys.exit(f"Data directory not found: {data_dir} — upload the section CSVs there first.")

    csv_files = sorted(data_dir.glob("Section *.csv"))
    if not csv_files:
        sys.exit(f"No 'Section *.csv' files found in {data_dir}")

    for csv_path in csv_files:
        import_file(csv_path)
