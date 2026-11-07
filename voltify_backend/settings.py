"""
Django settings for voltify_backend project.

Proyecto Voltify ejecutado con Django 4.1.3.
"""

from pathlib import Path


# Define la carpeta principal del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent


# Clave interna utilizada por Django
import os

def cargar_env(ruta):
    if not ruta.is_file():
        raise RuntimeError("Falta el archivo .env de Voltify")

    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue

        clave, separador, valor = linea.partition("=")
        if separador and clave.strip() == "DJANGO_SECRET_KEY":
            os.environ.setdefault(clave.strip(), valor.strip())

cargar_env(BASE_DIR / ".env")
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]


# Mantiene visibles los errores durante el desarrollo
DEBUG = True


# Define los hosts permitidos para ejecutar el proyecto
ALLOWED_HOSTS = []


# Aplicaciones instaladas en Django
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'consumos',
]


# Componentes que procesan las solicitudes y respuestas
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'consumos.middleware_login.LoginRateLimitMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# Archivo principal de rutas
ROOT_URLCONF = 'voltify_backend.urls'


# Configuración de templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            BASE_DIR / 'templates',
        ],

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


# Aplicación WSGI
WSGI_APPLICATION = 'voltify_backend.wsgi.application'


# Conexión con MariaDB/MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',

        'NAME': 'voltify_e3',

        'USER': 'root',

        'PASSWORD': '',

        'HOST': '127.0.0.1',

        'PORT': '3306',

        'OPTIONS': {
            'charset': 'utf8mb4',

            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# Validadores de contraseña de Django
LOGIN_SECURITY_DB = BASE_DIR / '.runtime' / 'login_security.sqlite3'
LOGIN_MAX_ATTEMPTS = 3
LOGIN_LOCKOUT_SECONDS = 30 * 60
LOGIN_ATTEMPT_WINDOW = 24 * 60 * 60
LOGIN_IP_MAX_ATTEMPTS = 30
LOGIN_IP_WINDOW = 10 * 60
LOGIN_IP_LOCKOUT_SECONDS = 5 * 60


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },

    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator'
        ),
    },

    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },

    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator'
        ),
    },
]


# Configuración regional
LANGUAGE_CODE = 'es-cl'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True


# Archivos estáticos
STATIC_URL = 'static/'


# Correos visibles en consola durante desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Las sesiones se almacenan en la base de datos
SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# Duración máxima de la sesión: 1 hora
SESSION_COOKIE_AGE = 3600


# La sesión expira al cerrar completamente el navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# Impide que JavaScript acceda a la cookie de sesión
SESSION_COOKIE_HTTPONLY = True


# Limita el envío de la cookie en solicitudes externas
SESSION_COOKIE_SAMESITE = 'Lax'


# False mientras Voltify se ejecute localmente mediante HTTP
SESSION_COOKIE_SECURE = False


# Protección de la cookie CSRF
CSRF_COOKIE_HTTPONLY = True

CSRF_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = False
