import os
from pathlib import Path
from dotenv import load_dotenv
from corsheaders.defaults import default_headers


load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'django-insecure-^)6p6qfzg&2^!ej3+f!$&fo)qh^k^^nan*g6dlf)ca^*yx_nh6'
SECRET_KEY = os.environ.get("SECRET_KEY", "default-dev-secret-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Application definition

INSTALLED_APPS = [
    #django apps
    'django.contrib.admin',
    'django.contrib.auth',
    # my users app
    'users',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'django_bootstrap5',
    'django_htmx',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    # my apps
    'recognition',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # must be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-csrftoken",
]

# Cookie settings — SameSite=None (no attribute) allows cross-port cookies over HTTP in dev.
# When HTTPS is set up, switch to SESSION_COOKIE_SAMESITE = 'None' + SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = None   # Python None = omit the SameSite attribute entirely
CSRF_COOKIE_SAMESITE = None
SESSION_COOKIE_SECURE = False    # set True when behind HTTPS
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False     # frontend JS needs to read the csrftoken cookie

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # keep for admin/browsable API
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}

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

DATABASES = {
"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("POSTGRES_DB"),
    "USER": os.getenv("POSTGRES_USER"),
    "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
    "HOST": os.getenv("DB_HOST"),
    "PORT": os.getenv("DB_PORT"),
    }
}
# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases




# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

# settings.py

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

LOGIN_URL = "/users/login/"
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

MEDIA_ROOT.mkdir(exist_ok=True)
STATIC_ROOT.mkdir(exist_ok=True)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ===== FACE RECOGNITION CONFIGURATION =====
# Paths for face encodings and ID cards
FACE_RECOGNITION_DIR = os.path.join(BASE_DIR, 'recognition', 'uploads', 'faces')
ID_CARD_DIR = os.path.join(BASE_DIR, 'recognition', 'uploads', 'faces', 'cards')

# Face detection and matching parameters
FACE_SCALE_FACTOR = float(os.getenv("SCALE", "0.25"))  # Scale down frames for faster processing
FACE_TOLERANCE = float(os.getenv("TOLERANCE", "0.55"))  # Threshold for face matching (lower = stricter)
FACE_TARGET = float(os.getenv("TOLERANCE", "0.55"))  # Target distance for face matching
TARGET_FPS = 30  # Target frames per second for recognition

# Frame processing optimization
PROCESS_EVERY_N_FRAMES = int(os.getenv("PROCESS_EVERY_N_FRAMES", "3"))  # Process every 3rd frame (skip 2 out of 3)
CARD_DISPLAY_FRAMES = int(os.getenv("CARD_DISPLAY_FRAMES", "10"))  # Frames to display ID card
MIN_FACE_SIZE = int(os.getenv("MIN_FACE_SIZE", "100"))  # Minimum face size in pixels to process

# Caching configuration
ENCODING_CACHE_KEY = os.getenv("ENCODING_CACHE_KEY")
ENCODING_CACHE_TTL = int(os.getenv("ENCODING_CACHE_TTL", "600"))  # 10 minutes - cache expires after this time