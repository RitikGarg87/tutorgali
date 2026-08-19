"""
Django settings for tutorgali project.
Reads all secrets from .env via python-decouple.
"""

from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY')
DEBUG      = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# ── Installed Apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.syndication',
    'users',
    'blog',
]

AUTHENTICATION_BACKENDS = [
    'users.backends.EmailOrMobileBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tutorgali.urls'

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
                'users.context_processors.seo_defaults',
            ],
        },
    },
]

WSGI_APPLICATION = 'tutorgali.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
# Reads DATABASE_URL from the environment (e.g. Neon PostgreSQL:
# postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require). Falls back
# to local SQLite when DATABASE_URL is unset (dev). conn_max_age keeps
# connections alive between requests; ssl_require forces TLS in production
# (Neon requires it — the sslmode in the URL also covers this).
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
        ssl_require=not DEBUG,
    )
}

# ── Password Validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

# ── Static & Media Files ──────────────────────────────────────────────────────
STATIC_URL       = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT      = BASE_DIR / 'staticfiles'   # used by collectstatic

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Whitenoise serves static files directly from gunicorn with gzip/brotli
# compression + long-lived cache-control headers — there's no CDN or
# reverse-proxy static layer in front of this deploy today.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ── Default PK ───────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Auth Redirects ────────────────────────────────────────────────────────────
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL           = '/login/'

# ── Email ─────────────────────────────────────────────────────────────────────
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = f'TutorGali <{EMAIL_HOST_USER}>'

# ── Session ───────────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE        = 1209600   # 2 weeks
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ── Payment — Razorpay ────────────────────────────────────────────────────────
RAZORPAY_KEY_ID     = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')
# Separate secret generated when configuring the webhook URL in the
# Razorpay dashboard (Settings > Webhooks) — NOT the same as the API key
# secret above. Used to verify /subscriptions/webhook/ requests actually
# came from Razorpay. Leave unset in dev; the webhook view returns 500
# until it's configured, and does not require a webhook to work locally.
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default='')

# ── OTP — Fast2SMS ────────────────────────────────────────────────────────────
FAST2SMS_API_KEY = config('FAST2SMS_API_KEY', default='')

# ── Google Maps ───────────────────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# ── SEO ───────────────────────────────────────────────────────────────────────
# Canonical production domain — used to build absolute URLs in sitemap.xml,
# robots.txt, canonical tags, and Open Graph tags. Override via .env once the
# domain is live (e.g. SITE_DOMAIN=tutorgali.in).
SITE_DOMAIN = config('SITE_DOMAIN', default='tutorgali.in')
SITE_URL = f'https://{SITE_DOMAIN}'

# ── Production Security Headers ───────────────────────────────────────────────
# These activate automatically when DEBUG=False. The site is now live on
# HTTPS (tutorgali.in), so the SSL/HSTS-dependent settings below are enabled.
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER   = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS             = 'DENY'

    # Redirect all HTTP requests to HTTPS.
    SECURE_SSL_REDIRECT         = True
    # Only send session/CSRF cookies over HTTPS.
    SESSION_COOKIE_SECURE       = True
    CSRF_COOKIE_SECURE          = True
    # HSTS: tells browsers to only ever connect via HTTPS for the next year,
    # including subdomains. Start with a short SECURE_HSTS_SECONDS value in
    # a test deploy if unsure, then raise it — once submitted to browsers'
    # HSTS preload lists this is hard to reverse.
    SECURE_HSTS_SECONDS         = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD         = True

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'tutorgali.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'users': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
}
