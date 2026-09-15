from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0013_rename_training_ii_subject"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(fields=["status", "date"], name="session_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(fields=["section", "date"], name="session_section_date_idx"),
        ),
        migrations.AddIndex(
            model_name="attendance",
            index=models.Index(fields=["session", "student"], name="attendance_session_student_idx"),
        ),
    ]
