web: gunicorn prayer_room_api.wsgi:application
worker: celery -A prayer_room_api worker -l INFO

release: /root/.local/bin/poetry run ./manage.py migrate --noinput
