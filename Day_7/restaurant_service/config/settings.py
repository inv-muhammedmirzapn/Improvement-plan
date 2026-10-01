"""
Django settings for Restaurant Service.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'restaurant-service-secret-key-change-in-prod')
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
    'restaurant',
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

# --- Independent PostgreSQL database for Restaurant Service ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'restaurant_service_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '12345678'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 5,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---- Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/1')
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 100
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_BEAT_SCHEDULE = {
    'restaurant-publish-outbox': {
        'task': 'restaurant.tasks.publish_outbox_events',
        'schedule': 5.0,
    },
    'restaurant-reconcile-capacity': {
        'task': 'restaurant.tasks.reconcile_capacity',
        'schedule': 60.0,
    },
    'restaurant-retry-stale-outbox': {
        'task': 'restaurant.tasks.retry_stale_outbox',
        'schedule': 30.0,
    },
}

# ---- Outbox Configuration
OUTBOX_BATCH_SIZE = int(os.environ.get('OUTBOX_BATCH_SIZE', 50))
OUTBOX_MAX_ATTEMPTS = int(os.environ.get('OUTBOX_MAX_ATTEMPTS', 10))
OUTBOX_LEASE_SECONDS = int(os.environ.get('OUTBOX_LEASE_SECONDS', 60))
OUTBOX_STALE_SECONDS = int(os.environ.get('OUTBOX_STALE_SECONDS', 300))

# ---- Service URLs (for internal calls)
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://127.0.0.1:8002')
ORDER_SERVICE_TIMEOUT = int(os.environ.get('ORDER_SERVICE_TIMEOUT', 5))

# ---- Restaurant Business Configuration
MAX_ACTIVE_ORDERS = int(os.environ.get('MAX_ACTIVE_ORDERS', 20))
STUCK_ORDER_THRESHOLD_MINUTES = int(os.environ.get('STUCK_ORDER_THRESHOLD_MINUTES', 30))
