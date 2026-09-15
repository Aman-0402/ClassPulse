from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_studentprofile_trusted_device"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="studentprofile",
            index=models.Index(fields=["section", "crn"], name="student_section_crn_idx"),
        ),
    ]
