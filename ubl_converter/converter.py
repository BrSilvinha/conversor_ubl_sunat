# ubl_converter/converter.py
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
        
        # Registrar namespaces
        for prefix, uri in self.namespaces.items():
            if prefix.startswith('xmlns:'):
                ET.register_namespace(prefix[6:], uri)
            elif prefix == 'xmlns':
                ET.register_namespace('', uri)
    
    def convert_invoice_to_xml(self, invoice):
        """Convierte una factura/boleta a XML UBL 2.1"""
        try:
            logger.info(f"Iniciando conversión UBL para {invoice.full_document_name}")
            
            # Determinar el tipo de documento
            if invoice.document_type == '01':
                root_element = 'Invoice'
            elif invoice.document_type == '03':
                root_element = 'Invoice'  # Boleta también usa Invoice en UBL
            else:
                raise ValueError(f"Tipo de documento no soportado: {invoice.document_type}")
            
            # Crear elemento raíz
            root = ET.Element(root_element)
            
            # Agregar namespaces
            for prefix, uri in self.namespaces.items():
                if prefix == 'xmlns':
                    root.set(prefix, uri)
                else:
                    root.set(prefix, uri)
            
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
    
    def _add_ubl_extensions(self, root):
        """Agrega UBL Extensions para la firma digital"""
        ext_elem = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}UBLExtensions')
        
        # Extensión para información adicional SUNAT
        ubl_ext = ET.SubElement(ext_elem, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}UBLExtension')
        ext_content = ET.SubElement(ubl_ext, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ExtensionContent')
        
        # Aquí iría la información adicional SUNAT
        
        # Extensión para firma digital (se agregará después del firmado)
        ubl_ext_sign = ET.SubElement(ext_elem, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}UBLExtension')
        ext_content_sign = ET.SubElement(ubl_ext_sign, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ExtensionContent')
        # El contenido de la firma se agregará por el servicio de firma digital
    
    def _add_basic_document_info(self, root, invoice):
        """Agrega información básica del documento"""
        # UBL Version
        ubl_version = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UBLVersionID')
        ubl_version.text = self.version
        
        # Customization ID
        customization = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CustomizationID')
        customization.text = self.customization_id
        
        # Profile ID
        profile = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ProfileID')
        profile.set('schemeName', 'Tipo de Operacion')
        profile.set('schemeAgencyName', 'PE:SUNAT')
        profile.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo17')
        profile.text = invoice.operation_type_code
        
        # ID del documento
        doc_id = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        doc_id.text = invoice.document_id
        
        # Fecha de emisión
        issue_date = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate')
        issue_date.text = invoice.issue_date.strftime('%Y-%m-%d')
        
        # Hora de emisión
        issue_time = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueTime')
        issue_time.text = timezone.now().strftime('%H:%M:%S')
        
        # Fecha de vencimiento (si existe)
        if invoice.due_date:
            due_date = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DueDate')
            due_date.text = invoice.due_date.strftime('%Y-%m-%d')
        
        # Tipo de documento
        doc_type = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode')
        doc_type.set('listAgencyName', 'PE:SUNAT')
        doc_type.set('listName', 'Tipo de Documento')
        doc_type.set('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01')
        doc_type.text = invoice.document_type
        
        # Observaciones
        if invoice.observations:
            note = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Note')
            note.text = invoice.observations
        
        # Moneda
        currency = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DocumentCurrencyCode')
        currency.set('listID', 'ISO 4217 Alpha')
        currency.set('listName', 'Currency')
        currency.set('listAgencyName', 'United Nations Economic Commission for Europe')
        currency.text = invoice.currency_code
    
    def _add_supplier_party(self, root, company):
        """Agrega información del proveedor (emisor)"""
        supplier_party = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AccountingSupplierParty')
        party = ET.SubElement(supplier_party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Party')
        
        # Identificación del proveedor
        party_id = ET.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyIdentification')
        id_elem = ET.SubElement(party_id, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        id_elem.set('schemeID', '6')
        id_elem.set('schemeName', 'Documento de Identidad')
        id_elem.set('schemeAgencyName', 'PE:SUNAT')
        id_elem.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
        id_elem.text = company.ruc
        
        # Nombre del proveedor
        party_name = ET.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyName')
        name_elem = ET.SubElement(party_name, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')
        name_elem.text = company.trade_name or company.business_name
        
        # Nombre legal
        party_legal = ET.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyLegalEntity')
        legal_name = ET.SubElement(party_legal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName')
        legal_name.text = company.business_name
        
        # Dirección
        address = ET.SubElement(party_legal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}RegistrationAddress')
        
        address_id = ET.SubElement(address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        address_id.set('schemeName', 'Ubigeos')
        address_id.set('schemeAgencyName', 'PE:INEI')
        address_id.text = company.ubigeo or '150101'
        
        address_type = ET.SubElement(address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}AddressTypeCode')
        address_type.set('listAgencyName', 'PE:SUNAT')
        address_type.set('listName', 'Establecimientos anexos')
        address_type.text = company.address_type_code
        
        city_name = ET.SubElement(address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CityName')
        city_name.text = company.province
        
        country_subentity = ET.SubElement(address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CountrySubentity')
        country_subentity.text = company.department
        
        district = ET.SubElement(address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}District')
        district.text = company.district
        
        address_line = ET.SubElement(address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AddressLine')
        line = ET.SubElement(address_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Line')
        line.text = company.address
        
        country = ET.SubElement(address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Country')
        country_code = ET.SubElement(country, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IdentificationCode')
        country_code.set('listID', 'ISO 3166-1')
        country_code.set('listAgencyName', 'United Nations Economic Commission for Europe')
        country_code.set('listName', 'Country')
        country_code.text = company.country_code
    
    def _add_customer_party(self, root, customer):
        """Agrega información del cliente"""
        customer_party = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AccountingCustomerParty')
        party = ET.SubElement(customer_party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Party')
        
        # Identificación del cliente
        party_id = ET.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyIdentification')
        id_elem = ET.SubElement(party_id, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        id_elem.set('schemeID', customer.document_type)
        id_elem.set('schemeName', 'Documento de Identidad')
        id_elem.set('schemeAgencyName', 'PE:SUNAT')
        id_elem.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
        id_elem.text = customer.document_number
        
        # Nombre del cliente
        party_legal = ET.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyLegalEntity')
        legal_name = ET.SubElement(party_legal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName')
        legal_name.text = customer.business_name
    
    def _add_invoice_lines(self, root, invoice):
        """Agrega las líneas de detalle de la factura"""
        for line in invoice.invoice_lines.all():
            invoice_line = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine')
            
            # Número de línea
            line_id = ET.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
            line_id.text = str(line.line_number)
            
            # Cantidad
            quantity_elem = ET.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoicedQuantity')
            quantity_elem.text = str(line.quantity)
            
            # Valor de línea
            line_amount = ET.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount')
            line_amount.set('currencyID', invoice.currency_code)
            line_amount.text = f"{line.line_extension_amount:.2f}"
            
            # Precio de referencia (para items gratuitos)
            if line.tax_category_code == 'Z' and line.reference_price > 0:
                pricing_ref = ET.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PricingReference')
                alt_price = ET.SubElement(pricing_ref, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AlternativeConditionPrice')
                price_amount = ET.SubElement(alt_price, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount')
                price_amount.set('currencyID', invoice.currency_code)
                price_amount.text = f"{line.reference_price:.2f}"
                price_type = ET.SubElement(alt_price, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceTypeCode')
                price_type.set('listName', 'Tipo de Precio')
                price_type.set('listAgencyName', 'PE:SUNAT')
                price_type.set('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16')
                price_type.text = '01'  # Precio unitario (incluye el IGV)
            
            # Información de impuestos por línea
            self._add_line_tax_totals(invoice_line, line, invoice.currency_code)
            
            # Información del item
            item = ET.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Item')
            description = ET.SubElement(item, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Description')
            description.text = line.description
            
            # Sellers item identification
            sellers_id = ET.SubElement(item, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}SellersItemIdentification')
            sellers_id_code = ET.SubElement(sellers_id, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
            sellers_id_code.text = line.product_code
            
            # Clasificación del item
            commodity_class = ET.SubElement(item, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}CommodityClassification')
            item_class_code = ET.SubElement(commodity_class, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ItemClassificationCode')
            item_class_code.set('listID', 'UNSPSC')
            item_class_code.set('listAgencyName', 'GS1 US')
            item_class_code.set('listName', 'Item Classification')
            item_class_code.text = '10000000'  # Código genérico
            
            # Precio unitario
            price = ET.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Price')
            price_amount = ET.SubElement(price, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount')
            price_amount.set('currencyID', invoice.currency_code)
            price_amount.text = f"{line.unit_price:.2f}"
    
    def _add_line_tax_totals(self, invoice_line, line, currency_code):
        """Agrega información de impuestos por línea"""
        tax_total = ET.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal')
        
        # Monto total de impuestos de la línea
        total_tax_amount = line.igv_amount + line.isc_amount + line.icbper_amount
        tax_amount = ET.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
        tax_amount.set('currencyID', currency_code)
        tax_amount.text = f"{total_tax_amount:.2f}"
        
        # IGV
        if line.igv_amount > 0 or line.tax_category_code in ['S', 'E', 'O']:
            self._add_tax_subtotal(tax_total, line, 'IGV', '1000', line.igv_amount, line.igv_rate, currency_code)
        
        # ISC
        if line.isc_amount > 0:
            self._add_tax_subtotal(tax_total, line, 'ISC', '2000', line.isc_amount, line.isc_rate, currency_code)
        
        # ICBPER
        if line.icbper_amount > 0:
            self._add_tax_subtotal(tax_total, line, 'ICBPER', '7152', line.icbper_amount, line.icbper_rate, currency_code)
    
    def _add_tax_subtotal(self, tax_total, line, tax_name, tax_id, amount, rate, currency_code):
        """Agrega un subtotal de impuesto"""
        tax_subtotal = ET.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal')
        
        # Base imponible
        taxable_amount = ET.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount')
        taxable_amount.set('currencyID', currency_code)
        
        if tax_name == 'ICBPER':
            # Para ICBPER la base es la cantidad
            taxable_amount.text = f"{line.quantity:.2f}"
        else:
            # Para IGV e ISC la base es el valor de venta
            base = line.line_extension_amount if line.tax_category_code != 'Z' else (line.quantity * line.reference_price)
            taxable_amount.text = f"{base:.2f}"
        
        # Monto del impuesto
        tax_amount = ET.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
        tax_amount.set('currencyID', currency_code)
        tax_amount.text = f"{amount:.2f}"
        
        # Categoría del impuesto
        tax_category = ET.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory')
        
        # Código de categoría
        tax_category_code = ET.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        tax_category_code.set('schemeID', 'UN/ECE 5305')
        tax_category_code.set('schemeName', 'Tax Category Identifier')
        tax_category_code.set('schemeAgencyName', 'United Nations Economic Commission for Europe')
        tax_category_code.text = line.tax_category_code
        
        # Tasa del impuesto
        if tax_name != 'ICBPER':
            percent = ET.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent')
            percent.text = f"{rate:.2f}"
        
        # Código de exoneración (si aplica)
        if line.tax_exemption_reason_code and line.tax_category_code in ['E', 'O']:
            exemption_reason = ET.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxExemptionReasonCode')
            exemption_reason.set('listAgencyName', 'PE:SUNAT')
            exemption_reason.set('listName', 'Afectacion del IGV')
            exemption_reason.set('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07')
            exemption_reason.text = line.tax_exemption_reason_code
        
        # Esquema de impuesto
        tax_scheme = ET.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
        scheme_id = ET.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        scheme_id.set('schemeName', 'Codigo de tributos')
        scheme_id.set('schemeAgencyName', 'PE:SUNAT')
        scheme_id.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05')
        scheme_id.text = tax_id
        
        scheme_name = ET.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')
        scheme_name.text = tax_name
        
        tax_type_code = ET.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxTypeCode')
        tax_type_code.text = tax_name
    
    def _add_tax_totals(self, root, invoice):
        """Agrega los totales de impuestos del documento"""
        tax_total = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal')
        
        # Monto total de impuestos
        total_tax_amount = invoice.igv_amount + invoice.isc_amount + invoice.icbper_amount
        tax_amount = ET.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
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
        tax_subtotal = ET.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal')
        
        # Base imponible
        taxable_amount = ET.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount')
        taxable_amount.set('currencyID', invoice.currency_code)
        taxable_amount.text = f"{base_amount:.2f}"
        
        # Monto del impuesto
        tax_amount = ET.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
        tax_amount.set('currencyID', invoice.currency_code)
        tax_amount.text = f"{amount:.2f}"
        
        # Categoría del impuesto
        tax_category = ET.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory')
        
        # Tasa del impuesto
        if tax_name != 'ICBPER' and rate > 0:
            percent = ET.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent')
            percent.text = f"{rate:.2f}"
        
        # Esquema de impuesto
        tax_scheme = ET.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
        scheme_id = ET.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        scheme_id.text = tax_id
        scheme_name = ET.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')
        scheme_name.text = tax_name
        tax_type_code = ET.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxTypeCode')
        tax_type_code.text = tax_name
    
    def _add_legal_monetary_total(self, root, invoice):
        """Agrega los totales monetarios legales"""
        monetary_total = ET.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}LegalMonetaryTotal')
        
        # Valor de venta - operaciones gravadas
        if invoice.total_taxed_amount > 0:
            taxable_amount = ET.SubElement(monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxInclusiveAmount')
            taxable_amount.set('currencyID', invoice.currency_code)
            taxable_amount.text = f"{invoice.total_taxed_amount:.2f}"
        
        # Valor de venta - operaciones inafectas
        if invoice.total_unaffected_amount > 0:
            unaffected_amount = ET.SubElement(monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxExclusiveAmount')
            unaffected_amount.set('currencyID', invoice.currency_code)
            unaffected_amount.text = f"{invoice.total_unaffected_amount:.2f}"
        
        # Valor de venta - operaciones exoneradas
        if invoice.total_exempt_amount > 0:
            exempt_amount = ET.SubElement(monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}AllowanceTotalAmount')
            exempt_amount.set('currencyID', invoice.currency_code)
            exempt_amount.text = f"{invoice.total_exempt_amount:.2f}"
        
        # Valor de venta - operaciones gratuitas
        if invoice.total_free_amount > 0:
            free_amount = ET.SubElement(monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ChargeTotalAmount')
            free_amount.set('currencyID', invoice.currency_code)
            free_amount.text = f"{invoice.total_free_amount:.2f}"
        
        # Subtotal de venta
        line_extension_amount = ET.SubElement(monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount')
        line_extension_amount.set('currencyID', invoice.currency_code)
        subtotal = invoice.total_taxed_amount + invoice.total_unaffected_amount + invoice.total_exempt_amount
        line_extension_amount.text = f"{subtotal:.2f}"
        
        # Importe total de la venta
        payable_amount = ET.SubElement(monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PayableAmount')
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
            raiseset('unitCode', line.unit_code)
            quantity_elem.set('unitCodeListID', 'UN/ECE rec 20')
            quantity_elem.set('unitCodeListAgencyID', '6')
            raise