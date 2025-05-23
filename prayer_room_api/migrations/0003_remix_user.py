# Generated by Django 5.1.5 on 2025-01-31 09:31

from django.db import migrations

def create_user(apps, schema_editor):
    User = apps.get_model('auth.User')
    Token = apps.get_model('authtoken.Token')

    user = User.objects.create_user(
        'remix_app',
        'prayer@thec3.uk'
    )


def remove_user(apps, schema_editor):
    User = apps.get_model('auth.User')
    User.objects.filter(username='remix_app').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('prayer_room_api', '0002_alter_prayerpraiserequest_created_at'),
        ("authtoken", "0004_alter_tokenproxy_options"),
    ]

    operations = [
        migrations.RunPython(create_user, remove_user)
    ]
