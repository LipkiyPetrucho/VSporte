from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0012_game_team_assignment"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="game",
            index=models.Index(
                fields=["status", "start_time"],
                name="games_game_status_start_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="game",
            index=models.Index(fields=["sport"], name="games_game_sport_idx"),
        ),
        migrations.AddIndex(
            model_name="game",
            index=models.Index(
                fields=["-start_time"],
                name="games_game_start_time_idx",
            ),
        ),
    ]
