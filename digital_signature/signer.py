# digital_signature/signer.py - VERSIÓN CORREGIDA
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
        """Crea el elemento de firma XML-DSig"""
        # Calcular hash del documento (sin la firma)
        root_copy = self._remove_signature_elements(root)
        canonical_xml = self._canonicalize_xml(root_copy)
        document_hash = hashlib.sha256(canonical_xml.encode('utf-8')).digest()
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
        
        # DigestMethod
        digest_method = ET.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}DigestMethod')
        digest_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        
        # DigestValue
        digest_value_elem = ET.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}DigestValue')
        digest_value_elem.text = digest_value
        
        # Firmar el SignedInfo
        signed_info_xml = ET.tostring(signed_info, encoding='unicode')
        signed_info_hash = hashlib.sha1(signed_info_xml.encode('utf-8')).digest()
        
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
        """Canonicaliza el XML según C14N"""
        # Implementación básica de canonicalización
        xml_str = ET.tostring(element, encoding='unicode')
        
        # Remover espacios innecesarios y normalizar
        import re
        xml_str = re.sub(r'>\s+<', '><', xml_str)
        xml_str = re.sub(r'\s+', ' ', xml_str)
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
            signed_info_xml = ET.tostring(signed_info, encoding='unicode')
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