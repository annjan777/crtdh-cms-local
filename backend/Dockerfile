FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Migrations are expected to run separately (entrypoint override / docker-compose
# `command`, e.g. `python manage.py migrate && gunicorn ...`) rather than baked
# into this image's default CMD.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
