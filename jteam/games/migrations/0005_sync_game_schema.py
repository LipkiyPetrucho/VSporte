from django.db import migrations


class Migration(migrations.Migration):
    """
    Синхронизация старых БД (date + time) с текущей схемой (DateTimeField).

    На базах, где start_time уже timestamp и колонки date нет — no-op.
    """

    dependencies = [
        ("games", "0004_game_latitude_game_longitude"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'games_game'
                          AND column_name = 'date'
                    ) THEN
                        ALTER TABLE games_game
                        ADD COLUMN IF NOT EXISTS start_time_new timestamp with time zone;

                        UPDATE games_game
                        SET start_time_new = (date::timestamp + start_time)
                        WHERE start_time_new IS NULL
                          AND date IS NOT NULL
                          AND start_time IS NOT NULL;

                        UPDATE games_game
                        SET start_time_new = COALESCE(created_at, NOW())
                        WHERE start_time_new IS NULL;

                        ALTER TABLE games_game DROP COLUMN IF EXISTS start_time;
                        ALTER TABLE games_game DROP COLUMN IF EXISTS date;

                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'games_game'
                              AND column_name = 'start_time_new'
                        ) THEN
                            ALTER TABLE games_game
                            RENAME COLUMN start_time_new TO start_time;
                        END IF;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='ALTER TABLE games_game DROP COLUMN IF EXISTS "city";',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                ALTER TABLE games_game
                ADD COLUMN IF NOT EXISTS image varchar(100) NOT NULL DEFAULT '';
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
