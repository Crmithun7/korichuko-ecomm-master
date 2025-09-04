# korichuko/settings.py
from pathlib import Path
import os
import dj_database_url

# Optional: load .env locally
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

# -------------------- helpers --------------------
def env_bool(key: str, default: str = "0") -> bool:
    return os.getenv(key, default).strip().lower() in {"1", "true", "yes", "on"}

def env_csv(key: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(key, default).split(",") if item.strip()]

def normalize_origins(items: list[str], default_scheme: str) -> list[str]:
    """Ensure each origin has http(s) scheme to satisfy Django>=4 rule."""
    out = []
    for it in items:
        if it.startswith(("http://", "https://")):
            out.append(it)
        else:
            out.append(f"{default_scheme}://{it}")
    return out

# -------------------- core security / env --------------------
DEBUG = env_bool("DEBUG", "1")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

ALLOWED_HOSTS = env_csv("ALLOWED_HOSTS", "127.0.0.1,localhost")

DEFAULT_SCHEME = "http" if DEBUG else "https"
CSRF_TRUSTED_ORIGINS = normalize_origins(
    env_csv("CSRF_TRUSTED_ORIGINS", ""), default_scheme=DEFAULT_SCHEME
)

# -------------------- installed apps --------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",

    # Put BEFORE staticfiles so runserver uses WhiteNoise path
    "whitenoise.runserver_nostatic",

    "django.contrib.staticfiles",

    # your apps
    "store",
    "adminpanel",
]

# -------------------- middleware --------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise right after SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "korichuko.urls"

# -------------------- templates --------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # keep if present in your codebase
                "store.context_processors.cart_context",
            ],
        },
    },
]

WSGI_APPLICATION = "korichuko.wsgi.application"

# -------------------- database --------------------
# Prefer DATABASE_URL (Railway sets it). Example:
# mysql://user:pass@host:port/dbname?charset=utf8mb4
_db_url = os.getenv("DATABASE_URL", "").strip()
if _db_url:
    ssl_require = env_bool("DB_SSL_REQUIRE", "0")
    DATABASES = {
        "default": dj_database_url.parse(
            _db_url,
            conn_max_age=600,
            ssl_require=ssl_require,
        )
    }
else:
    # Local dev fallback (MySQL) — works with mysqlclient OR PyMySQL shim
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("MYSQL_DATABASE", "korichuko_db"),
            "USER": os.getenv("MYSQL_USER", "root"),
            "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
            "HOST": os.getenv("MYSQL_HOST", "localhost"),
            "PORT": os.getenv("MYSQL_PORT", "3306"),
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

# -------------------- i18n --------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# -------------------- static & media --------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "store" / "static",
    BASE_DIR / "adminpanel" / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default local media (used when CLOUDINARY_URL is missing)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise for static (compressed + hashed)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# -------------------- Cloudinary media (auto switch) --------------------
# If CLOUDINARY_URL is set, use Cloudinary for MEDIA; otherwise local filesystem.
USE_CLOUD_MEDIA = bool(os.getenv("CLOUDINARY_URL"))
if USE_CLOUD_MEDIA:
    INSTALLED_APPS += ["cloudinary", "cloudinary_storage"]
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    CLOUDINARY_STORAGE = {
        "PREFIX": "media",
        "DEFAULTS": {"use_filename": True, "unique_filename": False, "overwrite": True},
    }

# -------------------- auth redirects --------------------
LOGIN_URL = "store:login"
LOGIN_REDIRECT_URL = "store:home"

# -------------------- proxy / https security --------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# -------------------- third-party keys (env) --------------------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# -------------------- defaults --------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
