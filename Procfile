web: gunicorn prayer_room_api.wsgi:application
worker: celery -A prayer_room_api worker -l INFO

release: ./virtualenvs/bin/django-admin migrate --noinput
