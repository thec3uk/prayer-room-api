web: gunicorn prayer_room_api.wsgi:application
worker: celery -A prayer_room_api worker -l INFO

release: eval $(poetry env activate) && ./manage.py migrate --noinput
