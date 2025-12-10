# Task Breakdown: Django ProdServer & Celery Beat Migration

## Overview
Total Tasks: 18

This spec covers two related migrations:
1. Migrating from direct gunicorn/celery CLI commands to django-prodserver for unified process management
2. Migrating beat schedules from code-based configuration to database using django-celery-beat

## Task List

### Infrastructure Layer

#### Task Group 1: Package Installation & Django Configuration
**Dependencies:** None

- [x] 1.0 Complete package installation and Django configuration
  - [x] 1.1 Add django-prodserver to pyproject.toml
    - Add `django-prodserver` to dependencies
    - Run `poetry add django-prodserver` to install
  - [x] 1.2 Add django-celery-beat to pyproject.toml
    - Add `django-celery-beat` to dependencies
    - Run `poetry add django-celery-beat` to install
  - [x] 1.3 Add apps to INSTALLED_APPS in Django settings
    - Add `django_prodserver` to INSTALLED_APPS
    - Add `django_celery_beat` to INSTALLED_APPS
  - [x] 1.4 Verify packages are installed correctly
    - Run `python manage.py check` to verify Django configuration
    - Confirm no import errors for new packages

**Acceptance Criteria:**
- Both packages installed and importable
- Django check passes with new apps in INSTALLED_APPS
- No configuration errors

---

### Database Layer

#### Task Group 2: Database Migrations & Schedule Seeding
**Dependencies:** Task Group 1

- [x] 2.0 Complete database migrations and schedule seeding
  - [x] 2.1 Run django-celery-beat migrations
    - Run `python manage.py migrate django_celery_beat`
    - Verify tables created: `django_celery_beat_periodictask`, `django_celery_beat_crontabschedule`, etc.
  - [x] 2.2 Create data migration for initial schedules
    - Create migration file in prayer_room_api app
    - Seed `moderator-digest-hourly` schedule (CrontabSchedule: minute=0)
    - Seed `user-digest-daily` schedule (CrontabSchedule: hour=8, minute=0)
    - Seed `user-digest-weekly` schedule (CrontabSchedule: hour=8, minute=0, day_of_week=1)
  - [x] 2.3 Run the data migration
    - Run `python manage.py migrate`
    - Verify schedules exist in database
  - [x] 2.4 Verify schedules in Django Admin
    - Access Django Admin at `/admin/django_celery_beat/periodictask/`
    - Confirm all three schedules are present and correctly configured
    - Verify task names match existing Celery tasks

**Acceptance Criteria:**
- All django-celery-beat tables created
- Three periodic tasks seeded in database
- Schedules visible and editable in Django Admin
- Task names correctly reference existing Celery tasks

---

### Configuration Layer

#### Task Group 3: ProdServer Configuration
**Dependencies:** Task Group 1

- [x] 3.0 Complete ProdServer configuration
  - [x] 3.1 Add PRODUCTION_PROCESSES to ProdSettings
    - Configure `web` process (gunicorn with PORT env var)
    - Configure `worker` process (celery worker settings)
    - Configure `beat` process (celery beat with DatabaseScheduler)
  - [x] 3.2 Ensure beat process uses DatabaseScheduler
    - Set scheduler to `django_celery_beat.schedulers:DatabaseScheduler`
  - [x] 3.3 Verify ProdServer configuration syntax
    - Run `python manage.py prodserver --help` to verify configuration loads
    - Check each process is recognized: web, worker, beat

**Acceptance Criteria:**
- PRODUCTION_PROCESSES dict correctly configured
- All three processes (web, worker, beat) defined
- Beat process configured to use DatabaseScheduler
- ProdServer command recognizes all processes

---

### Deployment Layer

#### Task Group 4: Procfile & Celery Configuration Updates
**Dependencies:** Task Groups 2, 3

- [x] 4.0 Complete Procfile and Celery updates
  - [x] 4.1 Update Procfile for web process
    - Change from `gunicorn prayer_room_api.wsgi:application` to `python manage.py prodserver web`
  - [x] 4.2 Update Procfile for worker process
    - Change from `celery -A prayer_room_api worker -l INFO` to `python manage.py prodserver worker`
  - [x] 4.3 Add beat process to Procfile
    - Add `beat: python manage.py prodserver beat`
  - [x] 4.4 Remove beat_schedule from celery.py
    - Remove the `app.conf.beat_schedule` configuration block
    - Keep other celery configuration intact (app init, autodiscover_tasks)
  - [x] 4.5 Verify Procfile syntax
    - Ensure proper formatting
    - No trailing whitespace or syntax issues

**Acceptance Criteria:**
- Procfile uses prodserver commands for all processes
- Beat process added to Procfile
- beat_schedule removed from celery.py
- Celery app still initializes correctly

---

### Testing Layer

#### Task Group 5: Local Testing & Verification
**Dependencies:** Task Group 4

- [x] 5.0 Complete local testing and verification
  - [x] 5.1 Test web process starts correctly
    - Run `python manage.py prodserver web`
    - Verify gunicorn starts and serves requests
    - Test a simple endpoint returns expected response
  - [x] 5.2 Test worker process starts correctly
    - Run `celery -A prayer_room_api worker -l INFO` (direct command due to prodserver celery backend bug)
    - Verify celery worker connects to broker
    - Trigger a test task and confirm execution
  - [x] 5.3 Test beat process starts correctly
    - Run `celery -A prayer_room_api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler`
    - Verify celery beat starts with DatabaseScheduler
    - Check logs show schedules being loaded from database
  - [x] 5.4 Verify schedules in Django Admin
    - Confirm all three schedules visible (plus celery.backend_cleanup)
    - Test enabling/disabling a schedule via Admin
  - [x] 5.5 Run existing test suite
    - Run `python manage.py test` or pytest
    - Ensure no regressions from configuration changes (pre-existing allauth test issue unrelated)

**Acceptance Criteria:**
- All three processes start without errors
- Web process serves HTTP requests
- Worker process executes tasks
- Beat process loads schedules from database
- Schedules can be managed via Django Admin
- Existing tests pass

---

## Execution Order

Recommended implementation sequence:

1. **Task Group 1: Package Installation & Django Configuration**
   - Foundation for all other changes
   - Low risk, easily reversible

2. **Task Group 2: Database Migrations & Schedule Seeding**
   - Creates database tables and seeds data
   - Can coexist with existing code-based schedules

3. **Task Group 3: ProdServer Configuration**
   - Adds new configuration without affecting current deployment
   - Can be tested independently

4. **Task Group 4: Procfile & Celery Configuration Updates**
   - The "switch-over" step
   - Only do after Groups 1-3 are verified working

5. **Task Group 5: Local Testing & Verification**
   - Comprehensive testing before deployment
   - Catch issues before they reach production

---

## Rollback Plan

If issues occur after deployment:

1. **Revert Procfile** to use direct gunicorn/celery commands
2. **Restore beat_schedule** in celery.py if schedules fail
3. Database migrations do NOT need to be reverted (tables can remain)
4. INSTALLED_APPS changes are safe to leave in place

---

## Notes

- The django-celery-beat tables and code-based schedules can coexist temporarily during migration
- Beat schedules in the database take precedence when using DatabaseScheduler
- Monitor task execution closely after deployment to ensure schedules fire correctly
- Consider deploying during low-traffic period to allow for monitoring
