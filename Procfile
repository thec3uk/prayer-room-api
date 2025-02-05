web: gunicorn prayer_room_api.wsgi:application
worker: celery -A prayer_room_api worker -l INFO

release: django-admin migrate --noinput
