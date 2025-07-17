# ubl_converter/converter.py - VERSIÓN CORREGIDA PARA EVITAR ATRIBUTOS DUPLICADOS
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from decimal import Decimal
import os
import zipfile
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class UBLConverter:
    """Convertidor de objetos de negocio a XML UBL 2.1"""
    
    def __init__(self):
        self.namespaces = settings.UBL_CONFIG['NAMESPACES']
        self.version = settings.UBL_CONFIG['VERSION']
        self.customization_id = settings.UBL_CONFIG['CUSTOMIZATION_ID']
        
        # ✅ CORREGIDO: Registrar namespaces sin duplicados y de forma más limpia
        self._register_namespaces()
    
    def _register_namespaces(self):
        """Registra los namespaces de forma segura sin duplicados"""
        namespace_map = {
            '': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'sac': 'urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1',
            'qdt': 'urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2',
            'udt': 'urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2',
        }
        
        for prefix, uri in namespace_map.items():
            try:
                ET.register_namespace(prefix, uri)
            except Exception as e:
                logger.warning(f"No se pudo registrar namespace {prefix}: {e}")
    
    def convert_invoice_to_xml(self, invoice):
        """Convierte una factura/boleta a XML UBL 2.1"""
        try:
            logger.info(f"Iniciando conversión UBL para {invoice.full_document_name}")
            
            # Determinar el tipo de documento
            if invoice.document_type == '01':
                root_element = 'Invoice'
                default_ns = 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
            elif invoice.document_type == '03':
                root_element = 'Invoice'  # Boleta también usa Invoice en UBL
                default_ns = 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
            else:
                raise ValueError(f"Tipo de documento no soportado: {invoice.document_type}")
            
            # ✅ CORREGIDO: Crear elemento raíz de forma más limpia
            root = ET.Element(root_element)
            
            # ✅ CORREGIDO: Agregar namespaces sin duplicados usando un mapa limpio
            self._add_namespaces_to_root(root)
            
            # UBL Extensions (para firma digital)
            self._add_ubl_extensions(root)
            
            # Información básica del documento
            self._add_basic_document_info(root, invoice)
            
            # Información del emisor
            self._add_supplier_party(root, invoice.company)
            
            # Información del cliente
            self._add_customer_party(root, invoice.customer)
            
            # Líneas de detalle
            self._add_invoice_lines(root, invoice)
            
            # Totales e impuestos
            self._add_tax_totals(root, invoice)
            self._add_legal_monetary_total(root, invoice)
            
            # Convertir a string XML
            xml_str = self._prettify_xml(root)
            
            logger.info(f"Conversión UBL completada para {invoice.full_document_name}")
            return xml_str
            
        except Exception as e:
            logger.error(f"Error en conversión UBL para {invoice.full_document_name}: {str(e)}")
            raise
    
    def _add_namespaces_to_root(self, root):
        """Agrega namespaces al elemento raíz de forma controlada"""
        # ✅ CORREGIDO: Mapa único de namespaces sin duplicados
        namespace_declarations = [
            ('xmlns', 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'),
            ('xmlns:cac', 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'),
            ('xmlns:cbc', 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'),
            ('xmlns:ds', 'http://www.w3.org/2000/09/xmldsig#'),
            ('xmlns:ext', 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'),
            ('xmlns:sac', 'urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1'),
            ('xmlns:qdt', 'urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2'),
            ('xmlns:udt', 'urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2')
        ]
        
        # Agregar cada namespace una sola vez
        for attr_name, attr_value in namespace_declarations:
            if attr_name not in root.attrib:  # ✅ Verificar que no existe antes de agregar
                root.set(attr_name, attr_value)
    
    def _add_ubl_extensions(self, root):
        """Agrega UBL Extensions para la firma digital"""
        ext_elem = ET.SubElement(root, 'ext:UBLExtensions')
        
        # Extensión para información adicional SUNAT
        ubl_ext = ET.SubElement(ext_elem, 'ext:UBLExtension')
        ext_content = ET.SubElement(ubl_ext, 'ext:ExtensionContent')
        
        # Información adicional SUNAT
        additional_info = ET.SubElement(ext_content, 'sac:AdditionalInformation')
        
        # Extensión para firma digital (se agregará después del firmado)
        ubl_ext_sign = ET.SubElement(ext_elem, 'ext:UBLExtension')
        ext_content_sign = ET.SubElement(ubl_ext_sign, 'ext:ExtensionContent')
        # El contenido de la firma se agregará por el servicio de firma digital
    
    def _add_basic_document_info(self, root, invoice):
        """Agrega información básica del documento"""
        # UBL Version
        ubl_version = ET.SubElement(root, 'cbc:UBLVersionID')
        ubl_version.text = self.version
        
        # Customization ID
        customization = ET.SubElement(root, 'cbc:CustomizationID')
        customization.text = self.customization_id
        
        # Profile ID
        profile = ET.SubElement(root, 'cbc:ProfileID')
        # ✅ CORREGIDO: Agregar atributos sin duplicar
        profile_attrs = [
            ('schemeName', 'Tipo de Operacion'),
            ('schemeAgencyName', 'PE:SUNAT'),
            ('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo17')
        ]
        for attr_name, attr_value in profile_attrs:
            if attr_name not in profile.attrib:
                profile.set(attr_name, attr_value)
        profile.text = invoice.operation_type_code
        
        # ID del documento
        doc_id = ET.SubElement(root, 'cbc:ID')
        doc_id.text = invoice.document_id
        
        # Fecha de emisión
        issue_date = ET.SubElement(root, 'cbc:IssueDate')
        issue_date.text = invoice.issue_date.strftime('%Y-%m-%d')
        
        # Hora de emisión
        issue_time = ET.SubElement(root, 'cbc:IssueTime')
        issue_time.text = timezone.now().strftime('%H:%M:%S')
        
        # Fecha de vencimiento (si existe)
        if invoice.due_date:
            due_date = ET.SubElement(root, 'cbc:DueDate')
            due_date.text = invoice.due_date.strftime('%Y-%m-%d')
        
        # Tipo de documento
        doc_type = ET.SubElement(root, 'cbc:InvoiceTypeCode')
        # ✅ CORREGIDO: Agregar atributos sin duplicar
        doc_type_attrs = [
            ('listAgencyName', 'PE:SUNAT'),
            ('listName', 'Tipo de Documento'),
            ('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01')
        ]
        for attr_name, attr_value in doc_type_attrs:
            if attr_name not in doc_type.attrib:
                doc_type.set(attr_name, attr_value)
        doc_type.text = invoice.document_type
        
        # Observaciones
        if invoice.observations:
            note = ET.SubElement(root, 'cbc:Note')
            note.text = invoice.observations
        
        # Moneda
        currency = ET.SubElement(root, 'cbc:DocumentCurrencyCode')
        # ✅ CORREGIDO: Agregar atributos sin duplicar
        currency_attrs = [
            ('listID', 'ISO 4217 Alpha'),
            ('listName', 'Currency'),
            ('listAgencyName', 'United Nations Economic Commission for Europe')
        ]
        for attr_name, attr_value in currency_attrs:
            if attr_name not in currency.attrib:
                currency.set(attr_name, attr_value)
        currency.text = invoice.currency_code
    
    def _add_supplier_party(self, root, company):
        """Agrega información del proveedor (emisor)"""
        supplier_party = ET.SubElement(root, 'cac:AccountingSupplierParty')
        party = ET.SubElement(supplier_party, 'cac:Party')
        
        # Identificación del proveedor
        party_id = ET.SubElement(party, 'cac:PartyIdentification')
        id_elem = ET.SubElement(party_id, 'cbc:ID')
        # ✅ CORREGIDO: Agregar atributos sin duplicar
        id_attrs = [
            ('schemeID', '6'),
            ('schemeName', 'Documento de Identidad'),
            ('schemeAgencyName', 'PE:SUNAT'),
            ('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
        ]
        for attr_name, attr_value in id_attrs:
            if attr_name not in id_elem.attrib:
                id_elem.set(attr_name, attr_value)
        id_elem.text = company.ruc
        
        # Nombre del proveedor
        party_name = ET.SubElement(party, 'cac:PartyName')
        name_elem = ET.SubElement(party_name, 'cbc:Name')
        name_elem.text = company.trade_name or company.business_name
        
        # Nombre legal
        party_legal = ET.SubElement(party, 'cac:PartyLegalEntity')
        legal_name = ET.SubElement(party_legal, 'cbc:RegistrationName')
        legal_name.text = company.business_name
        
        # Dirección
        address = ET.SubElement(party_legal, 'cac:RegistrationAddress')
        
        address_id = ET.SubElement(address, 'cbc:ID')
        address_id_attrs = [
            ('schemeName', 'Ubigeos'),
            ('schemeAgencyName', 'PE:INEI')
        ]
        for attr_name, attr_value in address_id_attrs:
            if attr_name not in address_id.attrib:
                address_id.set(attr_name, attr_value)
        address_id.text = company.ubigeo or '150101'
        
        address_type = ET.SubElement(address, 'cbc:AddressTypeCode')
        address_type_attrs = [
            ('listAgencyName', 'PE:SUNAT'),
            ('listName', 'Establecimientos anexos')
        ]
        for attr_name, attr_value in address_type_attrs:
            if attr_name not in address_type.attrib:
                address_type.set(attr_name, attr_value)
        address_type.text = company.address_type_code
        
        city_name = ET.SubElement(address, 'cbc:CityName')
        city_name.text = company.province
        
        country_subentity = ET.SubElement(address, 'cbc:CountrySubentity')
        country_subentity.text = company.department
        
        district = ET.SubElement(address, 'cbc:District')
        district.text = company.district
        
        address_line = ET.SubElement(address, 'cac:AddressLine')
        line = ET.SubElement(address_line, 'cbc:Line')
        line.text = company.address
        
        country = ET.SubElement(address, 'cac:Country')
        country_code = ET.SubElement(country, 'cbc:IdentificationCode')
        country_attrs = [
            ('listID', 'ISO 3166-1'),
            ('listAgencyName', 'United Nations Economic Commission for Europe'),
            ('listName', 'Country')
        ]
        for attr_name, attr_value in country_attrs:
            if attr_name not in country_code.attrib:
                country_code.set(attr_name, attr_value)
        country_code.text = company.country_code
    
    def _add_customer_party(self, root, customer):
        """Agrega información del cliente"""
        customer_party = ET.SubElement(root, 'cac:AccountingCustomerParty')
        party = ET.SubElement(customer_party, 'cac:Party')
        
        # Identificación del cliente
        party_id = ET.SubElement(party, 'cac:PartyIdentification')
        id_elem = ET.SubElement(party_id, 'cbc:ID')
        # ✅ CORREGIDO: Agregar atributos sin duplicar
        customer_id_attrs = [
            ('schemeID', customer.document_type),
            ('schemeName', 'Documento de Identidad'),
            ('schemeAgencyName', 'PE:SUNAT'),
            ('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
        ]
        for attr_name, attr_value in customer_id_attrs:
            if attr_name not in id_elem.attrib:
                id_elem.set(attr_name, attr_value)
        id_elem.text = customer.document_number
        
        # Nombre del cliente
        party_legal = ET.SubElement(party, 'cac:PartyLegalEntity')
        legal_name = ET.SubElement(party_legal, 'cbc:RegistrationName')
        legal_name.text = customer.business_name
    
    def _add_invoice_lines(self, root, invoice):
        """Agrega las líneas de detalle de la factura"""
        for line in invoice.invoice_lines.all():
            invoice_line = ET.SubElement(root, 'cac:InvoiceLine')
            
            # Número de línea
            line_id = ET.SubElement(invoice_line, 'cbc:ID')
            line_id.text = str(line.line_number)
            
            # Cantidad
            quantity_elem = ET.SubElement(invoice_line, 'cbc:InvoicedQuantity')
            quantity_elem.text = str(line.quantity)
            # ✅ CORREGIDO: Agregar atributos sin duplicar
            quantity_attrs = [
                ('unitCode', line.unit_code),
                ('unitCodeListID', 'UN/ECE rec 20'),
                ('unitCodeListAgencyID', '6')
            ]
            for attr_name, attr_value in quantity_attrs:
                if attr_name not in quantity_elem.attrib:
                    quantity_elem.set(attr_name, attr_value)
            
            # Valor de línea
            line_amount = ET.SubElement(invoice_line, 'cbc:LineExtensionAmount')
            line_amount.set('currencyID', invoice.currency_code)
            line_amount.text = f"{line.line_extension_amount:.2f}"
            
            # Precio de referencia (para items gratuitos)
            if line.tax_category_code == 'Z' and line.reference_price > 0:
                pricing_ref = ET.SubElement(invoice_line, 'cac:PricingReference')
                alt_price = ET.SubElement(pricing_ref, 'cac:AlternativeConditionPrice')
                price_amount = ET.SubElement(alt_price, 'cbc:PriceAmount')
                price_amount.set('currencyID', invoice.currency_code)
                price_amount.text = f"{line.reference_price:.2f}"
                price_type = ET.SubElement(alt_price, 'cbc:PriceTypeCode')
                # ✅ CORREGIDO: Agregar atributos sin duplicar
                price_type_attrs = [
                    ('listName', 'Tipo de Precio'),
                    ('listAgencyName', 'PE:SUNAT'),
                    ('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16')
                ]
                for attr_name, attr_value in price_type_attrs:
                    if attr_name not in price_type.attrib:
                        price_type.set(attr_name, attr_value)
                price_type.text = '01'  # Precio unitario (incluye el IGV)
            
            # Información de impuestos por línea
            self._add_line_tax_totals(invoice_line, line, invoice.currency_code)
            
            # Información del item
            item = ET.SubElement(invoice_line, 'cac:Item')
            description = ET.SubElement(item, 'cbc:Description')
            description.text = line.description
            
            # Sellers item identification
            sellers_id = ET.SubElement(item, 'cac:SellersItemIdentification')
            sellers_id_code = ET.SubElement(sellers_id, 'cbc:ID')
            sellers_id_code.text = line.product_code
            
            # Clasificación del item
            commodity_class = ET.SubElement(item, 'cac:CommodityClassification')
            item_class_code = ET.SubElement(commodity_class, 'cbc:ItemClassificationCode')
            # ✅ CORREGIDO: Agregar atributos sin duplicar
            class_attrs = [
                ('listID', 'UNSPSC'),
                ('listAgencyName', 'GS1 US'),
                ('listName', 'Item Classification')
            ]
            for attr_name, attr_value in class_attrs:
                if attr_name not in item_class_code.attrib:
                    item_class_code.set(attr_name, attr_value)
            item_class_code.text = '10000000'  # Código genérico
            
            # Precio unitario
            price = ET.SubElement(invoice_line, 'cac:Price')
            price_amount = ET.SubElement(price, 'cbc:PriceAmount')
            price_amount.set('currencyID', invoice.currency_code)
            price_amount.text = f"{line.unit_price:.2f}"
    
    def _add_line_tax_totals(self, invoice_line, line, currency_code):
        """Agrega información de impuestos por línea"""
        tax_total = ET.SubElement(invoice_line, 'cac:TaxTotal')
        
        # Monto total de impuestos de la línea
        total_tax_amount = (line.igv_amount or 0) + (line.isc_amount or 0) + (line.icbper_amount or 0)
        tax_amount = ET.SubElement(tax_total, 'cbc:TaxAmount')
        tax_amount.set('currencyID', currency_code)
        tax_amount.text = f"{total_tax_amount:.2f}"
        
        # IGV
        if (line.igv_amount and line.igv_amount > 0) or line.tax_category_code in ['S', 'E', 'O']:
            self._add_tax_subtotal(tax_total, line, 'IGV', '1000', line.igv_amount or 0, line.igv_rate, currency_code)
        
        # ISC
        if line.isc_amount and line.isc_amount > 0:
            self._add_tax_subtotal(tax_total, line, 'ISC', '2000', line.isc_amount, line.isc_rate, currency_code)
        
        # ICBPER
        if line.icbper_amount and line.icbper_amount > 0:
            self._add_tax_subtotal(tax_total, line, 'ICBPER', '7152', line.icbper_amount, line.icbper_rate, currency_code)
    
    def _add_tax_subtotal(self, tax_total, line, tax_name, tax_id, amount, rate, currency_code):
        """Agrega un subtotal de impuesto"""
        tax_subtotal = ET.SubElement(tax_total, 'cac:TaxSubtotal')
        
        # Base imponible
        taxable_amount = ET.SubElement(tax_subtotal, 'cbc:TaxableAmount')
        taxable_amount.set('currencyID', currency_code)
        
        if tax_name == 'ICBPER':
            # Para ICBPER la base es la cantidad
            taxable_amount.text = f"{line.quantity:.2f}"
        else:
            # Para IGV e ISC la base es el valor de venta
            base = line.line_extension_amount if line.tax_category_code != 'Z' else (line.quantity * (line.reference_price or 0))
            taxable_amount.text = f"{base:.2f}"
        
        # Monto del impuesto
        tax_amount = ET.SubElement(tax_subtotal, 'cbc:TaxAmount')
        tax_amount.set('currencyID', currency_code)
        tax_amount.text = f"{amount:.2f}"
        
        # Categoría del impuesto
        tax_category = ET.SubElement(tax_subtotal, 'cac:TaxCategory')
        
        # Código de categoría
        tax_category_code = ET.SubElement(tax_category, 'cbc:ID')
        # ✅ CORREGIDO: Agregar atributos sin duplicar
        tax_cat_attrs = [
            ('schemeID', 'UN/ECE 5305'),
            ('schemeName', 'Tax Category Identifier'),
            ('schemeAgencyName', 'United Nations Economic Commission for Europe')
        ]
        for attr_name, attr_value in tax_cat_attrs:
            if attr_name not in tax_category_code.attrib:
                tax_category_code.set(attr_name, attr_value)
        tax_category_code.text = line.tax_category_code
        
        # Tasa del impuesto
        if tax_name != 'ICBPER':
            percent = ET.SubElement(tax_category, 'cbc:Percent')
            percent.text = f"{rate:.2f}"
        
        # Código de exoneración (si aplica)
        if line.tax_exemption_reason_code and line.tax_category_code in ['E', 'O']:
            exemption_reason = ET.SubElement(tax_category, 'cbc:TaxExemptionReasonCode')
            # ✅ CORREGIDO: Agregar atributos sin duplicar
            exemption_attrs = [
                ('listAgencyName', 'PE:SUNAT'),
                ('listName', 'Afectacion del IGV'),
                ('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07')
            ]
            for attr_name, attr_value in exemption_attrs:
                if attr_name not in exemption_reason.attrib:
                    exemption_reason.set(attr_name, attr_value)
            exemption_reason.text = line.tax_exemption_reason_code
        
        # Esquema de impuesto
        tax_scheme = ET.SubElement(tax_category, 'cac:TaxScheme')
        scheme_id = ET.SubElement(tax_scheme, 'cbc:ID')
        # ✅ CORREGIDO: Agregar atributos sin duplicar
        scheme_attrs = [
            ('schemeName', 'Codigo de tributos'),
            ('schemeAgencyName', 'PE:SUNAT'),
            ('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05')
        ]
        for attr_name, attr_value in scheme_attrs:
            if attr_name not in scheme_id.attrib:
                scheme_id.set(attr_name, attr_value)
        scheme_id.text = tax_id
        
        scheme_name = ET.SubElement(tax_scheme, 'cbc:Name')
        scheme_name.text = tax_name
        
        tax_type_code = ET.SubElement(tax_scheme, 'cbc:TaxTypeCode')
        tax_type_code.text = tax_name
    
    def _add_tax_totals(self, root, invoice):
        """Agrega los totales de impuestos del documento"""
        tax_total = ET.SubElement(root, 'cac:TaxTotal')
        
        # Monto total de impuestos
        total_tax_amount = invoice.igv_amount + invoice.isc_amount + invoice.icbper_amount
        tax_amount = ET.SubElement(tax_total, 'cbc:TaxAmount')
        tax_amount.set('currencyID', invoice.currency_code)
        tax_amount.text = f"{total_tax_amount:.2f}"
        
        # Subtotales por tipo de impuesto
        if invoice.igv_amount > 0:
            self._add_document_tax_subtotal(tax_total, invoice, 'IGV', '1000', invoice.igv_amount, 18.00, invoice.total_taxed_amount)
        
        if invoice.isc_amount > 0:
            self._add_document_tax_subtotal(tax_total, invoice, 'ISC', '2000', invoice.isc_amount, 0, invoice.total_taxed_amount)
        
        if invoice.icbper_amount > 0:
            # Para ICBPER necesitamos calcular la cantidad total de bolsas
            total_bags = sum(line.quantity for line in invoice.invoice_lines.filter(icbper_amount__gt=0))
            self._add_document_tax_subtotal(tax_total, invoice, 'ICBPER', '7152', invoice.icbper_amount, 0, total_bags)
    
    def _add_document_tax_subtotal(self, tax_total, invoice, tax_name, tax_id, amount, rate, base_amount):
        """Agrega subtotal de impuesto a nivel de documento"""
        tax_subtotal = ET.SubElement(tax_total, 'cac:TaxSubtotal')
        
        # Base imponible
        taxable_amount = ET.SubElement(tax_subtotal, 'cbc:TaxableAmount')
        taxable_amount.set('currencyID', invoice.currency_code)
        taxable_amount.text = f"{base_amount:.2f}"
        
        # Monto del impuesto
        tax_amount = ET.SubElement(tax_subtotal, 'cbc:TaxAmount')
        tax_amount.set('currencyID', invoice.currency_code)
        tax_amount.text = f"{amount:.2f}"
        
        # Categoría del impuesto
        tax_category = ET.SubElement(tax_subtotal, 'cac:TaxCategory')
        
        # Tasa del impuesto
        if tax_name != 'ICBPER' and rate > 0:
            percent = ET.SubElement(tax_category, 'cbc:Percent')
            percent.text = f"{rate:.2f}"
        
        # Esquema de impuesto
        tax_scheme = ET.SubElement(tax_category, 'cac:TaxScheme')
        scheme_id = ET.SubElement(tax_scheme, 'cbc:ID')
        scheme_id.text = tax_id
        scheme_name = ET.SubElement(tax_scheme, 'cbc:Name')
        scheme_name.text = tax_name
        tax_type_code = ET.SubElement(tax_scheme, 'cbc:TaxTypeCode')
        tax_type_code.text = tax_name
    
    def _add_legal_monetary_total(self, root, invoice):
        """Agrega los totales monetarios legales"""
        monetary_total = ET.SubElement(root, 'cac:LegalMonetaryTotal')
        
        # Valor de venta - operaciones inafectas
        if invoice.total_unaffected_amount > 0:
            unaffected_amount = ET.SubElement(monetary_total, 'cbc:TaxExclusiveAmount')
            unaffected_amount.set('currencyID', invoice.currency_code)
            unaffected_amount.text = f"{invoice.total_unaffected_amount:.2f}"
        
        # Valor de venta - operaciones exoneradas
        if invoice.total_exempt_amount > 0:
            exempt_amount = ET.SubElement(monetary_total, 'cbc:AllowanceTotalAmount')
            exempt_amount.set('currencyID', invoice.currency_code)
            exempt_amount.text = f"{invoice.total_exempt_amount:.2f}"
        
        # Valor de venta - operaciones gratuitas
        if invoice.total_free_amount > 0:
            free_amount = ET.SubElement(monetary_total, 'cbc:ChargeTotalAmount')
            free_amount.set('currencyID', invoice.currency_code)
            free_amount.text = f"{invoice.total_free_amount:.2f}"
        
        # Subtotal de venta
        line_extension_amount = ET.SubElement(monetary_total, 'cbc:LineExtensionAmount')
        line_extension_amount.set('currencyID', invoice.currency_code)
        subtotal = invoice.total_taxed_amount + invoice.total_unaffected_amount + invoice.total_exempt_amount
        line_extension_amount.text = f"{subtotal:.2f}"
        
        # Importe total de la venta
        payable_amount = ET.SubElement(monetary_total, 'cbc:PayableAmount')
        payable_amount.set('currencyID', invoice.currency_code)
        payable_amount.text = f"{invoice.total_amount:.2f}"
    
    def _prettify_xml(self, elem):
        """Formatea el XML para que sea legible"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        
        # Remover líneas vacías
        lines = [line for line in pretty.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def save_xml_to_file(self, xml_content, filename):
        """Guarda el XML en un archivo"""
        try:
            file_path = os.path.join(settings.MEDIA_ROOT, 'xml_files', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            logger.info(f"XML guardado en: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error guardando XML: {str(e)}")
            raise
    
    def create_zip_file(self, xml_file_path, zip_filename):
        """Crea un archivo ZIP con el XML"""
        try:
            zip_path = os.path.join(settings.MEDIA_ROOT, 'zip_files', zip_filename)
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(xml_file_path, os.path.basename(xml_file_path))
            
            logger.info(f"ZIP creado en: {zip_path}")
            return zip_path
            
        except Exception as e:
            logger.error(f"Error creando ZIP: {str(e)}")
            raise - operaciones gravadas
        if invoice.total_taxed_amount > 0:
            taxable_amount = ET.SubElement(monetary_total, 'cbc:TaxInclusiveAmount')
            taxable_amount.set('currencyID', invoice.currency_code)
            taxable_amount.text = f"{invoice.total_taxed_amount:.2f}"
        
        # Valor de venta