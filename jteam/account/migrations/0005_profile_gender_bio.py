from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0004_friendship"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="bio",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("", "Не указан"), ("male", "Мужской"), ("female", "Женский")],
                default="",
                max_length=10,
            ),
        ),
    ]
