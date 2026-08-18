# Чеклист продакшена — https://jteam.ru

Перед открытием: `DJANGO_ENV=prod`, рабочие SMTP/`ADMINS` (или `SENTRY_DSN`), SMS Twilio, сертификаты в `./certs/`.

Автоматика (HTTPS, CSRF-токен, Secure-cookie, HSTS, `__debug__/`, Manifest-статика):

```bash
python scripts/prod_smoke.py --base-url https://jteam.ru
```

## P2 smoke

- [ ] `DJANGO_ENV=prod`, страница ошибки без traceback (`DEBUG=False`)
- [ ] Регистрация / логин / Google / Telegram (`/setdomain` и OAuth redirect на `jteam.ru`)
- [ ] Верификация телефона: SMS на номер, не только в лог (`SMS_BACKEND=twilio`)
- [ ] Создать игру, заявка, WebSocket-чат
- [ ] Статика (CSS/JS с hash Manifest) и медиа аватаров через nginx
- [ ] CSRF: POST форм без 403
- [ ] Cookies `Secure` в DevTools
- [ ] Уведомления + Celery worker/beat живы
- [ ] `__debug__/` недоступен
- [ ] Рестарт контейнеров → `migrate` идемпотентен, данные на месте

## Ошибки

Письма на `ADMINS` (Yandex SMTP) при HTTP 500. Опционально `SENTRY_DSN`.

Проверка: вызвать 500 (например, заведомо битый URL у авторизованного сценария) → письмо `[JTeam]` и/или событие в Sentry. Пустые `ADMINS` и `SENTRY_DSN` в prod дают `RuntimeWarning` при старте.

## Бэкапы Postgres

Сервис `backup` в `docker-compose.prod.yml`: `pg_dump -Fc` в `./backups/` раз в сутки, хранение `BACKUP_KEEP_DAYS` (по умолчанию 14). Volume `postgres_data` — данные БД; дампы лежат на хосте.

```bash
# Дампы на хосте
ls backups/

# Восстановление (остановите web-app/worker/beat; перезапишет объекты в БД)
docker compose -f docker-compose.prod.yml stop web-app worker celery-beat
docker compose -f docker-compose.prod.yml exec backup \
  env CONFIRM=yes /bin/sh /scripts/restore-postgres.sh /backups/jteam_YYYYMMDD_HHMMSS.dump
docker compose -f docker-compose.prod.yml start web-app worker celery-beat
```

Копии `./backups/` лучше увозить с сервера (rsync/S3) — диск хоста и Docker volume могут пропасть вместе.
