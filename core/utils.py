# core/utils.py - ARCHIVO NUEVO - CREAR ESTE ARCHIVO
import os
import re
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def normalize_file_path(file_path):
    """
    Normaliza rutas de archivos para ser consistentes entre Windows y Unix
    y almacenarlas de manera estándar en la base de datos
    """
    if not file_path:
        return file_path
    
    try:
        # ✅ PASO 1: Convertir a Path object para normalización automática
        path_obj = Path(file_path)
        
        # ✅ PASO 2: Si es ruta absoluta, convertir a relativa respecto a MEDIA_ROOT
        media_root = Path(settings.MEDIA_ROOT)
        
        if path_obj.is_absolute():
            try:
                # Intentar hacer la ruta relativa a MEDIA_ROOT
                relative_path = path_obj.relative_to(media_root)
                normalized = str(relative_path).replace(os.sep, '/')
                logger.debug(f"Ruta convertida de absoluta a relativa: {file_path} -> {normalized}")
                return normalized
            except ValueError:
                # Si no está dentro de MEDIA_ROOT, mantener absoluta pero normalizada
                normalized = str(path_obj).replace(os.sep, '/')
                logger.warning(f"Ruta absoluta fuera de MEDIA_ROOT: {normalized}")
                return normalized
        else:
            # ✅ PASO 3: Ruta relativa - normalizar separadores
            normalized = str(path_obj).replace(os.sep, '/')
            
            # Remover prefijo 'media/' si existe
            if normalized.startswith('media/'):
                normalized = normalized[6:]
            
            logger.debug(f"Ruta relativa normalizada: {file_path} -> {normalized}")
            return normalized
            
    except Exception as e:
        logger.error(f"Error normalizando ruta {file_path}: {e}")
        # Fallback: limpieza básica
        return file_path.replace('\\', '/').replace('media/', '')

def get_absolute_file_path(relative_path):
    """
    Convierte una ruta relativa almacenada en BD a ruta absoluta del sistema
    """
    if not relative_path:
        return None
    
    # Si ya es absoluta, devolverla normalizada
    if os.path.isabs(relative_path):
        return os.path.normpath(relative_path)
    
    # Construir ruta absoluta
    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path.replace('/', os.sep))
    return os.path.normpath(absolute_path)

def save_file_path_normalized(file_path):
    """
    Guarda una ruta de archivo de manera normalizada para almacenar en BD
    """
    normalized = normalize_file_path(file_path)
    logger.info(f"Ruta normalizada para BD: {file_path} -> {normalized}")
    return normalized

def clean_filename_for_windows(filename):
    """
    Limpia un nombre de archivo para evitar problemas en Windows
    """
    if not filename:
        return filename
    
    # Caracteres no permitidos en Windows
    invalid_chars = r'[<>:"/\\|?*]'
    
    # Remover caracteres inválidos
    clean_name = re.sub(invalid_chars, '_', filename)
    
    # Remover espacios múltiples y al inicio/final
    clean_name = re.sub(r'\s+', '_', clean_name.strip())
    
    # Asegurar que no esté vacío
    if not clean_name or clean_name in ['.', '..']:
        clean_name = 'archivo_sin_nombre'
    
    return clean_name

def ensure_media_directories():
    """
    Asegura que existan todos los directorios de media necesarios
    """
    directories = [
        'xml_files',
        'zip_files', 
        'cdr_files',
        'certificates'
    ]
    
    for directory in directories:
        dir_path = os.path.join(settings.MEDIA_ROOT, directory)
        try:
            os.makedirs(dir_path, exist_ok=True)
            logger.debug(f"Directorio asegurado: {dir_path}")
        except Exception as e:
            logger.error(f"Error creando directorio {dir_path}: {e}")

def find_file_in_media(filename):
    """
    Busca un archivo por nombre en todas las subcarpetas de media
    """
    ensure_media_directories()
    
    search_paths = [
        settings.MEDIA_ROOT,
        os.path.join(settings.MEDIA_ROOT, 'xml_files'),
        os.path.join(settings.MEDIA_ROOT, 'zip_files'),
        os.path.join(settings.MEDIA_ROOT, 'cdr_files')
    ]
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            # Búsqueda directa
            potential_path = os.path.join(search_path, filename)
            if os.path.exists(potential_path):
                logger.info(f"Archivo encontrado: {potential_path}")
                return potential_path
            
            # Búsqueda recursiva
            for root, dirs, files in os.walk(search_path):
                if filename in files:
                    found_path = os.path.join(root, filename)
                    logger.info(f"Archivo encontrado recursivamente: {found_path}")
                    return found_path
    
    logger.warning(f"Archivo no encontrado: {filename}")
    return None