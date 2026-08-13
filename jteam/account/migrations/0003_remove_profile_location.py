from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_create_trgm"),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE "account_profile" DROP COLUMN IF EXISTS "location";',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
