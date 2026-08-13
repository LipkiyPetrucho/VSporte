from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0008_userblock"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="notify_activity_updates",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="notify_chat_messages",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="notify_game_reminders",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="notify_social_updates",
            field=models.BooleanField(default=True),
        ),
    ]
