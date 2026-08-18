FROM python:3.11-alpine3.18

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Установка необходимых пакетов
RUN apk update && \
    apk add --no-cache postgresql-libs gcc musl-dev \
    pango-dev zlib-dev jpeg-dev openjpeg-dev g++ libffi-dev \
    font-liberation netcat-openbsd

# Копирование requirements.txt, кода и entrypoint
COPY requirements.txt /temp/requirements.txt
COPY jteam /jteam
COPY entrypoint.sh /entrypoint.sh

WORKDIR /jteam
EXPOSE 8000

# Установка зависимостей из requirements.txt
RUN pip install -r /temp/requirements.txt && chmod +x /entrypoint.sh

# web-app: migrate + collectstatic + Daphne (worker/beat переопределяют entrypoint)
CMD ["sh", "/entrypoint.sh"]
