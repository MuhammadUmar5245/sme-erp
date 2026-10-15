"""Settings shared by every environment. Values come from environment variables / .env."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-development-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=["https://localhost"])

# Company profile (case company) - used in templates, documents and seed data.
COMPANY = {
    "name": "Al Wadi Trading & Distribution LLC",
    "short_name": "Al Wadi Trading",
    "city": "Muscat",
    "country": "Sultanate of Oman",
    "currency": "OMR",
    "vat_number": "OM1100123456",
    "address": "Way 3503, Al Khuwair, Muscat, Sultanate of Oman",
    "phone": "+968 2448 1200",
}
CURRENCY = "OMR"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third party
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "drf_spectacular",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "axes",
    # SME-ERP modules
    "core",
    "accounts",
    "hr",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "accounts.middleware.CurrentRequestMiddleware",
    "accounts.middleware.TwoFactorEnforcementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Must be last: login lockout after repeated failures.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.erp",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="sme_erp"),
        "USER": env("POSTGRES_USER", default="sme_erp"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": True,
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# django-axes: lock an account for 30 minutes after 5 failed logins.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5  # hours
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_FORM_FIELD = "username"
AXES_LOCKOUT_TEMPLATE = "accounts/locked_out.html"
AXES_CLIENT_IP_CALLABLE = "accounts.middleware.get_client_ip"
AXES_VERBOSE = False
# Lockout is per account (not per IP) so one person's typos cannot lock out a whole office behind NAT.
SILENCED_SYSTEM_CHECKS = ["axes.W006"]

# django-otp (TOTP). Issuer shown in authenticator apps.
OTP_TOTP_ISSUER = "SME-ERP Al Wadi"

# Apps whose model changes are written to the audit log.
AUDIT_LOG_APPS = [
    "accounts",
    "hr",
    "inventory",
    "purchasing",
    "sales",
    "crm",
    "finance",
    "integrations",
    "feasibility",
    "auth",
]
# Field-level encryption key for sensitive data at rest (Fernet, see .env.example).
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = env("TIME_ZONE", default="Asia/Muscat")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Sessions: 30-minute idle timeout (expiry is pushed forward on every request).
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["core.permissions.ModelPermissions"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COERCE_DECIMAL_TO_STRING": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SME-ERP API",
    "DESCRIPTION": "RESTful service layer of the SME-ERP (Al Wadi Trading & Distribution LLC). "
    "Base path /api/v1/. Reporting endpoints under /api/v1/reports/ feed Power BI.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}
