# sunat_integration/client.py - VERSIÓN COMPLETA
import os
import base64
import zipfile
import tempfile
from django.conf import settings
from zeep import Client, Settings as ZeepSettings
from zeep.wsse.username import UsernameToken
from zeep.exceptions import Fault, TransportError
import logging

logger = logging.getLogger(__name__)

class SUNATWebServiceClient:
    """Cliente para los Web Services de SUNAT"""
    
    def __init__(self):
        self.config = settings.SUNAT_CONFIG
        self.use_beta = self.config['USE_BETA']
        self.ruc = self.config['RUC']
        self.username = self.config['USERNAME'] 
        self.password = self.config['PASSWORD']
        
        # URL del servicio según ambiente
        if self.use_beta:
            self.wsdl_url = self.config['BETA_URL']
            logger.info("Usando ambiente BETA de SUNAT")
        else:
            self.wsdl_url = self.config['PRODUCTION_URL']
            logger.info("Usando ambiente PRODUCCIÓN de SUNAT")
        
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente SOAP"""
        try:
            # Configuración de Zeep
            zeep_settings = ZeepSettings(
                strict=False,
                xml_huge_tree=True,
                force_https=False
            )
            
            # Crear cliente SOAP
            self.client = Client(self.wsdl_url, settings=zeep_settings)
            
            # Configurar autenticación WS-Security
            # Para SUNAT: username = RUC + USERNAME, password = PASSWORD
            auth_username = f"{self.ruc}{self.username}"
            self.client.wsse = UsernameToken(auth_username, self.password)
            
            logger.info(f"Cliente SUNAT inicializado correctamente: {self.wsdl_url}")
            
        except Exception as e:
            logger.error(f"Error inicializando cliente SUNAT: {str(e)}")
            raise
    
    def send_bill(self, zip_file_path, filename):
        """
        Envía una factura/boleta a SUNAT (método síncrono)
        
        Args:
            zip_file_path: Ruta al archivo ZIP
            filename: Nombre del archivo
            
        Returns:
            dict: Respuesta de SUNAT con CDR
        """
        try:
            logger.info(f"Enviando documento a SUNAT: {filename}")
            
            # Leer archivo ZIP
            with open(zip_file_path, 'rb') as f:
                zip_content = f.read()
            
            # Codificar en base64
            zip_base64 = base64.b64encode(zip_content).decode('utf-8')
            
            # Llamar al servicio sendBill
            response = self.client.service.sendBill(
                fileName=filename,
                contentFile=zip_base64
            )
            
            # La respuesta de sendBill es un ZIP con el CDR
            if response:
                # Decodificar la respuesta
                cdr_zip_content = base64.b64decode(response)
                
                # Guardar CDR temporalmente para extraer información
                cdr_info = self._extract_cdr_info(cdr_zip_content, filename)
                
                logger.info(f"Documento enviado exitosamente: {filename}")
                
                return {
                    'status': 'success',
                    'response_type': 'cdr',
                    'cdr_content': response,  # CDR en base64
                    'cdr_info': cdr_info,
                    'filename': filename
                }
            else:
                raise Exception("No se recibió respuesta de SUNAT")
                
        except Fault as e:
            # Error SOAP específico
            error_msg = f"Error SOAP de SUNAT: {str(e)}"
            logger.error(f"Error SOAP enviando documento {filename}: {str(e)}")
            return {
                'status': 'error',
                'error_message': error_msg,
                'error_type': 'soap_fault',
                'filename': filename
            }
        except TransportError as e:
            # Error de transporte (conexión, autenticación, etc.)
            error_msg = f"Error de conexión con SUNAT: {str(e)}"
            logger.error(f"Error de transporte enviando documento {filename}: {str(e)}")
            return {
                'status': 'error',
                'error_message': error_msg,
                'error_type': 'transport_error',
                'filename': filename
            }
        except Exception as e:
            logger.error(f"Error enviando documento {filename}: {str(e)}")
            return {
                'status': 'error',
                'error_message': str(e),
                'error_type': 'general_error',
                'filename': filename
            }
    
    def send_summary(self, zip_file_path, filename):
        """
        Envía resumen diario o comunicación de baja (método asíncrono)
        
        Args:
            zip_file_path: Ruta al archivo ZIP
            filename: Nombre del archivo
            
        Returns:
            dict: Respuesta de SUNAT con ticket
        """
        try:
            logger.info(f"Enviando resumen a SUNAT: {filename}")
            
            # Leer archivo ZIP
            with open(zip_file_path, 'rb') as f:
                zip_content = f.read()
            
            # Codificar en base64
            zip_base64 = base64.b64encode(zip_content).decode('utf-8')
            
            # Llamar al servicio sendSummary
            ticket = self.client.service.sendSummary(
                fileName=filename,
                contentFile=zip_base64
            )
            
            if ticket:
                logger.info(f"Resumen enviado exitosamente: {filename}, Ticket: {ticket}")
                
                return {
                    'status': 'success',
                    'response_type': 'ticket',
                    'ticket': ticket,
                    'filename': filename
                }
            else:
                raise Exception("No se recibió ticket de SUNAT")
                
        except Fault as e:
            error_msg = f"Error SOAP de SUNAT: {str(e)}"
            logger.error(f"Error SOAP enviando resumen {filename}: {str(e)}")
            return {
                'status': 'error',
                'error_message': error_msg,
                'error_type': 'soap_fault',
                'filename': filename
            }
        except TransportError as e:
            error_msg = f"Error de conexión con SUNAT: {str(e)}"
            logger.error(f"Error de transporte enviando resumen {filename}: {str(e)}")
            return {
                'status': 'error',
                'error_message': error_msg,
                'error_type': 'transport_error',
                'filename': filename
            }
        except Exception as e:
            logger.error(f"Error enviando resumen {filename}: {str(e)}")
            return {
                'status': 'error',
                'error_message': str(e),
                'error_type': 'general_error',
                'filename': filename
            }
    
    def get_status(self, ticket):
        """
        Consulta el estado de procesamiento usando ticket
        
        Args:
            ticket: Ticket devuelto por sendSummary
            
        Returns:
            dict: Estado del procesamiento
        """
        try:
            logger.info(f"Consultando estado de ticket: {ticket}")
            
            # Llamar al servicio getStatus
            response = self.client.service.getStatus(ticket=ticket)
            
            if response:
                status_code = response.statusCode if hasattr(response, 'statusCode') else None
                content = response.content if hasattr(response, 'content') else None
                
                logger.info(f"Estado obtenido para ticket {ticket}: {status_code}")
                
                result = {
                    'status': 'success',
                    'ticket': ticket,
                    'status_code': status_code,
                    'content': content
                }
                
                # Interpretar el estado
                if status_code == '0':
                    result['processing_status'] = 'completed'
                    result['description'] = 'Procesado correctamente'
                    if content:
                        # Extraer información del CDR
                        cdr_zip_content = base64.b64decode(content)
                        result['cdr_info'] = self._extract_cdr_info(cdr_zip_content, ticket)
                elif status_code == '98':
                    result['processing_status'] = 'processing'
                    result['description'] = 'En proceso'
                elif status_code == '99':
                    result['processing_status'] = 'error'
                    result['description'] = 'Procesado con errores'
                    if content:
                        # Extraer información del error
                        error_zip_content = base64.b64decode(content)
                        result['error_info'] = self._extract_error_info(error_zip_content)
                else:
                    result['processing_status'] = 'unknown'
                    result['description'] = f'Estado desconocido: {status_code}'
                
                return result
            else:
                raise Exception("No se recibió respuesta de SUNAT")
                
        except Exception as e:
            logger.error(f"Error consultando estado del ticket {ticket}: {str(e)}")
            return {
                'status': 'error',
                'error_message': str(e),
                'ticket': ticket
            }
    
    def get_status_cdr(self, ruc, document_type, series, number):
        """
        Consulta CDR de un documento específico
        
        Args:
            ruc: RUC del emisor
            document_type: Tipo de documento (01, 03, 07, 08)
            series: Serie del documento
            number: Número del documento
            
        Returns:
            dict: CDR del documento
        """
        try:
            logger.info(f"Consultando CDR: {ruc}-{document_type}-{series}-{number}")
            
            response = self.client.service.getStatusCdr(
                rucComprobante=ruc,
                tipoComprobante=document_type,
                serieComprobante=series,
                numeroComprobante=str(number)
            )
            
            if response:
                status_code = response.statusCode if hasattr(response, 'statusCode') else None
                content = response.content if hasattr(response, 'content') else None
                status_message = response.statusMessage if hasattr(response, 'statusMessage') else None
                
                logger.info(f"CDR obtenido: {status_code} - {status_message}")
                
                result = {
                    'status': 'success',
                    'status_code': status_code,
                    'status_message': status_message,
                    'content': content,
                    'document_id': f"{series}-{number}"
                }
                
                if content and status_code in ['0001', '0002', '0003']:
                    # Documento encontrado, extraer información del CDR
                    cdr_zip_content = base64.b64decode(content)
                    result['cdr_info'] = self._extract_cdr_info(cdr_zip_content, f"{ruc}-{document_type}-{series}-{number}")
                
                return result
            else:
                raise Exception("No se recibió respuesta de SUNAT")
                
        except Exception as e:
            logger.error(f"Error consultando CDR: {str(e)}")
            return {
                'status': 'error',
                'error_message': str(e)
            }
    
    def _extract_cdr_info(self, cdr_zip_content, reference):
        """Extrae información del CDR desde un ZIP"""
        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                temp_zip.write(cdr_zip_content)
                temp_zip_path = temp_zip.name
            
            # Extraer contenido del ZIP
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                if file_list:
                    # Leer el primer archivo XML del ZIP
                    xml_filename = file_list[0]
                    with zip_ref.open(xml_filename) as xml_file:
                        xml_content = xml_file.read().decode('utf-8')
                    
                    # Parsear XML para extraer información relevante
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(xml_content)
                    
                    # Namespaces comunes para CDR
                    namespaces = {
                        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
                        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
                    }
                    
                    # Extraer información básica
                    cdr_info = {
                        'xml_filename': xml_filename,
                        'response_code': None,
                        'response_description': None,
                        'document_reference': None,
                        'issue_date': None,
                        'notes': []
                    }
                    
                    # ID del proceso
                    cdr_id = root.find('.//cbc:ID', namespaces)
                    if cdr_id is not None:
                        cdr_info['process_id'] = cdr_id.text
                    
                    # Fecha de emisión
                    issue_date = root.find('.//cbc:IssueDate', namespaces)
                    if issue_date is not None:
                        cdr_info['issue_date'] = issue_date.text
                    
                    # Respuesta del documento
                    response = root.find('.//cac:DocumentResponse/cac:Response', namespaces)
                    if response is not None:
                        ref_id = response.find('.//cbc:ReferenceID', namespaces)
                        if ref_id is not None:
                            cdr_info['document_reference'] = ref_id.text
                        
                        resp_code = response.find('.//cbc:ResponseCode', namespaces)
                        if resp_code is not None:
                            cdr_info['response_code'] = resp_code.text
                        
                        description = response.find('.//cbc:Description', namespaces)
                        if description is not None:
                            cdr_info['response_description'] = description.text
                    
                    # Notas adicionales
                    notes = root.findall('.//cbc:Note', namespaces)
                    for note in notes:
                        if note.text:
                            cdr_info['notes'].append(note.text)
                    
                    # Limpiar archivo temporal
                    os.unlink(temp_zip_path)
                    
                    return cdr_info
            
        except Exception as e:
            logger.error(f"Error extrayendo información del CDR para {reference}: {str(e)}")
            return {'error': str(e)}
    
    def _extract_error_info(self, error_zip_content):
        """Extrae información de errores desde un ZIP"""
        try:
            # Similar al método anterior pero enfocado en errores
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                temp_zip.write(error_zip_content)
                temp_zip_path = temp_zip.name
            
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                if file_list:
                    xml_filename = file_list[0]
                    with zip_ref.open(xml_filename) as xml_file:
                        xml_content = xml_file.read().decode('utf-8')
                    
                    # Retornar contenido XML crudo para análisis posterior
                    os.unlink(temp_zip_path)
                    
                    return {
                        'xml_filename': xml_filename,
                        'xml_content': xml_content
                    }
            
        except Exception as e:
            logger.error(f"Error extrayendo información de error: {str(e)}")
            return {'error': str(e)}
    
    def test_connection(self):
        """Prueba la conexión con SUNAT"""
        try:
            # Intentar obtener información del WSDL
            operations = list(self.client.service.__dict__.keys())
            logger.info(f"Conexión exitosa. Operaciones disponibles: {operations}")
            
            return {
                'status': 'success',
                'message': 'Conexión exitosa con SUNAT',
                'operations': operations,
                'environment': 'BETA' if self.use_beta else 'PRODUCCIÓN',
                'wsdl_url': self.wsdl_url
            }
            
        except TransportError as e:
            # Error de autenticación o conexión
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                logger.warning(f"Error de autenticación SUNAT: {str(e)}")
                return {
                    'status': 'warning',
                    'message': 'Error de autenticación con SUNAT (normal con credenciales de prueba)',
                    'error_details': error_msg,
                    'environment': 'BETA' if self.use_beta else 'PRODUCCIÓN',
                    'suggestion': 'Verifica las credenciales o usa credenciales válidas para producción'
                }
            else:
                logger.error(f"Error de conexión SUNAT: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'Error de conexión: {str(e)}',
                    'environment': 'BETA' if self.use_beta else 'PRODUCCIÓN'
                }
        except Exception as e:
            logger.error(f"Error probando conexión: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error inesperado: {str(e)}',
                'environment': 'BETA' if self.use_beta else 'PRODUCCIÓN'
            }