FROM python:3.13-slim-bookworm AS base



ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=prayer_room_api.settings \
    PORT=8000 \
    WEB_CONCURRENCY=3 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Install system packages required by Wagtail and Django.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential curl \
    libpq-dev \
    postgresql-client \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    pipx \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system django \
    && adduser --system --ingroup django django

FROM base AS builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Requirements are installed here to ensure they will be cached.
RUN pipx ensurepath
RUN pipx install poetry==2.0.0

COPY entrypoint README.md pyproject.toml poetry.lock ./
RUN /root/.local/bin/poetry install --only main --no-root --no-directory

FROM base AS runtime

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app
# Copy project code
COPY . .

# Run as non-root user
RUN chown -R django:django /app
USER django

# Run application
ENTRYPOINT [ "/app/entrypoint" ]
