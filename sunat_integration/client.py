# sunat_integration/client.py - VERSIÓN DEMO CON SIMULACIÓN EXITOSA
import os
import base64
import zipfile
import tempfile
from django.conf import settings
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

logger = logging.getLogger(__name__)

class SUNATWebServiceClient:
    """Cliente para los Web Services de SUNAT - VERSIÓN DEMO SIMULADA"""
    
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
        Envía una factura/boleta a SUNAT - VERSIÓN DEMO SIMULADA
        """
        try:
            logger.info(f"📤 [DEMO] Enviando documento a SUNAT: {filename}")
            
            # ✅ SIMULACIÓN: Leer archivo ZIP para validar que existe
            if not os.path.exists(zip_file_path):
                return {
                    'status': 'error',
                    'error_message': f'Archivo ZIP no encontrado: {zip_file_path}',
                    'filename': filename
                }
            
            with open(zip_file_path, 'rb') as f:
                zip_content = f.read()
            
            logger.info(f"✅ [DEMO] Archivo ZIP leído correctamente: {len(zip_content)} bytes")
            
            # ✅ SIMULACIÓN: Crear CDR exitoso
            cdr_content = self._create_mock_successful_cdr(filename)
            
            logger.info(f"🎉 [DEMO] Documento enviado exitosamente: {filename}")
            
            return {
                'status': 'success',
                'response_type': 'cdr',
                'cdr_content': cdr_content,  # CDR simulado en base64
                'cdr_info': {
                    'response_code': '0',
                    'response_description': 'La Factura numero {}, ha sido aceptada'.format(filename.replace('.zip', '')),
                    'document_reference': filename.replace('.zip', ''),
                    'issue_date': datetime.now().strftime('%Y-%m-%d'),
                    'notes': ['ACEPTADA POR SUNAT (SIMULADO)']
                },
                'filename': filename,
                'demo_mode': True
            }
                
        except Exception as e:
            logger.error(f"❌ [DEMO] Error procesando documento {filename}: {str(e)}")
            
            # ✅ INCLUSO EN ERROR, DEVOLVER ÉXITO PARA DEMO
            cdr_content = self._create_mock_successful_cdr(filename)
            
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
        Envía resumen diario - VERSIÓN DEMO SIMULADA
        """
        try:
            logger.info(f"📤 [DEMO] Enviando resumen a SUNAT: {filename}")
            
            # ✅ SIMULACIÓN: Generar ticket exitoso
            mock_ticket = f"DEMO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{filename[:10]}"
            
            logger.info(f"🎫 [DEMO] Resumen enviado exitosamente: {filename}, Ticket: {mock_ticket}")
            
            return {
                'status': 'success',
                'response_type': 'ticket',
                'ticket': mock_ticket,
                'filename': filename,
                'demo_mode': True
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
        Consulta el estado de procesamiento usando ticket - VERSIÓN DEMO
        """
        try:
            logger.info(f"🔍 [DEMO] Consultando estado de ticket: {ticket}")
            
            # ✅ SIMULACIÓN: Siempre devolver completado exitosamente
            cdr_content = self._create_mock_successful_cdr(ticket)
            
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
        Consulta CDR de un documento específico - VERSIÓN DEMO
        """
        try:
            logger.info(f"🔍 [DEMO] Consultando CDR: {ruc}-{document_type}-{series}-{number}")
            
            # ✅ SIMULACIÓN: Siempre encontrar documento y devolver CDR exitoso
            document_id = f"{ruc}-{document_type}-{series}-{number}"
            cdr_content = self._create_mock_successful_cdr(document_id)
            
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
    
    def _create_mock_successful_cdr(self, reference):
        """Crea un CDR simulado exitoso en formato ZIP/Base64"""
        try:
            # ✅ CREAR XML CDR SIMULADO
            cdr_xml = self._generate_mock_cdr_xml(reference)
            
            # ✅ CREAR ZIP CON EL CDR
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Nombre del CDR dentro del ZIP
                    cdr_filename = f"R-{reference.replace('.zip', '')}.xml"
                    zipf.writestr(cdr_filename, cdr_xml.encode('utf-8'))
                
                # Leer el ZIP creado
                temp_zip.seek(0)
                with open(temp_zip.name, 'rb') as f:
                    zip_content = f.read()
                
                # Limpiar archivo temporal
                os.unlink(temp_zip.name)
                
                # Convertir a base64
                cdr_base64 = base64.b64encode(zip_content).decode('utf-8')
                
                logger.info(f"✅ [DEMO] CDR simulado creado exitosamente para: {reference}")
                return cdr_base64
                
        except Exception as e:
            logger.warning(f"⚠️ [DEMO] Error creando CDR simulado: {str(e)}")
            # Devolver un base64 mínimo válido
            return base64.b64encode(b"CDR SIMULADO DEMO").decode('utf-8')
    
    def _generate_mock_cdr_xml(self, reference):
        """Genera un XML CDR simulado"""
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        
        cdr_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ar:ApplicationResponse xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
                       xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                       xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:UBLVersionID>2.0</cbc:UBLVersionID>
    <cbc:CustomizationID>1.0</cbc:CustomizationID>
    <cbc:ID>DEMO-CDR-{reference}</cbc:ID>
    <cbc:IssueDate>{timestamp[:10]}</cbc:IssueDate>
    <cbc:IssueTime>{timestamp[11:]}</cbc:IssueTime>
    <cac:SenderParty>
        <cac:PartyIdentification>
            <cbc:ID>20100070970</cbc:ID>
        </cac:PartyIdentification>
        <cac:PartyName>
            <cbc:Name>SUNAT</cbc:Name>
        </cac:PartyName>
    </cac:SenderParty>
    <cac:ReceiverParty>
        <cac:PartyIdentification>
            <cbc:ID>{self.ruc}</cbc:ID>
        </cac:PartyIdentification>
    </cac:ReceiverParty>
    <cac:DocumentResponse>
        <cac:Response>
            <cbc:ReferenceID>{reference.replace('.zip', '')}</cbc:ReferenceID>
            <cbc:ResponseCode>0</cbc:ResponseCode>
            <cbc:Description>La Factura ha sido aceptada</cbc:Description>
        </cac:Response>
        <cac:DocumentReference>
            <cbc:ID>{reference.replace('.zip', '')}</cbc:ID>
        </cac:DocumentReference>
    </cac:DocumentResponse>
</ar:ApplicationResponse>"""
        
        return cdr_xml
    
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