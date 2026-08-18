#!/bin/sh
# Периодический pg_dump (custom format) в /backups.
# Восстановление: CONFIRM=yes sh /scripts/restore-postgres.sh /backups/<file>.dump
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
PREFIX="${BACKUP_PREFIX:-jteam}"

mkdir -p "$BACKUP_DIR"

echo "Postgres backup: every ${INTERVAL}s, keep ${KEEP_DAYS} days, dir ${BACKUP_DIR}"

while true; do
    ts=$(date +%Y%m%d_%H%M%S)
    dest="${BACKUP_DIR}/${PREFIX}_${ts}.dump"
    echo "$(date) dumping ${PGDATABASE:-db} to ${dest}"
    pg_dump -Fc --no-owner --file="$dest"
    echo "Wrote ${dest}"

    find "$BACKUP_DIR" -type f -name "${PREFIX}_*.dump" -mtime +"${KEEP_DAYS}" -print -delete || true

    sleep "$INTERVAL"
done
