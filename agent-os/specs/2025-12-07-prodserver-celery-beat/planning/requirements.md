# Requirements Research

## User Answers

1. **django-prodserver**: Using https://django-prodserver.readthedocs.io/en/latest/ (version 2.4.0)
2. **Current setup**: Running gunicorn directly, wants to switch to Django management commands
3. **Scheduled tasks**: Already configured in `prayer_room_api/celery.py`:
   - `moderator-digest-hourly`: Every hour at :00
   - `user-digest-daily`: Daily at 8am
   - `user-digest-weekly`: Monday at 8am
4. **Celery workers**: Already configured in Procfile
5. **Beat scheduler storage**: django-celery-beat (database-backed with admin interface)
6. **Deployment**: Procfile to Dokku
7. **Process management**: All processes in Procfile
8. **Out of scope**: Nothing excluded

## Current State Analysis

### Current Procfile
```
web: gunicorn prayer_room_api.wsgi:application
worker: celery -A prayer_room_api worker -l INFO
release: ./manage.py migrate --noinput
```

### Current Celery Configuration (prayer_room_api/celery.py)
- Celery app configured with Django settings
- Beat schedule defined in code (not database):
  - `moderator-digest-hourly`
  - `user-digest-daily`
  - `user-digest-weekly`

### Current Dependencies (pyproject.toml)
- celery = "^5.4.0"
- gunicorn = "^23.0.0"
- No django-prodserver
- No django-celery-beat

### Settings Structure
- Uses django-classy-settings (cbs)
- `Settings` base class for development
- `ProdSettings` for production
- CELERY_BROKER_URL configured in ProdSettings from RABBITMQ_URL env var

## Required Changes

### 1. Install new packages
- `django-prodserver` - production server management
- `django-celery-beat` - database-backed beat scheduler

### 2. Configure django-prodserver
Add to INSTALLED_APPS:
```python
"django_prodserver",
```

Add PRODUCTION_PROCESSES setting:
```python
PRODUCTION_PROCESSES = {
    "web": {
        "BACKEND": "django_prodserver.backends.gunicorn.GunicornServer",
        "ARGS": {"bind": "0.0.0.0:$PORT"},  # Dokku provides PORT env var
    },
    "worker": {
        "BACKEND": "django_prodserver.backends.celery.CeleryWorker",
        "APP": "prayer_room_api",
        "ARGS": {"loglevel": "INFO"},
    },
    "beat": {
        "BACKEND": "django_prodserver.backends.celery.CeleryBeat",  # If available
        "APP": "prayer_room_api",
        "ARGS": {},
    },
}
```

### 3. Configure django-celery-beat
Add to INSTALLED_APPS:
```python
"django_celery_beat",
```

Decision needed: Keep beat schedule in code OR migrate to database-backed?
- If database-backed: Remove `app.conf.beat_schedule` from celery.py
- If code-based: Keep existing schedule, just add beat process

### 4. Update Procfile
```
web: python manage.py prodserver web
worker: python manage.py prodserver worker
beat: python manage.py prodserver beat
release: ./manage.py migrate --noinput
```

### 5. Run migrations
django-celery-beat requires database tables for:
- PeriodicTask
- IntervalSchedule
- CrontabSchedule
- SolarSchedule
- ClockedSchedule

## Resolved Questions

1. **Beat scheduler**: Migrate existing beat schedule from code to database (django-celery-beat admin) - **Option A confirmed**

2. **CeleryBeat backend**: django-prodserver has a CeleryBeat backend - **confirmed**

3. **Gunicorn binding**: Dokku provides PORT env var - need to confirm django-prodserver can use environment variables in ARGS.

## django-prodserver Capabilities

From docs (v2.4.0):
- **Web backends**: GunicornServer, GranianASGIServer, GranianWSGIServer, WaitressServer, UvicornServer, UvicornWSGIServer
- **Worker backends**: CeleryWorker, CeleryBeat, DjangoTasksWorker
- **Usage**: `python manage.py prodserver <process_name>`
- Supports custom backends by extending BaseServerBackend

## Final Implementation Plan

1. Install django-prodserver and django-celery-beat
2. Add both to INSTALLED_APPS
3. Configure PRODUCTION_PROCESSES with web, worker, and beat
4. Remove hardcoded beat_schedule from celery.py
5. Create database migration for django-celery-beat tables
6. Add data migration to seed initial schedules in database
7. Update Procfile to use `python manage.py prodserver <process>`
