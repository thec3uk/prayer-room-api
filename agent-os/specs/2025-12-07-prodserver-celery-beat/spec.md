# Specification: Django Prodserver and Celery Beat Migration

## Goal

Migrate from direct gunicorn/celery CLI commands to django-prodserver for unified process management, and migrate beat schedules from code-based definitions in celery.py to database-backed schedules using django-celery-beat.

## Overview/Summary

This specification covers the installation and configuration of two packages:
1. **django-prodserver 2.4.0** - Unified management of production processes (web, worker, beat) through Django's manage.py command
2. **django-celery-beat** - Database-backed periodic task scheduling with Django Admin management

The migration consolidates process management under a single interface and moves schedule definitions from code to the database, enabling non-developer schedule management.

## User Stories

- As a developer, I want to start all production processes using `python manage.py prodserver <process>` so that I have a unified interface for process management
- As a developer, I want periodic task schedules stored in the database so that I can modify schedules without code changes
- As an administrator, I want to manage periodic task schedules through Django Admin so that I can enable/disable or modify schedules without deployments
- As a DevOps engineer, I want the Procfile to use consistent commands so that deployment configuration is simplified

## Goals

1. Install and configure django-prodserver for web, worker, and beat processes
2. Install and configure django-celery-beat for database-backed scheduling
3. Migrate existing beat schedules to database:
   - `moderator-digest-hourly` - Hourly moderator digest emails
   - `user-digest-daily` - Daily user digest emails
   - `user-digest-weekly` - Weekly user digest emails
4. Update Procfile for Dokku deployment
5. Remove code-based schedule definitions from celery.py
6. Maintain zero downtime during migration

## Non-Goals

- Changing the actual task implementations
- Modifying Celery broker or result backend configuration
- Adding new periodic tasks beyond migrating existing ones
- Implementing custom beat scheduler logic
- Multi-tenant schedule isolation

## Current State

### Existing Process Management

The current setup uses direct CLI commands in the Procfile:

```
web: gunicorn prayer_room_api.wsgi:application
worker: celery -A prayer_room_api worker -l INFO
release: ./manage.py migrate --noinput
```

### Existing Beat Schedules

Schedules are defined in `prayer_room_api/celery.py` using Celery's `beat_schedule` configuration:

```python
app.conf.beat_schedule = {
    "moderator-digest-hourly": {
        "task": "prayer_room_api.tasks.send_moderator_digest",
        "schedule": crontab(minute=0),  # Every hour at :00
    },
    "user-digest-daily": {
        "task": "prayer_room_api.tasks.send_user_digest",
        "schedule": crontab(hour=8, minute=0),  # Daily at 8am
        "args": ("daily",),
    },
    "user-digest-weekly": {
        "task": "prayer_room_api.tasks.send_user_digest",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 8am
        "args": ("weekly",),
    },
}
```

### Current Dependencies

- celery = "^5.4.0"
- gunicorn = "^23.0.0"
- Django 5.1.5

## Proposed Changes

### 1. Package Installation

Add to pyproject.toml:
```toml
django-prodserver = "^2.4.0"
django-celery-beat = "^2.8.0"
```

### 2. Django Settings Configuration

Add to `INSTALLED_APPS` (in Settings class):
```python
"django_prodserver",
"django_celery_beat",
```

Add `PRODUCTION_PROCESSES` configuration to ProdSettings:
```python
PRODUCTION_PROCESSES = {
    "web": {
        "BACKEND": "django_prodserver.backends.gunicorn.GunicornServer",
        "ARGS": {
            "bind": f"0.0.0.0:{os.environ.get('PORT', '8000')}",
        },
    },
    "worker": {
        "BACKEND": "django_prodserver.backends.celery.CeleryWorker",
        "APP": "prayer_room_api",
        "ARGS": {
            "loglevel": "info",
        },
    },
    "beat": {
        "BACKEND": "django_prodserver.backends.celery.CeleryBeat",
        "APP": "prayer_room_api",
        "ARGS": {
            "loglevel": "info",
            "scheduler": "django_celery_beat.schedulers:DatabaseScheduler",
        },
    },
}
```

### 3. Procfile Update

Update from direct commands to prodserver:
```
web: python manage.py prodserver web
worker: python manage.py prodserver worker
beat: python manage.py prodserver beat
release: ./manage.py migrate --noinput
```

### 4. Celery Configuration Changes

Remove `beat_schedule` from `prayer_room_api/celery.py`. The file should retain:
- Celery app initialization
- Autodiscover tasks
- Broker configuration (from settings)

### 5. Database Migration

Run django-celery-beat migrations:
```bash
python manage.py migrate django_celery_beat
```

## Technical Details

### Django-Prodserver Architecture

The prodserver command wraps process execution:
- Translates `ARGS` dict to CLI flags (e.g., `{"bind": "0.0.0.0:8000"}` becomes `--bind=0.0.0.0:8000`)
- Provides consistent interface across different backends
- Handles proper signal forwarding for graceful shutdown

### Django-Celery-Beat Models

Key models to understand:
- **PeriodicTask**: Defines task name, schedule reference, arguments, and enabled state
- **CrontabSchedule**: Stores cron expressions (minute, hour, day_of_week, day_of_month, month_of_year)
- **IntervalSchedule**: Stores interval values (every X seconds/minutes/hours/days)
- **PeriodicTasks**: Singleton tracking last schedule change (triggers scheduler reload)

### Scheduler Configuration

The DatabaseScheduler must be explicitly configured for beat:
```python
"scheduler": "django_celery_beat.schedulers:DatabaseScheduler"
```

This replaces the default file-based PersistentScheduler.

## Migration Strategy

### Phase 1: Install Packages (No Impact)

1. Add packages to pyproject.toml
2. Add apps to INSTALLED_APPS
3. Run migrations
4. Deploy (no process changes yet)

### Phase 2: Create Database Schedules

Create a data migration to populate schedules:

```python
# prayer_room_api/migrations/XXXX_create_beat_schedules.py
from django.db import migrations
import json

def create_schedules(apps, schema_editor):
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    
    # Moderator digest - hourly at minute 0
    hourly_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='*',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
        timezone='UTC',
    )
    
    PeriodicTask.objects.update_or_create(
        name='moderator-digest-hourly',
        defaults={
            'task': 'prayer_room_api.tasks.send_moderator_digest',
            'crontab': hourly_schedule,
            'enabled': True,
        }
    )
    
    # User digest daily - 8am every day
    daily_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='8',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
        timezone='UTC',
    )
    
    PeriodicTask.objects.update_or_create(
        name='user-digest-daily',
        defaults={
            'task': 'prayer_room_api.tasks.send_user_digest',
            'crontab': daily_schedule,
            'args': json.dumps(['daily']),
            'enabled': True,
        }
    )
    
    # User digest weekly - Monday 8am
    weekly_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='8',
        day_of_week='1',
        day_of_month='*',
        month_of_year='*',
        timezone='UTC',
    )
    
    PeriodicTask.objects.update_or_create(
        name='user-digest-weekly',
        defaults={
            'task': 'prayer_room_api.tasks.send_user_digest',
            'crontab': weekly_schedule,
            'args': json.dumps(['weekly']),
            'enabled': True,
        }
    )

def reverse_schedules(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name__in=[
        'moderator-digest-hourly',
        'user-digest-daily', 
        'user-digest-weekly'
    ]).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('prayer_room_api', 'XXXX_previous_migration'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),
    ]
    
    operations = [
        migrations.RunPython(create_schedules, reverse_schedules),
    ]
```

### Phase 3: Switch to Prodserver

1. Update Procfile to use prodserver commands
2. Add PRODUCTION_PROCESSES configuration
3. Remove beat_schedule from celery.py
4. Deploy

### Phase 4: Verification

1. Verify all schedules running correctly via Django Admin
2. Monitor task execution logs
3. Confirm tasks execute at expected times

## Testing Plan

### Local Testing

1. **Unit Tests**
   - Test that PRODUCTION_PROCESSES config is valid
   - Test that tasks are still discoverable

2. **Integration Tests**
   - Start prodserver web and verify HTTP responses
   - Start prodserver worker and verify task processing
   - Start prodserver beat with DatabaseScheduler and verify schedule loading

3. **Manual Verification**
   ```bash
   # Test each process starts correctly
   python manage.py prodserver web
   python manage.py prodserver worker
   python manage.py prodserver beat
   
   # Verify schedules in admin
   python manage.py shell
   >>> from django_celery_beat.models import PeriodicTask
   >>> PeriodicTask.objects.all()
   ```

### Staging Environment

1. Deploy full migration to staging
2. Verify all three processes start via Dokku
3. Wait for scheduled tasks to execute
4. Check task results and logs
5. Test enabling/disabling schedules via admin

### Production Deployment

1. Deploy during low-traffic period
2. Monitor process startup in Dokku logs
3. Verify first scheduled task executions
4. Monitor for 24+ hours to confirm all schedules execute

## Rollback Plan

### Immediate Rollback (Pre-Cutover)

If issues during Phase 1-2:
- Simply revert the deployment
- No data migration needed
- beat_schedule in code still active

### Rollback After Cutover

If issues after Phase 3:

1. **Revert Procfile** to direct commands:
   ```
   web: gunicorn prayer_room_api.wsgi:application
   worker: celery -A prayer_room_api worker -l INFO
   release: ./manage.py migrate --noinput
   ```

2. **Restore beat_schedule** in celery.py (keep in git history)

3. **Deploy** with reverted configuration

4. **Database schedules remain** but are unused (default beat scheduler ignores them)

### Data Preservation

- django-celery-beat tables remain in database regardless of rollback
- Schedules can be re-enabled by switching back to DatabaseScheduler
- No data loss in any rollback scenario

## Success Criteria

1. All three processes (web, worker, beat) start successfully via `python manage.py prodserver <process>`
2. Procfile uses prodserver commands and deploys successfully to Dokku
3. All three existing schedules migrated to database and visible in Django Admin
4. Scheduled tasks execute at correct times (verified over 1 week)
5. Administrators can enable/disable schedules via Django Admin without deployment
6. Zero downtime during migration
7. No duplicate task executions during cutover

## Out of Scope

- Custom admin interface for schedule management beyond django-celery-beat defaults
- Automatic schedule sync between code and database
- Schedule versioning or audit logging
- Multi-environment schedule differentiation (dev vs staging vs prod)
- Task result storage configuration changes
- Celery broker changes
- Worker autoscaling configuration
