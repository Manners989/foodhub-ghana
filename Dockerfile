# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr,
# so `docker logs` shows output immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps needed to build psycopg2 and Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libjpeg62-turbo-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt

COPY . .

# Run as a non-root user — never run the app as root inside the container.
RUN adduser --disabled-password --no-create-home appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "foodhub.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
