# digital_signature/signer.py - VERSIÓN CORREGIDA PARA HASH CONSISTENTE
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class XMLDigitalSigner:
    """Servicio de firma digital XML usando estándar XML-DSig"""
    
    def __init__(self, certificate_path=None, certificate_password=None):
        self.certificate_path = certificate_path or settings.SUNAT_CONFIG['CERTIFICATE_PATH']
        self.certificate_password = certificate_password or settings.SUNAT_CONFIG['CERTIFICATE_PASSWORD']
        self.private_key = None
        self.certificate = None
        self.load_certificate()
    
    def load_certificate(self):
        """Carga el certificado digital y la clave privada"""
        try:
            if not os.path.exists(self.certificate_path):
                raise FileNotFoundError(f"Certificado no encontrado: {self.certificate_path}")
            
            logger.info(f"Cargando certificado desde: {self.certificate_path}")
            
            # Leer el archivo PKCS#12 (.pfx)
            with open(self.certificate_path, 'rb') as f:
                pkcs12_data = f.read()
            
            # Cargar el certificado y clave privada
            from cryptography.hazmat.primitives.serialization import pkcs12
            
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                pkcs12_data, 
                self.certificate_password.encode('utf-8'),
                backend=default_backend()
            )
            
            self.private_key = private_key
            self.certificate = certificate
            
            # Validar que el certificado no esté expirado
            if certificate.not_valid_after < datetime.now():
                raise ValueError("El certificado ha expirado")
            
            logger.info("Certificado cargado exitosamente")
            
        except Exception as e:
            logger.error(f"Error cargando certificado: {str(e)}")
            raise
    
    def sign_xml(self, xml_content, document_id=None):
        """Firma un documento XML usando XML-DSig"""
        try:
            logger.info(f"Iniciando firma digital para documento: {document_id}")
            
            # Parsear el XML
            root = ET.fromstring(xml_content)
            
            # Buscar el elemento UBLExtension para la firma
            namespaces = {
                'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
                'ds': 'http://www.w3.org/2000/09/xmldsig#'
            }
            
            # Encontrar el UBLExtension vacío para la firma
            extensions = root.findall('.//ext:UBLExtensions/ext:UBLExtension', namespaces)
            signature_extension = None
            
            for ext in extensions:
                content = ext.find('ext:ExtensionContent', namespaces)
                if content is not None and len(content) == 0:  # ExtensionContent vacío
                    signature_extension = content
                    break
            
            if signature_extension is None:
                raise ValueError("No se encontró UBLExtension para la firma")
            
            # Generar la firma
            signature_elem = self._create_signature_element(root, document_id)
            signature_extension.append(signature_elem)
            
            # Convertir de vuelta a string
            signed_xml = ET.tostring(root, encoding='unicode')
            
            # Formatear el XML
            reparsed = minidom.parseString(signed_xml)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            # Limpiar líneas vacías
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            final_xml = '\n'.join(lines)
            
            logger.info(f"Firma digital completada para documento: {document_id}")
            return final_xml
            
        except Exception as e:
            logger.error(f"Error en firma digital para documento {document_id}: {str(e)}")
            raise
    
    def _create_signature_element(self, root, document_id):
        """Crea el elemento de firma XML-DSig - VERSIÓN CORREGIDA"""
        # ✅ CORREGIDO: Usar SHA-1 consistentemente (estándar para UBL/SUNAT)
        root_copy = self._remove_signature_elements(root)
        canonical_xml = self._canonicalize_xml(root_copy)
        
        # ✅ USAR SHA-1 para el digest (compatible con SUNAT)
        document_hash = hashlib.sha1(canonical_xml.encode('utf-8')).digest()
        digest_value = base64.b64encode(document_hash).decode('utf-8')
        
        # Crear elemento Signature
        signature = ET.Element('{http://www.w3.org/2000/09/xmldsig#}Signature')
        signature.set('Id', f'SignatureKG')
        
        # SignedInfo
        signed_info = ET.SubElement(signature, '{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
        
        # CanonicalizationMethod
        canon_method = ET.SubElement(signed_info, '{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod')
        canon_method.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        
        # SignatureMethod
        sig_method = ET.SubElement(signed_info, '{http://www.w3.org/2000/09/xmldsig#}SignatureMethod')
        sig_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        
        # Reference
        reference = ET.SubElement(signed_info, '{http://www.w3.org/2000/09/xmldsig#}Reference')
        reference.set('URI', '')
        
        # Transforms
        transforms = ET.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}Transforms')
        transform = ET.SubElement(transforms, '{http://www.w3.org/2000/09/xmldsig#}Transform')
        transform.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')
        
        # DigestMethod - ✅ CORREGIDO: Usar SHA-1 consistentemente
        digest_method = ET.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}DigestMethod')
        digest_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        
        # DigestValue
        digest_value_elem = ET.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}DigestValue')
        digest_value_elem.text = digest_value
        
        # ✅ CORREGIDO: Canonicalizar SignedInfo correctamente antes de firmar
        signed_info_xml = self._canonicalize_element(signed_info)
        signed_info_hash = hashlib.sha1(signed_info_xml.encode('utf-8')).digest()
        
        # Firmar el hash del SignedInfo
        signature_value = self.private_key.sign(
            signed_info_hash,
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        
        # SignatureValue
        sig_value = ET.SubElement(signature, '{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        sig_value.text = base64.b64encode(signature_value).decode('utf-8')
        
        # KeyInfo
        key_info = ET.SubElement(signature, '{http://www.w3.org/2000/09/xmldsig#}KeyInfo')
        x509_data = ET.SubElement(key_info, '{http://www.w3.org/2000/09/xmldsig#}X509Data')
        x509_cert = ET.SubElement(x509_data, '{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
        
        # Agregar el certificado
        cert_der = self.certificate.public_bytes(serialization.Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode('utf-8')
        x509_cert.text = cert_b64
        
        return signature
    
    def _remove_signature_elements(self, root):
        """Remueve elementos de firma para el cálculo del hash"""
        # Crear una copia del elemento root
        root_copy = ET.fromstring(ET.tostring(root))
        
        # Remover elementos de firma existentes
        signatures = root_copy.findall('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
        for sig in signatures:
            parent = root_copy.find('.//' + sig.tag + '/..')
            if parent is not None:
                parent.remove(sig)
        
        return root_copy
    
    def _canonicalize_xml(self, element):
        """Canonicaliza el XML según C14N - VERSIÓN MEJORADA"""
        # Convertir a string sin declaración XML
        xml_str = ET.tostring(element, encoding='unicode')
        
        # Normalización básica C14N
        import re
        
        # Remover espacios entre elementos
        xml_str = re.sub(r'>\s+<', '><', xml_str)
        
        # Normalizar espacios en atributos
        xml_str = re.sub(r'\s+', ' ', xml_str)
        
        # Remover espacios al inicio y final
        xml_str = xml_str.strip()
        
        return xml_str
    
    def _canonicalize_element(self, element):
        """Canonicaliza un elemento específico"""
        # Para SignedInfo, usar canonicalización más estricta
        xml_str = ET.tostring(element, encoding='unicode')
        
        # Eliminar espacios y saltos de línea entre elementos
        import re
        xml_str = re.sub(r'>\s+<', '><', xml_str)
        xml_str = re.sub(r'\n\s*', '', xml_str)
        xml_str = xml_str.strip()
        
        return xml_str
    
    def verify_signature(self, signed_xml):
        """Verifica la firma digital de un XML"""
        try:
            root = ET.fromstring(signed_xml)
            
            # Buscar el elemento Signature
            signature = root.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
            if signature is None:
                return False, "No se encontró firma en el documento"
            
            # Extraer SignatureValue
            sig_value_elem = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
            if sig_value_elem is None:
                return False, "No se encontró SignatureValue"
            
            signature_value = base64.b64decode(sig_value_elem.text)
            
            # Extraer certificado
            cert_elem = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
            if cert_elem is None:
                return False, "No se encontró certificado"
            
            cert_der = base64.b64decode(cert_elem.text)
            certificate = x509.load_der_x509_certificate(cert_der, default_backend())
            
            # Verificar que el certificado no esté expirado
            if certificate.not_valid_after < datetime.now():
                return False, "El certificado ha expirado"
            
            # Extraer SignedInfo para verificación
            signed_info = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
            if signed_info is None:
                return False, "No se encontró SignedInfo"
            
            # Calcular hash del SignedInfo
            signed_info_xml = self._canonicalize_element(signed_info)
            signed_info_hash = hashlib.sha1(signed_info_xml.encode('utf-8')).digest()
            
            # Verificar la firma
            public_key = certificate.public_key()
            try:
                public_key.verify(
                    signature_value,
                    signed_info_hash,
                    padding.PKCS1v15(),
                    hashes.SHA1()
                )
                return True, "Firma válida"
            except Exception as e:
                return False, f"Firma inválida: {str(e)}"
                
        except Exception as e:
            return False, f"Error verificando firma: {str(e)}"
    
    def extract_signature_info(self, signed_xml):
        """Extrae información detallada de la firma para mostrar en el frontend"""
        try:
            root = ET.fromstring(signed_xml)
            
            # Buscar el elemento Signature
            signature = root.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
            if signature is None:
                return None
            
            signature_info = {
                'signature_found': True,
                'signature_id': signature.get('Id', 'N/A'),
                'algorithms': {},
                'certificate_info': {},
                'digest_info': {},
                'signature_value': None
            }
            
            # Extraer algoritmos
            canon_method = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod')
            if canon_method is not None:
                signature_info['algorithms']['canonicalization'] = canon_method.get('Algorithm', 'N/A')
            
            sig_method = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureMethod')
            if sig_method is not None:
                signature_info['algorithms']['signature'] = sig_method.get('Algorithm', 'N/A')
            
            digest_method = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}DigestMethod')
            if digest_method is not None:
                signature_info['algorithms']['digest'] = digest_method.get('Algorithm', 'N/A')
            
            # Extraer valor del digest
            digest_value = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}DigestValue')
            if digest_value is not None:
                signature_info['digest_info']['value'] = digest_value.text[:50] + '...' if len(digest_value.text) > 50 else digest_value.text
            
            # Extraer SignatureValue
            sig_value_elem = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
            if sig_value_elem is not None:
                sig_text = sig_value_elem.text
                signature_info['signature_value'] = sig_text[:50] + '...' if len(sig_text) > 50 else sig_text
            
            # Extraer información del certificado
            cert_elem = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
            if cert_elem is not None:
                try:
                    cert_der = base64.b64decode(cert_elem.text)
                    certificate = x509.load_der_x509_certificate(cert_der, default_backend())
                    
                    subject = certificate.subject
                    issuer = certificate.issuer
                    
                    # Extraer RUC del subject
                    ruc = None
                    for attribute in subject:
                        if attribute.oid._name == 'organizationalUnitName':
                            ruc = attribute.value
                            break
                    
                    signature_info['certificate_info'] = {
                        'subject': str(subject),
                        'issuer': str(issuer),
                        'not_valid_before': certificate.not_valid_before.strftime('%Y-%m-%d %H:%M:%S'),
                        'not_valid_after': certificate.not_valid_after.strftime('%Y-%m-%d %H:%M:%S'),
                        'serial_number': str(certificate.serial_number),
                        'ruc': ruc,
                        'is_valid': certificate.not_valid_after > datetime.now()
                    }
                except Exception as e:
                    signature_info['certificate_info']['error'] = f"Error procesando certificado: {str(e)}"
            
            return signature_info
            
        except Exception as e:
            return {
                'signature_found': False,
                'error': f"Error extrayendo información de firma: {str(e)}"
            }
    
    def get_certificate_info(self):
        """Obtiene información del certificado cargado"""
        if not self.certificate:
            return None
            
        try:
            subject = self.certificate.subject
            issuer = self.certificate.issuer
            
            # Extraer RUC del subject
            ruc = None
            for attribute in subject:
                if attribute.oid._name == 'organizationalUnitName':
                    ruc = attribute.value
                    break
            
            return {
                'subject': str(subject),
                'issuer': str(issuer),
                'not_valid_before': self.certificate.not_valid_before,
                'not_valid_after': self.certificate.not_valid_after,
                'serial_number': str(self.certificate.serial_number),
                'ruc': ruc,
                'is_valid': self.certificate.not_valid_after > datetime.now()
            }
        except Exception as e:
            logger.error(f"Error obteniendo información del certificado: {str(e)}")
            return None