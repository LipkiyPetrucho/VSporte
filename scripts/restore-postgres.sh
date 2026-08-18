#!/bin/sh
# Восстановление custom-format дампа в текущую БД (PG* из окружения).
# Опасно: перезаписывает объекты. Требует CONFIRM=yes.
set -eu

DUMP="${1:?usage: restore-postgres.sh <dump-file>}"

if [ "${CONFIRM:-}" != "yes" ]; then
    echo "Refusing to restore ${DUMP} into ${PGDATABASE:-?} without CONFIRM=yes"
    exit 1
fi

if [ ! -f "$DUMP" ]; then
    echo "Dump not found: ${DUMP}"
    exit 1
fi

echo "Restoring ${DUMP} into ${PGDATABASE} as ${PGUSER}@${PGHOST}"
pg_restore --clean --if-exists --no-owner --dbname="$PGDATABASE" "$DUMP"
echo "Restore finished"
