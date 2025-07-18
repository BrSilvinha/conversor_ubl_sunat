# conversor_ubl/settings.py - REEMPLAZAR COMPLETAMENTE
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

# ✅ MIDDLEWARE MEJORADO - Con supresor de warnings
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'conversor_ubl.middleware.SuppressUnwantedWarningsMiddleware',  # ✅ NUEVO - Suprimir warnings
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

# ✅ LOGGING COMPLETAMENTE MEJORADO - SIN ERRORES NI WARNINGS INNECESARIOS
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
        'minimal': {
            'format': '{asctime} {message}',
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
        'skip_suspicious_operations': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not any(
                pattern in record.getMessage() for pattern in [
                    'SuspiciousOperation',
                    'DisallowedHost',
                    'Invalid HTTP_HOST',
                ]
            )
        },
        'skip_unwanted_requests': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not any(
                pattern in record.getMessage() for pattern in [
                    '.well-known/',
                    'favicon.ico',
                    'robots.txt',
                    'apple-touch-icon',
                    'manifest.json',
                    'browserconfig.xml',
                    'Broken pipe',
                    'Connection reset by peer',
                ]
            )
        },
        'skip_sunat_auth_warnings': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not (
                '401' in record.getMessage() and 
                'SUNAT' in record.getMessage() and
                record.levelno <= 30  # WARNING level
            )
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'minimal',
            'filters': ['skip_unwanted_requests', 'skip_suspicious_operations'],
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
            'filters': ['skip_unwanted_requests'],
        },
        'sunat_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler', 
            'filename': BASE_DIR / 'logs' / 'sunat_integration.log',
            'formatter': 'verbose',
            'filters': ['skip_sunat_auth_warnings'],  # ✅ Filtrar warnings 401 de SUNAT
        },
        'ubl_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'ubl_converter.log',
            'formatter': 'verbose',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',  # Solo errores críticos 500+
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
            'filters': ['skip_unwanted_requests'],
        },
        'django.security': {
            'handlers': ['null'],  # ✅ Suprimir warnings de seguridad innecesarios
            'level': 'ERROR',
            'propagate': False,
        },
        'sunat_integration': {
            'handlers': ['sunat_file', 'console'],
            'level': 'INFO',  # ✅ Solo INFO y superior, no DEBUG
            'propagate': False,
        },
        'ubl_converter': {
            'handlers': ['ubl_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'digital_signature': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # ✅ Suprimir logs de librerías externas ruidosas
        'zeep': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'urllib3': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'requests': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
}

# ✅ SUNAT Configuration MEJORADA - Sin errores de URL
SUNAT_CONFIG = {
    # ✅ URLs corregidas sin ns1
    'BETA_URL': 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl',
    'PRODUCTION_URL': 'https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl',
    'USE_BETA': config('SUNAT_USE_BETA', default=True, cast=bool),
    'RUC': config('SUNAT_RUC', default='20000000001'),
    'USERNAME': config('SUNAT_USERNAME', default='MODDATOS'),
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

# ✅ Configuración específica para desarrollo
if DEBUG:
    # Desactivar algunas restricciones de seguridad en desarrollo
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    
    # IPs internas para debugging
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    # ✅ Suprimir warnings de desarrollo innecesarios
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    warnings.filterwarnings('ignore', message='.*well-known.*')

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