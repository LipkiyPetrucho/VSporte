from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0009_profile_notification_prefs"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="show_gender",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="show_location",
            field=models.BooleanField(default=True),
        ),
    ]
