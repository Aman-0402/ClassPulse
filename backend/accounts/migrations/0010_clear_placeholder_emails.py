from django.contrib.auth import get_user_model
from django.db import migrations


def clear_placeholder_emails(apps, schema_editor):
    # Old imports gave every student a fake "<urn>@bba.local" address. Blank
    # them so the profile shows "Not added yet" and the student adds a real one.
    User = get_user_model()
    User.objects.filter(email__iendswith="@bba.local").update(email="")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_studentscanpolicy"),
    ]

    operations = [
        migrations.RunPython(clear_placeholder_emails, migrations.RunPython.noop),
    ]
