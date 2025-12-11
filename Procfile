web: python manage.py prodserver web
worker: celery -A prayer_room_api worker -l INFO
beat: celery -A prayer_room_api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

release: ./manage.py migrate --noinput
