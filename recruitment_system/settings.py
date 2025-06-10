import os
from pathlib import Path
from dotenv import load_dotenv
from decouple import config
from cryptography.fernet import Fernet

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default="django-insecure-j4dod1kg#=4qqgb*djk@ysd@xk(wc-l_9*$*qtems66^!unn4j")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Custom User Model
AUTH_USER_MODEL = 'azure_auth.AppUser'

# Frontend URLs for Django redirects
FRONTEND_SUCCESS_URL = config('FRONTEND_SUCCESS_URL', default='http://localhost:3000/auth/callback')
FRONTEND_ERROR_URL = config('FRONTEND_ERROR_URL', default='http://localhost:3000/login')

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    
    # Local apps
    'azure_auth',
    'permissions',
    'mpr',
    'email_service',
    'users',
    'candidate',
    'interview',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'permissions.middleware.PermissionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "recruitment_system.urls"

# =============================================================================
# AZURE AD CONFIGURATION
# =============================================================================

AZURE_AD_CLIENT_ID = config('AZURE_AD_CLIENT_ID', default=None)
AZURE_AD_CLIENT_SECRET = config('AZURE_AD_CLIENT_SECRET', default=None)
AZURE_AD_TENANT_ID = config('AZURE_AD_TENANT_ID', default=None)
AZURE_AD_REDIRECT_URI = config('AZURE_AD_REDIRECT_URI', default='http://localhost:8000/auth/callback/')

# Microsoft Graph API
GRAPH_API_ENDPOINT = config('GRAPH_API_ENDPOINT', default='https://graph.microsoft.com/v1.0')

# Verify Azure AD configuration
if not all([AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, AZURE_AD_TENANT_ID]):
    print("⚠️  WARNING: Azure AD configuration incomplete!")
    print(f"CLIENT_ID: {'✓' if AZURE_AD_CLIENT_ID else '✗'}")
    print(f"CLIENT_SECRET: {'✓' if AZURE_AD_CLIENT_SECRET else '✗'}")
    print(f"TENANT_ID: {'✓' if AZURE_AD_TENANT_ID else '✗'}")
    print("Please check your .env file and ensure all Azure AD variables are set.")

# =============================================================================
# EMAIL SERVICE CONFIGURATION
# =============================================================================

# Email Service Encryption Key
EMAIL_SERVICE_ENCRYPTION_KEY = config('EMAIL_SERVICE_ENCRYPTION_KEY', default=None)

if not EMAIL_SERVICE_ENCRYPTION_KEY:
    print("⚠️  WARNING: EMAIL_SERVICE_ENCRYPTION_KEY not found!")
    print("Generating a temporary key for this session...")
    print("Please generate a permanent key and add it to your .env file:")
    print("python -c \"from cryptography.fernet import Fernet; print('EMAIL_SERVICE_ENCRYPTION_KEY=' + Fernet.generate_key().decode())\"")
    EMAIL_SERVICE_ENCRYPTION_KEY = Fernet.generate_key()
else:
    # Ensure it's bytes for Fernet
    if isinstance(EMAIL_SERVICE_ENCRYPTION_KEY, str):
        EMAIL_SERVICE_ENCRYPTION_KEY = EMAIL_SERVICE_ENCRYPTION_KEY.encode()

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS', 
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CORS_ALLOW_CREDENTIALS = True

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# =============================================================================
# REST FRAMEWORK CONFIGURATION
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'azure_auth.authentication.AzureTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# =============================================================================
# CELERY CONFIGURATION (Background Tasks)
# =============================================================================

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# =============================================================================
# TEMPLATES CONFIGURATION
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "recruitment_system.wsgi.application"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Default to SQLite for development, can be overridden with DATABASE_URL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Override with DATABASE_URL if provided (for production)
DATABASE_URL = config('DATABASE_URL', default=None)
if DATABASE_URL:
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

# Redis cache configuration
CACHE_URL = config('CACHE_URL', default='redis://localhost:6379/1')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': CACHE_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
} if 'redis://' in CACHE_URL else {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# =============================================================================
# EMAIL CONFIGURATION (Django Email Backend)
# =============================================================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@localhost')

# Admin email for error notifications
ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@localhost')),
]

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC FILES CONFIGURATION
# =============================================================================

STATIC_URL = config('STATIC_URL', default='/static/')
STATIC_ROOT = config('STATIC_ROOT', default=BASE_DIR / 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / 'static',
] if (BASE_DIR / 'static').exists() else []

# =============================================================================
# MEDIA FILES CONFIGURATION
# =============================================================================

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default=BASE_DIR / 'media')

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# Security headers
SECURE_BROWSER_XSS_FILTER = config('SECURE_BROWSER_XSS_FILTER', default=True, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = config('SECURE_CONTENT_TYPE_NOSNIFF', default=True, cast=bool)

# Session configuration
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=86400, cast=int)  # 24 hours
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = config('SESSION_COOKIE_HTTPONLY', default=True, cast=bool)

# CSRF configuration
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)

# Production security settings (only if not in DEBUG mode)
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
    SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOG_LEVEL = config('LOG_LEVEL', default='INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '[{asctime}] {levelname} {name} {module}:{lineno} - {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
            'level': 'DEBUG',
        },
        'file_general': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'general.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_email': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'email_service.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_auth': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'auth.log',
            'maxBytes': 5242880,  # 5MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
        'file_mpr': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'mpr.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_permissions': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'permissions.log',
            'maxBytes': 5242880,  # 5MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
        'file_celery': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'celery.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_django': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['require_debug_false'],
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
            'formatter': 'verbose',
        },
    },
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['console', 'file_general'],
    },
    'loggers': {
        # Azure Authentication Logging
        'azure_auth': {
            'handlers': ['console', 'file_auth'],
            'level': 'DEBUG',
            'propagate': False,
        },
        
        # Email Service Logging
        'email_service': {
            'handlers': ['console', 'file_email'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        
        # MPR System Logging
        'mpr': {
            'handlers': ['console', 'file_mpr'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        
        # Permissions System Logging
        'permissions': {
            'handlers': ['console', 'file_permissions'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        
        # User Permissions
        # 'users': {
        #     'handlers': ['file', 'console'],
        #     'level': LOG_LEVEL,
        #     'propagate': True,
        # },
        # Celery Task Logging
        'celery': {
            'handlers': ['console', 'file_celery'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['console', 'file_celery'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'celery.worker': {
            'handlers': ['console', 'file_celery'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        
        # Django Core Logging
        'django': {
            'handlers': ['console', 'file_django'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file_django', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file_django', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
        
        # Third-party Libraries
        'requests': {
            'handlers': ['console', 'file_general'],
            'level': 'WARNING',
            'propagate': False,
        },
        'urllib3': {
            'handlers': ['console', 'file_general'],
            'level': 'WARNING',
            'propagate': False,
        },
        'msal': {
            'handlers': ['console', 'file_auth'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        
        # Custom Application Loggers
        'recruitment_system': {
            'handlers': ['console', 'file_general'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'file_general'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'sync': {
            'handlers': ['console', 'file_email'],
            'level': 'DEBUG',
            'propagate': False,
        },
        
        # Performance and Monitoring
        'performance': {
            'handlers': ['console', 'file_general'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'monitoring': {
            'handlers': ['console', 'file_general'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        
        # Security Logging
        'security': {
            'handlers': ['console', 'file_auth', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'authentication': {
            'handlers': ['console', 'file_auth'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'authorization': {
            'handlers': ['console', 'file_permissions'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# =============================================================================
# DEVELOPMENT TOOLS
# =============================================================================

# Django Debug Toolbar (development only)
if DEBUG and config('ENABLE_DEBUG_TOOLBAR', default=False, cast=bool):
    try:
        import debug_toolbar
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
        
        # Debug toolbar configuration
        DEBUG_TOOLBAR_CONFIG = {
            'DISABLE_PANELS': [
                'debug_toolbar.panels.redirects.RedirectsPanel',
            ],
            'SHOW_TEMPLATE_CONTEXT': True,
        }
        
        # Ensure debug toolbar URLs are added
        ROOT_URLCONF_DEBUG = True
        
    except ImportError:
        print("⚠️  Debug toolbar is enabled but not installed. Run: pip install django-debug-toolbar")


# Django Extensions (development only)
if DEBUG and config('ENABLE_DJANGO_EXTENSIONS', default=False, cast=bool):
    try:
        import django_extensions
        INSTALLED_APPS += ['django_extensions']
    except ImportError:
        print("⚠️  Django extensions is enabled but not installed. Run: pip install django-extensions")

# =============================================================================
# DEFAULT AUTO FIELD
# =============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

# Enable performance logging
ENABLE_PERFORMANCE_LOGGING = config('ENABLE_PERFORMANCE_LOGGING', default=False, cast=bool)

# =============================================================================
# CUSTOM SETTINGS VALIDATION
# =============================================================================

def validate_settings():
    """Validate critical settings on startup"""
    errors = []
    warnings = []
    
    # Check Azure AD configuration
    if not all([AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, AZURE_AD_TENANT_ID]):
        warnings.append("Azure AD configuration incomplete")
    
    # Check email service encryption key
    if not EMAIL_SERVICE_ENCRYPTION_KEY or EMAIL_SERVICE_ENCRYPTION_KEY == Fernet.generate_key():
        errors.append("EMAIL_SERVICE_ENCRYPTION_KEY not properly configured")
    
    # Check production settings
    if not DEBUG:
        if SECRET_KEY.startswith('django-insecure'):
            errors.append("Using insecure SECRET_KEY in production")
        if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['*']:
            errors.append("ALLOWED_HOSTS not properly configured for production")
    
    # Log validation results
    if errors:
        import logging
        logger = logging.getLogger('recruitment_system')
        for error in errors:
            logger.error(f"❌ Configuration Error: {error}")
    
    if warnings:
        import logging
        logger = logging.getLogger('recruitment_system')
        for warning in warnings:
            logger.warning(f"⚠️  Configuration Warning: {warning}")

# Run validation on startup
try:
    validate_settings()
except Exception as e:
    print(f"Settings validation failed: {e}")

# =============================================================================
# FINAL CONFIGURATION SUMMARY
# =============================================================================

if DEBUG:
    print("🚀 Django Configuration Summary:")
    print(f"   Environment: {'Development' if DEBUG else 'Production'}")
    print(f"   Database: {DATABASES['default']['ENGINE'].split('.')[-1]}")
    print(f"   Cache: {'Redis' if 'redis' in CACHE_URL else 'Local Memory'}")
    print(f"   Azure AD: {'✓' if all([AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, AZURE_AD_TENANT_ID]) else '✗'}")
    print(f"   Email Service: {'✓' if EMAIL_SERVICE_ENCRYPTION_KEY else '✗'}")
    print(f"   Celery: {'✓' if 'redis://' in CELERY_BROKER_URL else 'File-based'}")
    print(f"   Logging: {len(LOGGING['loggers'])} loggers configured")