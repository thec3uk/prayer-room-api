web: gunicorn prayer_room_api.wsgi:application
worker: celery -A prayer_room_api worker -l INFO

release: sudo ls -la /root/.local/bin/poetry && /root/.local/bin/poetry run django-admin migrate --noinput
