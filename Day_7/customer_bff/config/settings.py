"""
Django settings for Customer BFF.
The BFF owns NO core business state — no PostgreSQL DB required for business data.
It uses SQLite only for sessions/admin if needed.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'customer-bff-secret-key-change-in-prod')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# BFF uses SQLite for sessions only (no business state)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---- Downstream service URLs
RESTAURANT_SERVICE_URL = os.environ.get('RESTAURANT_SERVICE_URL', 'http://127.0.0.1:8001')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://127.0.0.1:8002')

# ---- Per-service timeouts (seconds)
RESTAURANT_SERVICE_TIMEOUT = int(os.environ.get('RESTAURANT_SERVICE_TIMEOUT', 5))
ORDER_SERVICE_TIMEOUT = int(os.environ.get('ORDER_SERVICE_TIMEOUT', 5))

# ---- Retry configuration
SERVICE_MAX_RETRIES = int(os.environ.get('SERVICE_MAX_RETRIES', 3))
SERVICE_RETRY_BACKOFF = float(os.environ.get('SERVICE_RETRY_BACKOFF', 0.5))
