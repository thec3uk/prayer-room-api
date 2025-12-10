import json

from django.db import migrations


def create_schedules(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Moderator digest - hourly at minute 0
    hourly_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="*",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )

    PeriodicTask.objects.update_or_create(
        name="moderator-digest-hourly",
        defaults={
            "task": "prayer_room_api.tasks.send_moderator_digest",
            "crontab": hourly_schedule,
            "enabled": True,
        },
    )

    # User digest daily - 8am every day
    daily_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="8",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )

    PeriodicTask.objects.update_or_create(
        name="user-digest-daily",
        defaults={
            "task": "prayer_room_api.tasks.send_user_digest",
            "crontab": daily_schedule,
            "args": json.dumps(["daily"]),
            "enabled": True,
        },
    )

    # User digest weekly - Monday 8am
    weekly_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="8",
        day_of_week="1",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )

    PeriodicTask.objects.update_or_create(
        name="user-digest-weekly",
        defaults={
            "task": "prayer_room_api.tasks.send_user_digest",
            "crontab": weekly_schedule,
            "args": json.dumps(["weekly"]),
            "enabled": True,
        },
    )


def reverse_schedules(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name__in=[
            "moderator-digest-hourly",
            "user-digest-daily",
            "user-digest-weekly",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("prayer_room_api", "0015_seed_email_templates"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_schedules, reverse_schedules),
    ]
