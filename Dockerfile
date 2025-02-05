FROM python:3.13-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=prayer_room_api.settings \
    PORT=8000 \
    WEB_CONCURRENCY=3

# Install system packages required by Wagtail and Django.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential curl \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    pipx \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system django \
    && adduser --system --ingroup django django

# Requirements are installed here to ensure they will be cached.
RUN pipx ensurepath
RUN pipx install poetry==2.0.0
COPY ./poetry.lock /poetry.lock
COPY ./pyproject.toml /pyproject.toml
RUN poetry install
# RUN pip install -r /requirements.txt

# Copy project code
COPY . .

RUN python manage.py collectstatic --noinput --clear

# Run as non-root user
RUN chown -R django:django /app
USER django

# Run application
CMD gunicorn prayer_room_api.wsgi:application
