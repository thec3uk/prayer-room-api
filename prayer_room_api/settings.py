"""
Django settings for prayer_room_api project.

Generated by 'django-admin startproject' using Django 5.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path

from cbs import BaseSettings, env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ROOT_URLCONF = 'prayer_room_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'prayer_room_api.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


DJANGO_WEBHOOK = dict(MODELS=["prayer_room_api.PrayerPraiseRequest", "prayer_room_api.Setting"])


class Settings(BaseSettings):

    # Allow production to override the secret key, but fall-back to something consistent.
    SECRET_KEY = env('django-insecure-y&^-#s$ee58d8&&xi_9kl1^38x)!0-1hgby+ofhdl23$8d6)$u')

    # DEBUG defaults to True, but can be overridden by env var `DJANGO_DEBUG`
    DEBUG = env.bool(True, prefix='DJANGO_')

    # Simple cases that don't need `self` can even use a lambda
    MEDIA_ROOT = env(lambda self: BASE_DIR / 'media')

    # Methods will be transparently invoked by the __getattr__ implementation
    def INSTALLED_APPS(self):
        return list(filter(None, [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            # Conditionally include an app
            'debug_toolbar' if self.DEBUG else None,
            'import_export',
            'rest_framework',
            'rest_framework.authtoken',
            "corsheaders",
            "django_webhook",
            'allauth',
            'allauth.account',
            'allauth.socialaccount',
            'prayer_room_api',
        ]))

    def MIDDLEWARE(self):
        return list(filter(None, [
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            "allauth.account.middleware.AccountMiddleware",
            'whitenoise.middleware.WhiteNoiseMiddleware' if not self.DEBUG else False,
            # Conditionally include a middleware
            'debug_toolbar.middleware.DebugToolbarMiddleware' if self.DEBUG else False,
        ]))

    # Parse the URL into a database config dict.
    DEFAULT_DATABASE = env.dburl('sqlite:///db.sqlite3')

    CORS_ALLOWED_ORIGINS = [
        "http://localhost:4000",
    ]

    ALLOWED_HOSTS = []

    def DATABASES(self):
        return {
            'default': self.DEFAULT_DATABASE,
        }


class ProdSettings(Settings):
    # Override
    DEBUG = False

    # Values that *must* be provided in the environment.
    STATIC_ROOT = env(env.Required)
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

    CORS_ALLOWED_ORIGINS = [
        "https://api.prayer.thec3.uk"
    ]

    ALLOWED_HOSTS = [
        "api.prayer.thec3.uk"
    ] + [f'172.17.0.{num}' for num in range(2,255)]

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# The `use` method will find the right sub-class of ``BaseSettings`` to use
# Based on the value of the `DJANGO_MODE` env var.
__getattr__, __dir__ = Settings.use()
