"""
Django settings for the foodhub project.

Every value that differs between development and production (secrets, hosts,
database, email) is read from the environment instead of being hardcoded, so
the exact same codebase runs safely in both places. See `.env.example` for
every variable this file understands.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a local .env file if one exists (development only —
# in production these come from real environment variables set by the host).
load_dotenv(BASE_DIR / '.env', override=True)


def env_bool(name, default=False):
    """Read an environment variable as a boolean ('True'/'1'/'yes' -> True)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    """Read a comma-separated environment variable into a list of strings."""
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
# The fallback below only exists so the project still runs out-of-the-box in
# local development. Production MUST set a real SECRET_KEY environment
# variable — see .env.example for how to generate one.
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-dev-only-key-do-not-use-in-production-)xvek6b_7()j*6',
)

# Default to DEBUG=False so a forgotten environment variable fails safe.
# Development sets DEBUG=True explicitly via .env.
DEBUG = env_bool('DEBUG', default=False)

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', default='localhost,127.0.0.1')

# Needed when the site sits behind a proxy/load balancer that terminates TLS
# (Render, Railway, Fly.io, Heroku-style platforms all do this).
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    # Hardening that only makes sense once the site is served over HTTPS.
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 1 week; raise once confident everything works over HTTPS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'store',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves static files efficiently, even without DEBUG
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'foodhub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart_context',
                'store.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'foodhub.wsgi.application'


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Reads DATABASE_URL when set (e.g. postgres://user:pass@host:5432/db) and
# falls back to local SQLite when it isn't — so `python manage.py runserver`
# still works with zero configuration in development.

# Reads DATABASE_URL when it's actually set to a non-empty value (e.g.
# postgres://user:pass@host:5432/db) and falls back to local SQLite
# otherwise — so `python manage.py runserver` works with zero configuration
# in development, whether DATABASE_URL is unset OR present-but-blank (as it
# is in .env.example before you configure Postgres).
#
# NOTE: dj_database_url.config()'s `default=` argument only kicks in when
# the environment variable is completely absent — if DATABASE_URL exists
# but is an empty string (like `DATABASE_URL=` in .env), it's treated as
# "set" and produces an empty, engine-less config instead of falling back.
# Checking the value explicitly avoids that trap.
_database_url = os.environ.get('DATABASE_URL', '').strip()

if _database_url:
    DATABASES = {'default': dj_database_url.parse(_database_url, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
CURRENCY_SYMBOL = 'GH₵'
TIME_ZONE = 'Africa/Accra'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # Hashed + compressed filenames in production for cache-busting and
        # smaller payloads; a plain backend in development so runserver
        # doesn't require running collectstatic on every change.
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if not DEBUG else
            'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Auth redirects
# ---------------------------------------------------------------------------

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'store:home'
LOGOUT_REDIRECT_URL = 'store:home'


# ---------------------------------------------------------------------------
# Messages framework — map Django's message levels to Bootstrap alert classes
# ---------------------------------------------------------------------------

from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {
    message_constants.DEBUG: 'debug',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# NOTE: the previous version of this file set a `MAILERS` dict, which is not
# a setting Django reads — it silently did nothing and email would have
# fallen back to Django's default (SMTP with no host configured, which
# raises an error the first time anything tries to send mail). Real settings
# below, driven by environment variables so nothing sensitive is hardcoded.

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'FoodHub Ghana <no-reply@foodhub.gh>')


# ---------------------------------------------------------------------------
# Payments (Paystack — supports Ghanaian Mobile Money and card charges)
# ---------------------------------------------------------------------------

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', '')


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Everything goes to the console. Platforms like Render/Railway/Fly capture
# stdout/stderr automatically, so this is all that's needed to see logs.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
