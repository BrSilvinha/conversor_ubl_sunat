# core/utils.py - VERSIÓN ULTRA-CORREGIDA PARA WINDOWS
import os
import re
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def normalize_file_path(file_path):
    """
    Normaliza rutas de archivos para ser consistentes entre Windows y Unix
    VERSIÓN ULTRA-CORREGIDA para problemas de Windows
    """
    if not file_path:
        return file_path
    
    try:
        logger.debug(f"🔧 Normalizando ruta original: '{file_path}'")
        
        # ✅ PASO 1: Detectar y corregir rutas malformadas de Windows
        if ':' in file_path and not '/' in file_path and not '\\' in file_path:
            # Ruta malformada como "C:UsersjhamiOneDrive..."
            logger.warning(f"⚠️ Detectada ruta malformada de Windows: {file_path}")
            
            # Reconstruir la ruta insertando separadores
            corrected_path = file_path
            
            # Insertar separador después de la unidad
            if corrected_path.startswith('C:') and not corrected_path.startswith('C:/') and not corrected_path.startswith('C:\\'):
                corrected_path = corrected_path.replace('C:', 'C:/')
            
            # Patrones comunes para insertar separadores
            patterns_to_fix = [
                ('Users', '/Users/'),
                ('OneDrive', '/OneDrive/'),
                ('Documentos', '/Documentos/'),
                ('proyectos', '/proyectos/'),
                ('conversor_ubl_sunat', '/conversor_ubl_sunat/'),
                ('media', '/media/'),
                ('xml_files', '/xml_files/'),
                ('zip_files', '/zip_files/'),
                ('cdr_files', '/cdr_files/')
            ]
            
            for pattern, replacement in patterns_to_fix:
                if pattern in corrected_path and replacement not in corrected_path:
                    corrected_path = corrected_path.replace(pattern, replacement)
            
            file_path = corrected_path
            logger.info(f"✅ Ruta corregida: {file_path}")
        
        # ✅ PASO 2: Convertir a Path object para normalización automática
        path_obj = Path(file_path)
        
        # ✅ PASO 3: Si es ruta absoluta, convertir a relativa respecto a MEDIA_ROOT
        media_root = Path(settings.MEDIA_ROOT)
        
        if path_obj.is_absolute():
            try:
                # Intentar hacer la ruta relativa a MEDIA_ROOT
                relative_path = path_obj.relative_to(media_root)
                normalized = str(relative_path).replace(os.sep, '/')
                logger.debug(f"✅ Ruta convertida de absoluta a relativa: {file_path} -> {normalized}")
                return normalized
            except ValueError:
                # Si no está dentro de MEDIA_ROOT, mantener absoluta pero normalizada
                normalized = str(path_obj).replace(os.sep, '/')
                logger.warning(f"⚠️ Ruta absoluta fuera de MEDIA_ROOT: {normalized}")
                return normalized
        else:
            # ✅ PASO 4: Ruta relativa - normalizar separadores
            normalized = str(path_obj).replace(os.sep, '/')
            
            # Remover prefijo 'media/' si existe
            if normalized.startswith('media/'):
                normalized = normalized[6:]
            
            logger.debug(f"✅ Ruta relativa normalizada: {file_path} -> {normalized}")
            return normalized
            
    except Exception as e:
        logger.error(f"❌ Error normalizando ruta {file_path}: {e}")
        # Fallback: limpieza básica
        fallback = file_path.replace('\\', '/').replace('media/', '')
        if fallback.startswith('C:') and 'Users' in fallback:
            # Intentar extraer solo la parte del archivo
            parts = fallback.split('/')
            if len(parts) > 0:
                filename = parts[-1]
                if '.' in filename:
                    # Detectar tipo de archivo y colocar en directorio correcto
                    if filename.endswith('.xml'):
                        return f"xml_files/{filename}"
                    elif filename.endswith('.zip') and filename.startswith('R-'):
                        return f"cdr_files/{filename}"
                    elif filename.endswith('.zip'):
                        return f"zip_files/{filename}"
        return fallback

def get_absolute_file_path(relative_path):
    """
    Convierte una ruta relativa almacenada en BD a ruta absoluta del sistema
    VERSIÓN ULTRA-CORREGIDA
    """
    if not relative_path:
        return None
    
    logger.debug(f"🔍 Obteniendo ruta absoluta para: '{relative_path}'")
    
    # Si ya es absoluta, devolverla normalizada
    if os.path.isabs(relative_path):
        abs_path = os.path.normpath(relative_path)
        logger.debug(f"✅ Ruta ya era absoluta: {abs_path}")
        return abs_path
    
    # ✅ NUEVA LÓGICA: Detectar rutas malformadas de Windows
    if ':' in relative_path and not relative_path.startswith('/'):
        # Parece ser una ruta absoluta de Windows mal formateada
        corrected_path = normalize_file_path(relative_path)
        if corrected_path != relative_path:
            # La normalización la corrigió, ahora construir ruta absoluta
            absolute_path = os.path.join(settings.MEDIA_ROOT, corrected_path.replace('/', os.sep))
        else:
            # Usar la ruta tal como está si parece absoluta
            absolute_path = os.path.normpath(relative_path)
    else:
        # Construir ruta absoluta normal
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path.replace('/', os.sep))
    
    final_path = os.path.normpath(absolute_path)
    logger.debug(f"✅ Ruta absoluta final: {final_path}")
    return final_path

def save_file_path_normalized(file_path):
    """
    Guarda una ruta de archivo de manera normalizada para almacenar en BD
    """
    normalized = normalize_file_path(file_path)
    logger.info(f"💾 Ruta normalizada para BD: {file_path} -> {normalized}")
    return normalized

def clean_filename_for_windows(filename):
    """
    Limpia un nombre de archivo para evitar problemas en Windows
    """
    if not filename:
        return filename
    
    # Caracteres no permitidos en Windows
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    
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
            logger.debug(f"📁 Directorio asegurado: {dir_path}")
        except Exception as e:
            logger.error(f"❌ Error creando directorio {dir_path}: {e}")

def find_file_in_media(filename):
    """
    Busca un archivo por nombre en todas las subcarpetas de media
    VERSIÓN MEJORADA con búsqueda inteligente
    """
    ensure_media_directories()
    
    logger.info(f"🔍 Buscando archivo: {filename}")
    
    # ✅ BÚSQUEDA PRIORITARIA: Buscar por tipo de archivo
    search_paths = []
    
    # Determinar directorio probable basado en el nombre del archivo
    if filename.endswith('.xml'):
        search_paths.append(os.path.join(settings.MEDIA_ROOT, 'xml_files'))
    elif filename.endswith('.zip'):
        if filename.startswith('R-'):
            search_paths.append(os.path.join(settings.MEDIA_ROOT, 'cdr_files'))
        else:
            search_paths.append(os.path.join(settings.MEDIA_ROOT, 'zip_files'))
    
    # Agregar todos los directorios como respaldo
    search_paths.extend([
        settings.MEDIA_ROOT,
        os.path.join(settings.MEDIA_ROOT, 'xml_files'),
        os.path.join(settings.MEDIA_ROOT, 'zip_files'),
        os.path.join(settings.MEDIA_ROOT, 'cdr_files'),
        os.path.join(settings.MEDIA_ROOT, 'certificates')
    ])
    
    # ✅ BÚSQUEDA INTELIGENTE: También buscar variaciones del nombre
    filename_variations = [
        filename,
        filename.replace('00000001', '20000000001'),  # Corrección común de RUC
        filename.replace('20000000001', '23022479065'),  # Otro RUC común
    ]
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
            
        # Búsqueda directa
        for variation in filename_variations:
            potential_path = os.path.join(search_path, variation)
            if os.path.exists(potential_path):
                logger.info(f"✅ Archivo encontrado: {potential_path}")
                return potential_path
        
        # Búsqueda recursiva
        try:
            for root, dirs, files in os.walk(search_path):
                for variation in filename_variations:
                    if variation in files:
                        found_path = os.path.join(root, variation)
                        logger.info(f"✅ Archivo encontrado recursivamente: {found_path}")
                        return found_path
        except Exception as e:
            logger.warning(f"⚠️ Error en búsqueda recursiva en {search_path}: {e}")
    
    logger.warning(f"❌ Archivo no encontrado: {filename}")
    return None

def repair_file_path(malformed_path):
    """
    Repara rutas de archivos malformadas específicamente para Windows
    """
    if not malformed_path:
        return malformed_path
    
    logger.debug(f"🔧 Reparando ruta malformada: {malformed_path}")
    
    # Si es una ruta Windows sin separadores
    if ':' in malformed_path and '\\' not in malformed_path and '/' not in malformed_path:
        # Extraer solo el nombre del archivo
        if malformed_path.count('.') == 1:  # Probablemente hay un archivo
            parts = re.split(r'(?=[A-Z][a-z])', malformed_path)
            for part in reversed(parts):
                if '.' in part and len(part) > 3:
                    # Probablemente es un archivo
                    filename = part
                    logger.info(f"✅ Archivo extraído de ruta malformada: {filename}")
                    return filename
    
    return malformed_path

def get_safe_file_path(file_path_from_db):
    """
    Obtiene una ruta de archivo segura, manejando todos los casos problemáticos
    """
    if not file_path_from_db:
        return None
    
    logger.debug(f"🛡️ Obteniendo ruta segura para: {file_path_from_db}")
    
    # Intentar normalizar primero
    try:
        normalized = normalize_file_path(file_path_from_db)
        absolute = get_absolute_file_path(normalized)
        
        if os.path.exists(absolute):
            logger.debug(f"✅ Ruta segura encontrada: {absolute}")
            return absolute
    except Exception as e:
        logger.warning(f"⚠️ Error en normalización: {e}")
    
    # Si no funciona, intentar búsqueda por nombre de archivo
    try:
        # Extraer nombre de archivo
        filename = os.path.basename(file_path_from_db)
        if not filename:
            # Intentar extraer de ruta malformada
            filename = repair_file_path(file_path_from_db)
        
        if filename and '.' in filename:
            found_path = find_file_in_media(filename)
            if found_path:
                logger.info(f"✅ Archivo encontrado por búsqueda: {found_path}")
                return found_path
    except Exception as e:
        logger.warning(f"⚠️ Error en búsqueda: {e}")
    
    logger.error(f"❌ No se pudo obtener ruta segura para: {file_path_from_db}")
    return None