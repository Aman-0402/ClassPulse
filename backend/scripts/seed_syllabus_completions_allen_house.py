"""One-off: mark syllabus sessions complete using the real Allen House RCPL
BBA AI Training report (Aug-Sep 2026, Weeks 1-7; Weeks 8-15 were blank
template rows in the source PDF and are not represented here).

Each entry below is (session_number, section, date, present_count), read
directly off the report. Several report rows cover two syllabus sessions at
once ("Topic A & Topic B") - both get marked complete on that row's date.
Two sessions (2 and 3) were split across two class days in the real report;
the completion date used is the day the topic was actually finished, not
the day it started. Holiday rows and the blank 25-Sep rows carry no
attendance and are not included - nothing was "completed" that day.

Safe to re-run: update_or_create per (session, section), so re-running just
re-applies the same data rather than duplicating records.

cPanel Execute-python-script path: scripts/seed_syllabus_completions_allen_house.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from accounts.models import User
from syllabus.models import SyllabusCompletion, SyllabusSession

# (session_number, section, "YYYY-MM-DD", present_count)
RECORDS = [
    # Week 1
    (1, "A", "2026-08-03", 49), (1, "B", "2026-08-03", 40), (1, "C", "2026-08-03", 40),
    (1, "D", "2026-08-04", 10), (1, "E", "2026-08-04", 15), (1, "F", "2026-08-04", 15),
    (2, "A", "2026-08-05", 15), (2, "B", "2026-08-05", 13), (2, "C", "2026-08-05", 21),
    (2, "D", "2026-08-06", 42), (2, "E", "2026-08-06", 49), (2, "F", "2026-08-06", 39),
    (3, "A", "2026-08-07", 38), (3, "B", "2026-08-07", 43), (3, "C", "2026-08-07", 38),
    (3, "D", "2026-08-07", 36), (3, "E", "2026-08-07", 44), (3, "F", "2026-08-07", 38),

    # Week 2
    (4, "A", "2026-08-10", 43), (4, "B", "2026-08-10", 41), (4, "C", "2026-08-10", 34),
    (4, "D", "2026-08-11", 27), (4, "E", "2026-08-11", 39), (4, "F", "2026-08-11", 33),
    (5, "A", "2026-08-12", 36), (5, "B", "2026-08-12", 42), (5, "C", "2026-08-12", 34),
    (5, "D", "2026-08-13", 34), (5, "E", "2026-08-13", 41), (5, "F", "2026-08-13", 42),
    (6, "A", "2026-08-14", 19), (6, "B", "2026-08-14", 27), (6, "C", "2026-08-14", 25),
    (6, "D", "2026-08-14", 22), (6, "E", "2026-08-14", 36), (6, "F", "2026-08-14", 19),

    # Week 3
    (7, "A", "2026-08-17", 29), (7, "B", "2026-08-17", 35), (7, "C", "2026-08-17", 32),
    (7, "D", "2026-08-18", 31), (7, "E", "2026-08-18", 41), (7, "F", "2026-08-18", 34),
    (8, "A", "2026-08-19", 42), (8, "B", "2026-08-19", 47), (8, "C", "2026-08-19", 35),
    (8, "D", "2026-08-20", 37), (8, "E", "2026-08-20", 30), (8, "F", "2026-08-20", 32),
    (9, "A", "2026-08-21", 32), (9, "B", "2026-08-21", 39), (9, "C", "2026-08-21", 29),
    (9, "D", "2026-08-21", 36), (9, "E", "2026-08-21", 38), (9, "F", "2026-08-21", 27),

    # Week 4
    (10, "A", "2026-08-24", 31), (10, "B", "2026-08-24", 30), (10, "C", "2026-08-24", 37),
    (10, "D", "2026-08-25", 36), (10, "E", "2026-08-25", 26), (10, "F", "2026-08-25", 26),
    # A/B/C had holidays on 26 Aug and 28 Aug; their Session 11/12 lands in Week 5 instead.
    (11, "D", "2026-08-27", 10), (11, "E", "2026-08-27", 8), (11, "F", "2026-08-27", 12),
    (12, "D", "2026-08-27", 10), (12, "E", "2026-08-27", 8), (12, "F", "2026-08-27", 12),

    # Week 5
    (11, "A", "2026-09-09", 41), (11, "B", "2026-09-09", 28), (11, "C", "2026-09-09", 25),
    (12, "A", "2026-09-09", 41), (12, "B", "2026-09-09", 28), (12, "C", "2026-09-09", 25),
    # D/E/F had a holiday on 7-8 Sep; their Session 13/14 lands here instead.
    (13, "D", "2026-09-10", 26), (13, "E", "2026-09-10", 42), (13, "F", "2026-09-10", 39),
    (14, "D", "2026-09-10", 26), (14, "E", "2026-09-10", 42), (14, "F", "2026-09-10", 39),
    (15, "A", "2026-09-11", 34), (15, "B", "2026-09-11", 28), (15, "C", "2026-09-11", 21),
    (15, "D", "2026-09-11", 27), (15, "E", "2026-09-11", 24), (15, "F", "2026-09-11", 39),

    # Week 6
    (13, "A", "2026-09-14", 47), (13, "B", "2026-09-14", 37), (13, "C", "2026-09-14", 30),
    (14, "A", "2026-09-14", 47), (14, "B", "2026-09-14", 37), (14, "C", "2026-09-14", 30),
    (17, "D", "2026-09-15", 45), (17, "E", "2026-09-15", 48), (17, "F", "2026-09-15", 45),
    (22, "D", "2026-09-15", 45), (22, "E", "2026-09-15", 48), (22, "F", "2026-09-15", 45),
    (17, "A", "2026-09-16", 45), (17, "B", "2026-09-16", 42), (17, "C", "2026-09-16", 43),
    (22, "A", "2026-09-16", 45), (22, "B", "2026-09-16", 42), (22, "C", "2026-09-16", 43),
    (18, "D", "2026-09-17", 33), (18, "E", "2026-09-17", 44), (18, "F", "2026-09-17", 44),
    (19, "D", "2026-09-17", 33), (19, "E", "2026-09-17", 44), (19, "F", "2026-09-17", 44),
    (16, "A", "2026-09-18", 42), (16, "B", "2026-09-18", 38), (16, "C", "2026-09-18", 33),
    (16, "D", "2026-09-18", 31), (16, "E", "2026-09-18", 34), (16, "F", "2026-09-18", 37),

    # Week 7
    (18, "A", "2026-09-21", 41), (18, "B", "2026-09-21", 43), (18, "C", "2026-09-21", 38),
    (19, "A", "2026-09-21", 41), (19, "B", "2026-09-21", 43), (19, "C", "2026-09-21", 38),
    (23, "D", "2026-09-22", 41), (23, "E", "2026-09-22", 47), (23, "F", "2026-09-22", 33),
    (24, "D", "2026-09-22", 41), (24, "E", "2026-09-22", 47), (24, "F", "2026-09-22", 33),
    (23, "A", "2026-09-23", 16), (23, "B", "2026-09-23", 4), (23, "C", "2026-09-23", 16),
    (24, "A", "2026-09-23", 16), (24, "B", "2026-09-23", 4), (24, "C", "2026-09-23", 16),
    # 24-Sep D/E/F rows are the same topic repeated (a continuation/practice
    # session, not a new topic) - the 22-Sep record above already covers it,
    # so it's deliberately not duplicated here.
    # 25-Sep rows across all sections are blank in the source PDF (no topic,
    # no attendance) - nothing to record.
]

if __name__ == "__main__":
    sessions_by_number = {s.session_number: s for s in SyllabusSession.objects.all()}
    marked_by = User.objects.filter(role=User.ROLE_TEACHER).first()

    created = updated = missing_sessions = 0
    for session_number, section, date, present_count in RECORDS:
        session = sessions_by_number.get(session_number)
        if session is None:
            print(f"Session {session_number} not found in the syllabus - skipping.")
            missing_sessions += 1
            continue
        _, was_created = SyllabusCompletion.objects.update_or_create(
            session=session,
            section=section,
            defaults={"date": date, "present_count": present_count, "marked_by": marked_by},
        )
        created += was_created
        updated += not was_created

    print(f"{created} completion(s) created, {updated} updated, {missing_sessions} session(s) not found.")
    print(f"Total completion records now: {SyllabusCompletion.objects.count()}")
