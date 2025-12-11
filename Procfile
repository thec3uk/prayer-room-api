web: DJANGO_MODE=prod python manage.py prodserver web
worker: DJANGO_MODE=prod celery -A prayer_room_api worker -l INFO
beat: DJANGO_MODE=prod celery -A prayer_room_api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

release: ./manage.py migrate --noinput
