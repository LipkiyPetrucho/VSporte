# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("friendship_request", "Заявка в друзья"),
                    ("friendship_accepted", "Заявка в друзья принята"),
                    ("game_participation_request", "Заявка на участие в игре"),
                    ("game_invitation", "Приглашение на игру"),
                    ("game_participation_accepted", "Заявка на участие принята"),
                    ("game_participation_rejected", "Заявка на участие отклонена"),
                    ("chat_message", "Сообщение в чате игры"),
                    ("game_updated", "Изменение условий игры"),
                ],
                max_length=50,
            ),
        ),
    ]
