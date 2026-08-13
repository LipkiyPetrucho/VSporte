from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    """
    Добавляет поля Place, если их ещё нет.
    На базах, где колонки уже созданы вручную / старой схемой — no-op в SQL.
    """

    dependencies = [
        ("location", "0002_seed_cities"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="place",
                    name="description",
                    field=models.TextField(blank=True, default=""),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name="place",
                    name="image",
                    field=models.ImageField(blank=True, upload_to="places/%Y/%m/%d"),
                ),
                migrations.AddField(
                    model_name="place",
                    name="price",
                    field=models.DecimalField(
                        decimal_places=0, default=0, max_digits=10
                    ),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name="place",
                    name="available",
                    field=models.BooleanField(default=True),
                ),
                migrations.AddField(
                    model_name="place",
                    name="created",
                    field=models.DateTimeField(
                        auto_now_add=True, default=django.utils.timezone.now
                    ),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name="place",
                    name="updated",
                    field=models.DateTimeField(
                        auto_now=True, default=django.utils.timezone.now
                    ),
                    preserve_default=False,
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE location_place
                        ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT '';
                        ALTER TABLE location_place
                        ADD COLUMN IF NOT EXISTS image varchar(100) NOT NULL DEFAULT '';
                        ALTER TABLE location_place
                        ADD COLUMN IF NOT EXISTS price numeric(10, 0) NOT NULL DEFAULT 0;
                        ALTER TABLE location_place
                        ADD COLUMN IF NOT EXISTS available boolean NOT NULL DEFAULT true;
                        ALTER TABLE location_place
                        ADD COLUMN IF NOT EXISTS created timestamptz NOT NULL DEFAULT NOW();
                        ALTER TABLE location_place
                        ADD COLUMN IF NOT EXISTS updated timestamptz NOT NULL DEFAULT NOW();
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
