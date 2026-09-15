from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_alter_passwordresetotp_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="trusted_device_hash",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="trusted_device_bound_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
