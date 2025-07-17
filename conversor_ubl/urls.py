# conversor_ubl/urls.py - VERSIÓN COMPLETA Y CORREGIDA
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

# ✅ Vista para servir el frontend
class UBLTesterView(TemplateView):
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Conversor UBL 2.1 - Panel de Pruebas',
            'api_base_url': '/api',
            'debug': settings.DEBUG,
            'version': '1.0.0'
        })
        return context

# ✅ Vista de salud del sistema
@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Endpoint de verificación de salud del sistema"""
    import django
    from django.db import connection
    
    health_status = {
        'status': 'healthy',
        'django_version': django.get_version(),
        'debug_mode': settings.DEBUG,
        'database': 'disconnected',
        'services': {
            'ubl_converter': 'available',
            'digital_signature': 'available',
            'sunat_integration': 'available'
        },
        'timestamp': str(timezone.now()) if 'timezone' in globals() else str(datetime.now())
    }
    
    # Verificar conexión a base de datos
    try:
        connection.ensure_connection()
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Verificar configuración SUNAT
    try:
        sunat_config = settings.SUNAT_CONFIG
        if sunat_config.get('RUC') and sunat_config.get('USERNAME'):
            health_status['services']['sunat_config'] = 'configured'
        else:
            health_status['services']['sunat_config'] = 'not_configured'
    except Exception:
        health_status['services']['sunat_config'] = 'error'
    
    # Verificar certificado
    try:
        cert_path = settings.SUNAT_CONFIG.get('CERTIFICATE_PATH')
        if cert_path and os.path.exists(cert_path):
            health_status['services']['certificate'] = 'available'
        else:
            health_status['services']['certificate'] = 'not_found'
    except Exception:
        health_status['services']['certificate'] = 'error'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)

# ✅ Vista de información del sistema
@csrf_exempt
@require_http_methods(["GET"])
def system_info(request):
    """Endpoint con información del sistema"""
    import platform
    import sys
    
    system_info = {
        'system': {
            'platform': platform.platform(),
            'python_version': sys.version,
            'django_version': django.get_version(),
        },
        'configuration': {
            'debug': settings.DEBUG,
            'language': settings.LANGUAGE_CODE,
            'timezone': settings.TIME_ZONE,
            'database_engine': settings.DATABASES['default']['ENGINE'],
        },
        'ubl_config': {
            'version': settings.UBL_CONFIG.get('VERSION'),
            'customization_id': settings.UBL_CONFIG.get('CUSTOMIZATION_ID'),
        },
        'sunat_config': {
            'use_beta': settings.SUNAT_CONFIG.get('USE_BETA'),
            'ruc': settings.SUNAT_CONFIG.get('RUC'),
            'environment': 'BETA' if settings.SUNAT_CONFIG.get('USE_BETA') else 'PRODUCTION',
        },
        'directories': {
            'media_root': str(settings.MEDIA_ROOT),
            'static_root': str(settings.STATIC_ROOT),
            'base_dir': str(settings.BASE_DIR),
        }
    }
    
    return JsonResponse(system_info)

# ✅ Importaciones necesarias
import os
from datetime import datetime
from django.utils import timezone
import django

# URLs principales
urlpatterns = [
    # ✅ Admin de Django
    path('admin/', admin.site.urls),
    
    # ✅ APIs del conversor UBL
    path('api/', include('api.urls')),
    
    # ✅ Frontend principal
    path('', UBLTesterView.as_view(), name='frontend'),
    path('tester/', UBLTesterView.as_view(), name='tester'),
    path('panel/', UBLTesterView.as_view(), name='panel'),
    
    # ✅ Endpoints de utilidad
    path('health/', health_check, name='health_check'),
    path('system-info/', system_info, name='system_info'),
]

# ✅ Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    # Archivos media (XMLs, ZIPs, CDRs generados)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Archivos estáticos (CSS, JS, imágenes)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)
    
    # ✅ Rutas adicionales para desarrollo
    urlpatterns += [
        # Acceso directo a logs (solo en desarrollo)
        path('logs/django/', lambda r: JsonResponse({'log_file': str(settings.BASE_DIR / 'logs' / 'django.log')})),
        path('logs/ubl/', lambda r: JsonResponse({'log_file': str(settings.BASE_DIR / 'logs' / 'ubl_converter.log')})),
        path('logs/sunat/', lambda r: JsonResponse({'log_file': str(settings.BASE_DIR / 'logs' / 'sunat_integration.log')})),
        
        # Vista de configuración (solo en desarrollo)
        path('debug/config/', lambda r: JsonResponse({
            'settings': {
                'SUNAT_CONFIG': settings.SUNAT_CONFIG,
                'UBL_CONFIG': settings.UBL_CONFIG,
                'TEST_DATA_CONFIG': getattr(settings, 'TEST_DATA_CONFIG', {}),
                'VALIDATION_CONFIG': getattr(settings, 'VALIDATION_CONFIG', {}),
            }
        }) if settings.DEBUG else JsonResponse({'error': 'Not available in production'})),
    ]

# ✅ Handler para errores personalizados
def custom_404_view(request, exception):
    """Vista personalizada para errores 404"""
    if request.path.startswith('/api/'):
        return JsonResponse({
            'status': 'error',
            'message': 'Endpoint no encontrado',
            'path': request.path,
            'available_endpoints': [
                '/api/create-test-scenarios/',
                '/api/invoice/{id}/convert-ubl/',
                '/api/invoice/{id}/sign/',
                '/api/invoice/{id}/send-sunat/',
                '/api/invoice/{id}/status/',
                '/api/invoice/{id}/process-complete/',
                '/api/test-sunat-connection/',
            ]
        }, status=404)
    else:
        # Para rutas no-API, redirigir al frontend
        return UBLTesterView.as_view()(request)

def custom_500_view(request):
    """Vista personalizada para errores 500"""
    return JsonResponse({
        'status': 'error',
        'message': 'Error interno del servidor',
        'debug': settings.DEBUG,
        'timestamp': str(timezone.now())
    }, status=500)

# ✅ Configurar handlers de error
if settings.DEBUG:
    handler404 = custom_404_view
    handler500 = custom_500_view