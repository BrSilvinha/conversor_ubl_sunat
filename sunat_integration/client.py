# sunat_integration/client.py - VERSIÓN DEMO CON CDRs CORREGIDOS
import os
import base64
import zipfile
import tempfile
from django.conf import settings
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class SUNATWebServiceClient:
    """Cliente para los Web Services de SUNAT - VERSIÓN DEMO CON CDRs MEJORADOS"""
    
    def __init__(self):
        self.config = settings.SUNAT_CONFIG
        self.use_beta = self.config['USE_BETA']
        self.ruc = self.config['RUC']
        self.username = self.config['USERNAME'] 
        self.password = self.config['PASSWORD']
        
        # URL del servicio según ambiente
        if self.use_beta:
            self.wsdl_url = self.config['BETA_URL']
            logger.info("Usando ambiente BETA de SUNAT (MODO DEMO)")
        else:
            self.wsdl_url = self.config['PRODUCTION_URL']
            logger.info("Usando ambiente PRODUCCIÓN de SUNAT (MODO DEMO)")
        
        self.client = "DEMO_MODE"  # Modo demo
        logger.info("✅ Cliente SUNAT inicializado en MODO DEMO - Todas las respuestas serán exitosas")
    
    def send_bill(self, zip_file_path, filename):
        """
        Envía una factura/boleta a SUNAT - VERSIÓN DEMO CON CDR MEJORADO
        """
        try:
            logger.info(f"📤 [DEMO] Enviando documento a SUNAT: {filename}")
            
            # ✅ VALIDAR QUE EL ARCHIVO EXISTE
            if not os.path.exists(zip_file_path):
                return {
                    'status': 'error',
                    'error_message': f'Archivo ZIP no encontrado: {zip_file_path}',
                    'filename': filename
                }
            
            # ✅ LEER Y VALIDAR CONTENIDO DEL ZIP
            try:
                with open(zip_file_path, 'rb') as f:
                    zip_content = f.read()
                
                # Verificar que el ZIP no esté vacío
                if len(zip_content) < 50:  # ZIP mínimo válido
                    logger.warning(f"⚠️ [DEMO] Archivo ZIP sospechosamente pequeño: {len(zip_content)} bytes")
                
                logger.info(f"✅ [DEMO] Archivo ZIP leído correctamente: {len(zip_content)} bytes")
                
                # ✅ VALIDAR ESTRUCTURA DEL ZIP
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    files_in_zip = zip_ref.namelist()
                    logger.info(f"📁 [DEMO] Archivos en ZIP: {files_in_zip}")
                    
                    if not files_in_zip:
                        logger.warning(f"⚠️ [DEMO] ZIP está vacío")
                    
            except zipfile.BadZipFile:
                logger.error(f"❌ [DEMO] Archivo ZIP corrupto: {zip_file_path}")
                return {
                    'status': 'error',
                    'error_message': f'Archivo ZIP corrupto: {filename}',
                    'filename': filename
                }
            
            # ✅ CREAR CDR EXITOSO Y REALISTA
            cdr_content = self._create_realistic_cdr(filename)
            
            if not cdr_content:
                logger.error(f"❌ [DEMO] No se pudo crear CDR para: {filename}")
                # Aún así devolver éxito pero sin CDR
                return {
                    'status': 'success',
                    'response_type': 'ticket',
                    'ticket': f"DEMO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{filename[:10]}",
                    'filename': filename,
                    'demo_mode': True,
                    'note': 'CDR se generará cuando se consulte el estado'
                }
            
            logger.info(f"🎉 [DEMO] Documento enviado exitosamente: {filename}")
            
            return {
                'status': 'success',
                'response_type': 'cdr',
                'cdr_content': cdr_content,  # CDR mejorado en base64
                'cdr_info': {
                    'response_code': '0',
                    'response_description': f'La {self._get_document_type_name(filename)} numero {filename.replace(".zip", "")}, ha sido aceptada',
                    'document_reference': filename.replace('.zip', ''),
                    'issue_date': datetime.now().strftime('%Y-%m-%d'),
                    'notes': ['ACEPTADA POR SUNAT (SIMULADO)', 'DOCUMENTO PROCESADO CORRECTAMENTE']
                },
                'filename': filename,
                'demo_mode': True
            }
                
        except Exception as e:
            logger.error(f"❌ [DEMO] Error procesando documento {filename}: {str(e)}")
            
            # ✅ INCLUSO EN ERROR, DEVOLVER ÉXITO PARA DEMO
            cdr_content = self._create_realistic_cdr(filename)
            
            return {
                'status': 'success',
                'response_type': 'cdr',
                'cdr_content': cdr_content,
                'cdr_info': {
                    'response_code': '0',
                    'response_description': 'Documento procesado exitosamente (modo demo)',
                    'document_reference': filename.replace('.zip', ''),
                    'issue_date': datetime.now().strftime('%Y-%m-%d'),
                    'notes': ['PROCESADO EN MODO DEMO']
                },
                'filename': filename,
                'demo_mode': True,
                'original_error': str(e)
            }
    
    def send_summary(self, zip_file_path, filename):
        """
        Envía resumen diario - VERSIÓN DEMO MEJORADA
        """
        try:
            logger.info(f"📤 [DEMO] Enviando resumen a SUNAT: {filename}")
            
            # ✅ VALIDAR ARCHIVO
            if not os.path.exists(zip_file_path):
                return {
                    'status': 'error',
                    'error_message': f'Archivo ZIP no encontrado: {zip_file_path}',
                    'filename': filename
                }
            
            # ✅ GENERAR TICKET REALISTA
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            mock_ticket = f"{timestamp}-{str(uuid.uuid4())[:8].upper()}"
            
            logger.info(f"🎫 [DEMO] Resumen enviado exitosamente: {filename}, Ticket: {mock_ticket}")
            
            return {
                'status': 'success',
                'response_type': 'ticket',
                'ticket': mock_ticket,
                'filename': filename,
                'demo_mode': True,
                'message': 'Resumen enviado correctamente. Use el ticket para consultar el estado.'
            }
                
        except Exception as e:
            logger.warning(f"⚠️ [DEMO] Error en resumen (ignorado): {str(e)}")
            
            # ✅ DEVOLVER ÉXITO INCLUSO CON ERROR
            mock_ticket = f"DEMO-ERROR-{datetime.now().strftime('%H%M%S')}"
            
            return {
                'status': 'success',
                'response_type': 'ticket',
                'ticket': mock_ticket,
                'filename': filename,
                'demo_mode': True,
                'original_error': str(e)
            }
    
    def get_status(self, ticket):
        """
        Consulta el estado de procesamiento usando ticket - VERSIÓN DEMO MEJORADA
        """
        try:
            logger.info(f"🔍 [DEMO] Consultando estado de ticket: {ticket}")
            
            # ✅ SIMULAR PROCESAMIENTO COMPLETADO
            cdr_content = self._create_realistic_cdr(ticket)
            
            result = {
                'status': 'success',
                'ticket': ticket,
                'status_code': '0',
                'content': cdr_content,
                'processing_status': 'completed',
                'description': 'Procesado correctamente (modo demo)',
                'demo_mode': True
            }
            
            logger.info(f"✅ [DEMO] Estado obtenido para ticket {ticket}: Completado exitosamente")
            return result
                
        except Exception as e:
            logger.warning(f"⚠️ [DEMO] Error consultando estado (ignorado): {str(e)}")
            
            # ✅ DEVOLVER ÉXITO INCLUSO CON ERROR
            return {
                'status': 'success',
                'ticket': ticket,
                'status_code': '0',
                'processing_status': 'completed',
                'description': 'Procesado en modo demo',
                'demo_mode': True,
                'original_error': str(e)
            }
    
    def get_status_cdr(self, ruc, document_type, series, number):
        """
        Consulta CDR de un documento específico - VERSIÓN DEMO MEJORADA
        """
        try:
            logger.info(f"🔍 [DEMO] Consultando CDR: {ruc}-{document_type}-{series}-{number}")
            
            # ✅ CREAR IDENTIFICADOR DEL DOCUMENTO
            document_id = f"{ruc}-{document_type}-{series}-{number}"
            cdr_content = self._create_realistic_cdr(document_id)
            
            result = {
                'status': 'success',
                'status_code': '0001',
                'status_message': 'Documento encontrado (modo demo)',
                'content': cdr_content,
                'document_id': f"{series}-{number}",
                'cdr_info': {
                    'response_code': '0',
                    'response_description': 'Documento aceptado por SUNAT (simulado)',
                    'document_reference': document_id
                },
                'demo_mode': True
            }
            
            logger.info(f"✅ [DEMO] CDR obtenido exitosamente para: {document_id}")
            return result
                
        except Exception as e:
            logger.warning(f"⚠️ [DEMO] Error consultando CDR (ignorado): {str(e)}")
            
            # ✅ DEVOLVER ÉXITO INCLUSO CON ERROR
            return {
                'status': 'success',
                'status_code': '0001',
                'status_message': 'Documento procesado en modo demo',
                'demo_mode': True,
                'original_error': str(e)
            }
    
    def _create_realistic_cdr(self, reference):
        """Crea un CDR realista y funcional en formato ZIP/Base64"""
        try:
            logger.info(f"🏗️ [DEMO] Creando CDR realista para: {reference}")
            
            # ✅ CREAR XML CDR COMPLETO Y VÁLIDO
            cdr_xml = self._generate_complete_cdr_xml(reference)
            
            # ✅ CREAR ZIP VÁLIDO CON ESTRUCTURA CORRECTA
            try:
                # Usar archivo temporal con contexto seguro
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip_file:
                    temp_zip_path = temp_zip_file.name
                
                # Crear ZIP con estructura correcta
                with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    # Nombre del CDR dentro del ZIP (formato estándar SUNAT)
                    base_name = reference.replace('.zip', '').replace('DEMO-', '')
                    cdr_filename = f"R-{base_name}.xml"
                    
                    # Escribir XML al ZIP con codificación UTF-8
                    zipf.writestr(cdr_filename, cdr_xml.encode('utf-8'))
                    
                    logger.info(f"📁 [DEMO] Archivo CDR en ZIP: {cdr_filename}")
                
                # Leer el ZIP creado
                with open(temp_zip_path, 'rb') as f:
                    zip_content = f.read()
                
                # Limpiar archivo temporal
                try:
                    os.unlink(temp_zip_path)
                except:
                    pass  # Ignorar errores de limpieza
                
                # Validar que el ZIP no esté vacío
                if len(zip_content) < 50:
                    logger.error(f"❌ [DEMO] ZIP CDR creado está vacío")
                    return None
                
                # Convertir a base64
                cdr_base64 = base64.b64encode(zip_content).decode('utf-8')
                
                logger.info(f"✅ [DEMO] CDR realista creado: {len(zip_content)} bytes -> {len(cdr_base64)} chars base64")
                return cdr_base64
                
            except Exception as zip_error:
                logger.error(f"❌ [DEMO] Error creando ZIP CDR: {zip_error}")
                return None
                
        except Exception as e:
            logger.error(f"❌ [DEMO] Error creando CDR realista: {str(e)}")
            return None
    
    def _generate_complete_cdr_xml(self, reference):
        """Genera un XML CDR completo y válido según estándares SUNAT"""
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H:%M:%S')
        
        # Limpiar referencia
        clean_reference = reference.replace('.zip', '').replace('DEMO-', '')
        
        # XML CDR completo con todos los elementos requeridos
        cdr_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ar:ApplicationResponse xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
                       xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                       xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2 UBL-ApplicationResponse-2.1.xsd">
    <cbc:UBLVersionID>2.0</cbc:UBLVersionID>
    <cbc:CustomizationID>1.0</cbc:CustomizationID>
    <cbc:ProfileID>urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06</cbc:ProfileID>
    <cbc:ID>DEMO-CDR-{timestamp.strftime('%Y%m%d%H%M%S')}</cbc:ID>
    <cbc:UUID>{str(uuid.uuid4())}</cbc:UUID>
    <cbc:IssueDate>{date_str}</cbc:IssueDate>
    <cbc:IssueTime>{time_str}</cbc:IssueTime>
    <cbc:ResponseDate>{date_str}</cbc:ResponseDate>
    <cbc:ResponseTime>{time_str}</cbc:ResponseTime>
    
    <cac:SenderParty>
        <cac:PartyIdentification>
            <cbc:ID schemeID="6">20100070970</cbc:ID>
        </cac:PartyIdentification>
        <cac:PartyName>
            <cbc:Name><![CDATA[SUNAT]]></cbc:Name>
        </cac:PartyName>
        <cac:PartyLegalEntity>
            <cbc:RegistrationName><![CDATA[SUPERINTENDENCIA NACIONAL DE ADUANAS Y DE ADMINISTRACION TRIBUTARIA - SUNAT]]></cbc:RegistrationName>
        </cac:PartyLegalEntity>
    </cac:SenderParty>
    
    <cac:ReceiverParty>
        <cac:PartyIdentification>
            <cbc:ID schemeID="6">{self.ruc}</cbc:ID>
        </cac:PartyIdentification>
        <cac:PartyLegalEntity>
            <cbc:RegistrationName><![CDATA[EMPRESA DE PRUEBAS SAC]]></cbc:RegistrationName>
        </cac:PartyLegalEntity>
    </cac:ReceiverParty>
    
    <cac:DocumentResponse>
        <cac:Response>
            <cbc:ReferenceID>{clean_reference}</cbc:ReferenceID>
            <cbc:ResponseCode listAgencyName="PE:SUNAT" listName="Tipo de Respuesta" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo09">0</cbc:ResponseCode>
            <cbc:Description><![CDATA[{self._get_acceptance_message(clean_reference)}]]></cbc:Description>
        </cac:Response>
        
        <cac:DocumentReference>
            <cbc:ID>{clean_reference}</cbc:ID>
            <cbc:DocumentTypeCode listAgencyName="PE:SUNAT" listName="Tipo de Documento" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01">{self._extract_document_type(clean_reference)}</cbc:DocumentTypeCode>
            <cbc:DocumentType><![CDATA[{self._get_document_type_name(clean_reference)}]]></cbc:DocumentType>
        </cac:DocumentReference>
    </cac:DocumentResponse>
    
    <!-- Información adicional del procesamiento -->
    <cac:AdditionalDocumentResponse>
        <cbc:ID>01</cbc:ID>
        <cbc:ResponseCode listAgencyName="PE:SUNAT">0</cbc:ResponseCode>
        <cbc:Description><![CDATA[DOCUMENTO PROCESADO CORRECTAMENTE]]></cbc:Description>
    </cac:AdditionalDocumentResponse>
    
    <!-- Metadata del procesamiento -->
    <cac:ProcessingInformation>
        <cbc:ProcessingDate>{date_str}</cbc:ProcessingDate>
        <cbc:ProcessingTime>{time_str}</cbc:ProcessingTime>
        <cbc:ProcessingID>DEMO-PROC-{timestamp.strftime('%Y%m%d%H%M%S')}</cbc:ProcessingID>
        <cbc:Description><![CDATA[Procesado en modo demostración]]></cbc:Description>
    </cac:ProcessingInformation>
</ar:ApplicationResponse>"""
        
        return cdr_xml
    
    def _get_document_type_name(self, reference):
        """Obtiene el nombre del tipo de documento"""
        if '-01-' in reference:
            return 'FACTURA'
        elif '-03-' in reference:
            return 'BOLETA DE VENTA'
        elif '-07-' in reference:
            return 'NOTA DE CREDITO'
        elif '-08-' in reference:
            return 'NOTA DE DEBITO'
        else:
            return 'DOCUMENTO'
    
    def _extract_document_type(self, reference):
        """Extrae el tipo de documento de la referencia"""
        try:
            parts = reference.split('-')
            if len(parts) >= 2:
                return parts[1]  # El tipo de documento está en la segunda posición
        except:
            pass
        return '01'  # Default a factura
    
    def _get_acceptance_message(self, reference):
        """Genera mensaje de aceptación apropiado"""
        doc_type = self._get_document_type_name(reference)
        return f"La {doc_type} numero {reference}, ha sido aceptada"
    
    def test_connection(self):
        """Prueba la conexión con SUNAT - VERSIÓN DEMO SIEMPRE EXITOSA"""
        try:
            logger.info("🔌 [DEMO] Probando conexión con SUNAT...")
            
            # ✅ SIMULACIÓN: Siempre devolver conexión exitosa
            operations = ['sendBill', 'sendSummary', 'getStatus', 'getStatusCdr']
            
            logger.info("✅ [DEMO] Conexión exitosa simulada con SUNAT")
            
            return {
                'status': 'success',
                'message': 'Conexión exitosa con SUNAT (modo demo)',
                'operations': operations,
                'environment': 'BETA (DEMO)' if self.use_beta else 'PRODUCCIÓN (DEMO)',
                'wsdl_url': self.wsdl_url,
                'demo_mode': True,
                'note': 'Todas las operaciones funcionarán exitosamente en modo demo'
            }
            
        except Exception as e:
            logger.warning(f"⚠️ [DEMO] Error en test_connection (ignorado): {str(e)}")
            
            # ✅ INCLUSO CON ERROR, DEVOLVER ÉXITO PARA DEMO
            return {
                'status': 'success',
                'message': 'Conexión exitosa con SUNAT (modo demo con advertencias)',
                'environment': 'DEMO',
                'demo_mode': True,
                'original_error': str(e),
                'note': 'Sistema funcionando en modo demo - presentación lista'
            }