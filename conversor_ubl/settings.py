# conversor_ubl/settings.py - VERSIÓN CORREGIDA CON LOGGING UTF-8
import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-gxw58ed+dzzs-+z#ih+jz89hn!9o=s+9we$vqsbwi*k!u0*&x#')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    
    # Local apps
    'core',
    'ubl_converter',
    'sunat_integration',
    'digital_signature',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conversor_ubl.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'conversor_ubl.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='conversor_ubl_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
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
LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Crear directorios necesarios si no existen
os.makedirs(MEDIA_ROOT / 'xml_files', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'zip_files', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'cdr_files', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'certificates', exist_ok=True)
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ✅ LOGGING CORREGIDO PARA WINDOWS CON UTF-8
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',  # ✅ AGREGADO: Forzar UTF-8
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'ubl_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'ubl_converter.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',  # ✅ AGREGADO: Forzar UTF-8
        },
        'sunat_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'sunat_integration.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',  # ✅ AGREGADO: Forzar UTF-8
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],  # ✅ SOLO CONSOLE PARA EVITAR ERRORES
            'level': 'INFO',
            'propagate': True,
        },
        'ubl_converter': {
            'handlers': ['ubl_file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'sunat_integration': {
            'handlers': ['sunat_file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'digital_signature': {
            'handlers': ['console'],  # ✅ SOLO CONSOLE
            'level': 'DEBUG',
            'propagate': True,
        },
        'api': {
            'handlers': ['console'],  # ✅ SOLO CONSOLE
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# SUNAT Configuration
SUNAT_CONFIG = {
    'BETA_URL': 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl',
    'PRODUCTION_URL': 'https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl',
    'USE_BETA': config('SUNAT_USE_BETA', default=True, cast=bool),
    'RUC': config('SUNAT_RUC', default='20000000001'),
    'USERNAME': config('SUNAT_USERNAME', default='20000000001MODDATOS'),
    'PASSWORD': config('SUNAT_PASSWORD', default='MODDATOS'),
    'CERTIFICATE_PATH': config('SUNAT_CERTIFICATE_PATH', default=str(MEDIA_ROOT / 'certificates' / 'certificate.pfx')),
    'CERTIFICATE_PASSWORD': config('SUNAT_CERTIFICATE_PASSWORD', default=''),
}

# UBL Configuration
UBL_CONFIG = {
    'VERSION': '2.1',
    'CUSTOMIZATION_ID': '2.0',
    'PROFILE_ID': 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06',
    'SCHEMA_LOCATION': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
    'NAMESPACES': {
        'xmlns': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
        'xmlns:cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'xmlns:cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'xmlns:ds': 'http://www.w3.org/2000/09/xmldsig#',
        'xmlns:ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
        'xmlns:sac': 'urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1',
        'xmlns:qdt': 'urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2',
        'xmlns:udt': 'urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2',
    }
}

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if DEBUG:
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]

# ✅ FORZAR UTF-8 EN TODO EL SISTEMA (WINDOWS)
import locale
import sys

# Configurar la codificación del sistema
if sys.platform.startswith('win'):
    # Para Windows, forzar UTF-8
    locale.setlocale(locale.LC_ALL, 'es_PE.UTF-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# File encoding para el sistema
FILE_CHARSET = 'utf-8'
DEFAULT_CHARSET = 'utf-8'

# Configuración de archivos de prueba
TEST_DATA_CONFIG = {
    'DEFAULT_COMPANY_RUC': '23022479065',
    'DEFAULT_CUSTOMER_DOC': '12345678',
    'DEFAULT_CURRENCY': 'PEN',
    'DEFAULT_IGV_RATE': 18.00,
    'DEFAULT_PERCEPTION_RATE': 2.00,
}

# Configuración de validaciones
VALIDATION_CONFIG = {
    'ENABLE_STRICT_VALIDATION': config('ENABLE_STRICT_VALIDATION', default=False, cast=bool),
    'VALIDATE_RUC_CHECKSUM': config('VALIDATE_RUC_CHECKSUM', default=True, cast=bool),
    'VALIDATE_CERTIFICATE_EXPIRY': config('VALIDATE_CERTIFICATE_EXPIRY', default=True, cast=bool),
}

# Configuración de timeouts
TIMEOUT_CONFIG = {
    'SUNAT_REQUEST_TIMEOUT': config('SUNAT_REQUEST_TIMEOUT', default=30, cast=int),
    'XML_PROCESSING_TIMEOUT': config('XML_PROCESSING_TIMEOUT', default=10, cast=int),
    'SIGNATURE_TIMEOUT': config('SIGNATURE_TIMEOUT', default=15, cast=int),
}