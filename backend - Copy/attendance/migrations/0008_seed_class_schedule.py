from django.db import migrations

MON, TUE, WED, THU, FRI = 0, 1, 2, 3, 4

# BBA 3rd Semester (Training II) weekly timetable, 2026-27, Lab 3E.
SLOTS = [
    (MON, "10:05", "10:55", "A"),
    (MON, "11:05", "11:55", "A"),
    (MON, "12:45", "13:35", "B"),
    (MON, "13:35", "14:25", "B"),
    (MON, "14:35", "15:25", "C"),
    (MON, "15:25", "16:15", "C"),
    (TUE, "10:05", "10:55", "D"),
    (TUE, "11:05", "11:55", "D"),
    (TUE, "12:45", "13:35", "E"),
    (TUE, "13:35", "14:25", "E"),
    (TUE, "14:35", "15:25", "F"),
    (TUE, "15:25", "16:15", "F"),
    (WED, "10:05", "10:55", "A"),
    (WED, "11:05", "11:55", "A"),
    (WED, "12:45", "13:35", "B"),
    (WED, "13:35", "14:25", "B"),
    (WED, "14:35", "15:25", "C"),
    (WED, "15:25", "16:15", "C"),
    (THU, "10:05", "10:55", "D"),
    (THU, "11:05", "11:55", "D"),
    (THU, "12:45", "13:35", "E"),
    (THU, "13:35", "14:25", "E"),
    (THU, "14:35", "15:25", "F"),
    (THU, "15:25", "16:15", "F"),
    (FRI, "10:05", "10:55", "A"),
    (FRI, "11:05", "11:55", "E"),
    (FRI, "12:45", "13:35", "C"),
    (FRI, "13:35", "14:25", "B"),
    (FRI, "14:35", "15:25", "D"),
    (FRI, "15:25", "16:15", "F"),
]


def seed_schedule(apps, schema_editor):
    ClassSchedule = apps.get_model("attendance", "ClassSchedule")
    ClassSchedule.objects.bulk_create(
        [
            ClassSchedule(day_of_week=day, start_time=start, end_time=end, section=section)
            for day, start, end, section in SLOTS
        ]
    )


def remove_seeded_schedule(apps, schema_editor):
    ClassSchedule = apps.get_model("attendance", "ClassSchedule")
    ClassSchedule.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0007_classschedule"),
    ]

    operations = [
        migrations.RunPython(seed_schedule, remove_seeded_schedule),
    ]
