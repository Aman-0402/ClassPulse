from django.db import migrations


def rename_subject(apps, schema_editor):
    ClassSchedule = apps.get_model("attendance", "ClassSchedule")
    ClassSchedule.objects.filter(subject="Training II").update(subject="AI Training")


def revert_subject(apps, schema_editor):
    ClassSchedule = apps.get_model("attendance", "ClassSchedule")
    ClassSchedule.objects.filter(subject="AI Training").update(subject="Training II")


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0012_alter_classschedule_subject"),
    ]

    operations = [
        migrations.RunPython(rename_subject, revert_subject),
    ]
