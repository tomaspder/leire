"""Configuración de Django. Todos los valores sensibles se leen de variables de entorno."""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Las variables ya definidas en el entorno tienen prioridad sobre el archivo .env.
load_dotenv(BASE_DIR / ".env", override=False)


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Falta la variable de entorno {name}.")
    return value


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


DEBUG = env("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    # core va primero: sus comandos (migrate, flush) incluyen salvaguardas.
    "core",
    "demografia",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Toda vista requiere sesión salvo las marcadas explícitamente (login).
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.PrivateResponseMiddleware",
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
                "core.context_processors.app_mode",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos -----------------------------------------------------------
# "demo": base local con datos ficticios. "real": base universitaria (pendiente).
APP_DB_MODE = env("APP_DB_MODE", "demo")
if APP_DB_MODE not in ("demo", "real"):
    raise ImproperlyConfigured("APP_DB_MODE debe ser 'demo' o 'real'.")

_prefix = "DEMO_DB_" if APP_DB_MODE == "demo" else "REAL_DB_"
_db_options = {}
if APP_DB_MODE == "real":
    _db_options["sslmode"] = env("REAL_DB_SSLMODE", "prefer")
    if env("REAL_DB_SEARCH_PATH"):
        _db_options["options"] = f"-c search_path={env('REAL_DB_SEARCH_PATH')}"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env(f"{_prefix}NAME", required=True),
        "USER": env(f"{_prefix}USER", required=True),
        "PASSWORD": env(f"{_prefix}PASSWORD", ""),
        "HOST": env(f"{_prefix}HOST", "localhost"),
        "PORT": env(f"{_prefix}PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": _db_options,
    }
}

DATABASE_ROUTERS = ["core.routers.SafeMigrationRouter"]

# Apps cuyas tablas solo existen en la base de demostración.
DEMO_ONLY_APPS = ["demografia"]
# Apps de datos cuyos permisos se asignan a los grupos "Consulta" y "Edición".
DATA_APPS = ["demografia"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Autenticación -----------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- Seguridad HTTP (activa fuera de DEBUG) -----------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT", "1") == "1"
    SECURE_HSTS_SECONDS = int(env("DJANGO_SECURE_HSTS_SECONDS", "0"))
    if env("DJANGO_BEHIND_PROXY", "0") == "1":
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Internacionalización -----------------------------------------------------
LANGUAGE_CODE = "es"
LANGUAGES = [("es", "Español")]
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

# --- Estáticos (sin CDN: el servidor puede no tener acceso a internet) -------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # El manifiesto solo existe tras collectstatic; en desarrollo y pruebas se usa el almacenamiento simple.
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG or "test" in sys.argv[1:2]
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

PAGINATE_BY = 25

# --- Logs: sin datos de registros ni parámetros SQL ---------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
