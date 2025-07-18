# conversor_ubl/middleware.py - CREAR ESTE ARCHIVO NUEVO
import logging
from django.http import Http404, HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class SuppressUnwantedWarningsMiddleware(MiddlewareMixin):
    """Middleware para suprimir warnings innecesarios y requests automáticos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Procesa requests antes de llegar a las vistas"""
        # Lista de paths que queremos suprimir silenciosamente
        suppress_paths = [
            '/.well-known/appspecific/com.chrome.devtools.json',
            '/.well-known/security.txt', 
            '/.well-known/apple-app-site-association',
            '/robots.txt',
            '/favicon.ico',
            '/apple-touch-icon.png',
            '/apple-touch-icon-precomposed.png',
            '/manifest.json',
            '/browserconfig.xml'
        ]
        
        # Si es un path que queremos suprimir, devolver respuesta vacía
        if request.path in suppress_paths:
            logger.debug(f"Suprimiendo request automático: {request.path}")
            return HttpResponse(status=204)  # No Content - más limpio que 404
        
        return None
    
    def process_exception(self, request, exception):
        """Procesa excepciones para logging mejorado"""
        # Si es un 404 de paths suprimidos, no log
        if isinstance(exception, Http404):
            suppress_paths = [
                '/.well-known/',
                '/robots.txt',
                '/favicon.ico',
                '/apple-touch-icon',
                '/manifest.json'
            ]
            
            if any(path in request.path for path in suppress_paths):
                # No logear estos 404s
                return HttpResponse(status=204)
        
        return None