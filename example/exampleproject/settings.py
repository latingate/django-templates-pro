"""Settings for the django-templates-pro demo project. Development only."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "demo-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "templates_pro",
    "demo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "exampleproject.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "exampleproject.wsgi.application"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/admin/login/"

# The preview iframe loads same-origin content.
X_FRAME_OPTIONS = "SAMEORIGIN"

TEMPLATES_PRO = {
    "DEFAULT_CURRENCY": "GBP",
    "DEFAULT_LOCALE": "en_GB",
    "OUTPUT_FORMATS": ["html", "pdf", "docx", "txt"],
    "DEFAULT_OUTPUT_FORMATS": ["html", "pdf", "docx"],
    "DEFAULT_THEME": "classic",
    # A project-specific theme next to the built-in ones:
    "THEMES": {"northwind": {"label": "Northwind brand", "css": "demo/northwind-theme.css"}},
    # Constants computed in code, merged with the ones edited in the admin:
    "CONSTANTS_PROVIDER": "demo.constants.provide",
    "EDITOR": {"preset": "full", "skin": "default", "height": 480},
}
