from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0005_profile_gender_bio"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="interests",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="profile",
            name="show_email",
            field=models.BooleanField(default=True),
        ),
    ]
