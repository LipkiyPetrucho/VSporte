from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("account", "0012_phone_verification_login_purpose"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="friendship",
            index=models.Index(
                fields=["from_user", "status"],
                name="account_fri_from_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="friendship",
            index=models.Index(
                fields=["to_user", "status"],
                name="account_fri_to_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userblock",
            index=models.Index(fields=["blocker"], name="account_use_blocker_idx"),
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS auth_user_username_trgm "
                "ON auth_user USING gin (username gin_trgm_ops);"
            ),
            reverse_sql="DROP INDEX IF EXISTS auth_user_username_trgm;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS auth_user_first_name_trgm "
                "ON auth_user USING gin (first_name gin_trgm_ops);"
            ),
            reverse_sql="DROP INDEX IF EXISTS auth_user_first_name_trgm;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS auth_user_last_name_trgm "
                "ON auth_user USING gin (last_name gin_trgm_ops);"
            ),
            reverse_sql="DROP INDEX IF EXISTS auth_user_last_name_trgm;",
        ),
    ]
