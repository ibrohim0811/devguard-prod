import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent 


SECRET_KEY = os.getenv('SECRET_KEY')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False 

ALLOWED_HOSTS = [
    'api.devguard.uz',
    'ibrohim.api.devguard.uz',
    '.devguard.uz',
    'localhost',
    '127.0.0.1',
    '84.235.169.116',
]

# Nginx reverse proxy orqasida ishlayotgani uchun
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CSRF uchun ishonchli manbalar
CSRF_TRUSTED_ORIGINS = [
    'https://api.devguard.uz',
    'http://api.devguard.uz',
    'https://ibrohim.api.devguard.uz',
    'http://ibrohim.api.devguard.uz',
]



INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'core',
    'users',
    'channels',

    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'django_celery_results',
]

ASGI_APPLICATION = 'devshield.asgi.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'devshield.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'devshield.wsgi.application'



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("NAME"),          
        'USER': os.getenv("POSTGRES_USER"),           
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("HOST"),          
        'PORT': os.getenv("PORT"),               
    }
}



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




LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


AUTH_USER_MODEL = 'users.Users'

STATIC_ROOT = Path(__file__).resolve().parent.parent / 'staticfiles'
STATIC_URL = '/static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://devshield.uz,https://www.devshield.uz"
    ).split(",") if origin.strip()
]

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')




REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv('REDIS_LOCATION'), 
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

SIMPLE_JWT = {
    
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),    
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),       

    
    'ROTATE_REFRESH_TOKENS': True,                     
    'BLACKLIST_AFTER_ROTATION': True,                  

    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    
    'SIGNING_KEY': os.getenv('SECRET_KEY'), 
    'ALGORITHM': 'HS256',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Devshield',
    'DESCRIPTION': 'Devshield project',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # OTHER SETTINGS
}

# settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                {
                    "address": "redis://redis:6379/0",
                    "health_check_interval": 15, # Har 15 soniyada Redis bilan ulanishni tekshiradi
                    "socket_connect_timeout": 5, # Ulanish kutish vaqti
                    "socket_keepalive": True,    # TCP Keepalive yoqish
                },
            ],
            "capacity": 1500,
            "expiry": 60,
        },
    },
}

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = "DevGuard <devguard.uz@gmail.com>"

