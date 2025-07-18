# ubl_converter/models.py - VERSIÓN COMPLETA CORREGIDA
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid
from core.models import TimeStampedModel, Company, Customer, Product, ProcessingStatus

class Invoice(TimeStampedModel):
    """Modelo para Facturas y Boletas de Venta"""
    DOCUMENT_TYPE_CHOICES = [
        ('01', 'FACTURA'),
        ('03', 'BOLETA DE VENTA'),
    ]

    CURRENCY_CHOICES = [
        ('PEN', 'NUEVOS SOLES'),
        ('USD', 'DOLARES AMERICANOS'),
        ('EUR', 'EUROS'),
    ]

    OPERATION_TYPE_CHOICES = [
        ('0101', 'VENTA INTERNA'),
        ('0112', 'VENTA INTERNA - ANTICIPOS'),
        ('0200', 'EXPORTACIÓN'),
        ('0401', 'VENTA INTERNA NO DOMICILIADOS'),
    ]

    # Identificación
    correlation_id = models.UUIDField(default=uuid.uuid4, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoices')
    document_type = models.CharField(max_length=2, choices=DOCUMENT_TYPE_CHOICES)
    series = models.CharField(max_length=4)
    number = models.PositiveIntegerField()
    
    # Fechas
    issue_date = models.DateField(verbose_name="Fecha de Emisión")
    due_date = models.DateField(blank=True, null=True, verbose_name="Fecha de Vencimiento")
    
    # Cliente
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    
    # Configuración
    currency_code = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='PEN')
    operation_type_code = models.CharField(max_length=4, choices=OPERATION_TYPE_CHOICES, default='0101')
    
    # Totales
    total_taxed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Operaciones Gravadas")
    total_unaffected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Operaciones Inafectas")
    total_exempt_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Operaciones Exoneradas")
    total_free_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Operaciones Gratuitas")
    
    # Impuestos
    igv_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="IGV")
    isc_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="ISC")
    icbper_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="ICBPER")
    
    # Otros cargos/descuentos
    total_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Descuentos")
    total_charge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Cargos")
    
    # Percepción/Retención
    perception_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Monto de Percepción")
    perception_base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Base de Percepción")
    perception_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Porcentaje de Percepción")
    perception_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Código de Percepción")
    
    # Total final
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Importe Total")
    
    # Información adicional
    observations = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Estado de procesamiento
    status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING)
    
    # Archivos generados
    xml_file = models.CharField(max_length=500, blank=True, null=True)
    zip_file = models.CharField(max_length=500, blank=True, null=True)
    cdr_file = models.CharField(max_length=500, blank=True, null=True)
    
    # SUNAT Response
    sunat_ticket = models.CharField(max_length=50, blank=True, null=True)
    sunat_response_code = models.CharField(max_length=10, blank=True, null=True)
    sunat_response_description = models.TextField(blank=True, null=True)
    
    @property
    def document_id(self):
        """Retorna el ID del documento con formato serie-número"""
        return f"{self.series}-{str(self.number).zfill(8)}"
    
    @property
    def full_document_name(self):
        """Retorna el nombre completo del documento: RUC-TIPO-SERIE-NUMERO"""
        return f"{self.company.ruc}-{self.document_type}-{self.document_id}"
    
    @classmethod
    def get_next_number(cls, company, document_type, series):
        """
        Obtiene el siguiente número disponible para una serie específica
        """
        existing_invoice = cls.objects.filter(
            company=company,
            document_type=document_type,
            series=series
        ).order_by('-number').first()
        
        return (existing_invoice.number + 1) if existing_invoice else 1
    
    @classmethod
    def create_with_auto_number(cls, company, document_type, series, **kwargs):
        """
        Crea una nueva factura con numeración automática para evitar duplicados
        """
        next_number = cls.get_next_number(company, document_type, series)
        
        return cls.objects.create(
            company=company,
            document_type=document_type,
            series=series,
            number=next_number,
            **kwargs
        )
    
    def calculate_totals(self):
        """Calcula los totales basado en las líneas de detalle - VERSIÓN CORREGIDA"""
        lines = self.invoice_lines.all()
        
        # Resetear totales
        self.total_taxed_amount = Decimal('0.00')
        self.total_unaffected_amount = Decimal('0.00') 
        self.total_exempt_amount = Decimal('0.00')
        self.total_free_amount = Decimal('0.00')
        self.igv_amount = Decimal('0.00')
        self.isc_amount = Decimal('0.00')
        self.icbper_amount = Decimal('0.00')
        
        for line in lines:
            # ✅ CORREGIDO: Manejar valores None correctamente
            line_extension_amount = line.line_extension_amount or Decimal('0.00')
            igv_amount = line.igv_amount or Decimal('0.00')
            isc_amount = line.isc_amount or Decimal('0.00')
            icbper_amount = line.icbper_amount or Decimal('0.00')
            
            if line.tax_category_code == 'S':  # Gravado
                self.total_taxed_amount += line_extension_amount
                self.igv_amount += igv_amount
            elif line.tax_category_code == 'E':  # Exonerado
                self.total_exempt_amount += line_extension_amount
            elif line.tax_category_code == 'O':  # Inafecto
                self.total_unaffected_amount += line_extension_amount
            elif line.tax_category_code == 'Z':  # Gratuito
                self.total_free_amount += line_extension_amount
                
            self.isc_amount += isc_amount
            self.icbper_amount += icbper_amount
        
        # Calcular total
        self.total_amount = (
            self.total_taxed_amount + 
            self.total_unaffected_amount + 
            self.total_exempt_amount +
            self.igv_amount + 
            self.isc_amount + 
            self.icbper_amount +
            self.perception_amount
        )
        
        self.save()
    
    def get_document_type_display_extended(self):
        """Retorna descripción extendida del tipo de documento"""
        type_mapping = {
            '01': 'Factura Electrónica',
            '03': 'Boleta de Venta Electrónica',
            '07': 'Nota de Crédito Electrónica',
            '08': 'Nota de Débito Electrónica'
        }
        return type_mapping.get(self.document_type, self.get_document_type_display())
    
    def get_currency_symbol(self):
        """Retorna el símbolo de la moneda"""
        symbols = {
            'PEN': 'S/',
            'USD': '$',
            'EUR': '€'
        }
        return symbols.get(self.currency_code, self.currency_code)
    
    def is_taxed_document(self):
        """Verifica si el documento tiene operaciones gravadas"""
        return self.total_taxed_amount > 0
    
    def has_perception(self):
        """Verifica si el documento tiene percepción"""
        return self.perception_amount > 0
    
    def get_total_before_tax(self):
        """Calcula el total antes de impuestos"""
        return self.total_taxed_amount + self.total_unaffected_amount + self.total_exempt_amount

    def __str__(self):
        return f"{self.document_id} - {self.customer.business_name}"

    class Meta:
        verbose_name = "Factura/Boleta"
        verbose_name_plural = "Facturas/Boletas"
        unique_together = ['company', 'document_type', 'series', 'number']
        ordering = ['-created_at']

class InvoiceLine(TimeStampedModel):
    """Líneas de detalle de Facturas y Boletas"""
    TAX_CATEGORY_CHOICES = [
        ('S', 'GRAVADO - OPERACIÓN ONEROSA'),
        ('E', 'EXONERADO - OPERACIÓN ONEROSA'),
        ('O', 'INAFECTO - OPERACIÓN ONEROSA'),
        ('Z', 'GRATUITO'),
    ]

    UNIT_CODE_CHOICES = [
        ('NIU', 'UNIDAD (BIENES)'),
        ('ZZ', 'UNIDAD (SERVICIOS)'),
        ('KGM', 'KILOGRAMO'),
        ('MTR', 'METRO'),
        ('LTR', 'LITRO'),
        ('HUR', 'HORA'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='invoice_lines')
    line_number = models.PositiveIntegerField(verbose_name="Número de Línea")
    
    # Producto/Servicio
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    product_code = models.CharField(max_length=50, verbose_name="Código del Producto")
    description = models.CharField(max_length=500, verbose_name="Descripción")
    
    # Cantidad y precio
    quantity = models.DecimalField(max_digits=12, decimal_places=6, verbose_name="Cantidad")
    unit_code = models.CharField(max_length=3, choices=UNIT_CODE_CHOICES, default='NIU')
    unit_price = models.DecimalField(max_digits=12, decimal_places=6, verbose_name="Precio Unitario")
    
    # Valores de referencia para gratuitos
    reference_price = models.DecimalField(max_digits=12, decimal_places=6, default=0, verbose_name="Precio de Referencia")
    
    # Totales de línea
    line_extension_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Valor de Venta")
    
    # Impuestos
    tax_category_code = models.CharField(max_length=1, choices=TAX_CATEGORY_CHOICES, default='S')
    tax_exemption_reason_code = models.CharField(max_length=2, blank=True, null=True)
    
    # Montos de impuestos
    igv_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, verbose_name="Tasa IGV %")
    igv_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, verbose_name="Monto IGV")
    
    isc_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tasa ISC %")
    isc_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, verbose_name="Monto ISC")
    
    icbper_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tasa ICBPER")
    icbper_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, verbose_name="Monto ICBPER")
    
    def calculate_amounts(self):
        """Calcula los montos de la línea basado en cantidad, precio y tipo de impuesto"""
        # Valor de venta (sin impuestos)
        if self.tax_category_code == 'Z':  # Gratuito
            self.line_extension_amount = Decimal('0.00')
            if not self.reference_price:
                self.reference_price = self.unit_price  # Usar precio como referencia si no se especifica
                self.unit_price = Decimal('0.00')
        else:
            self.line_extension_amount = self.quantity * self.unit_price
        
        # IGV
        if self.tax_category_code == 'S':  # Solo gravado paga IGV
            base_amount = self.line_extension_amount if self.tax_category_code != 'Z' else (self.quantity * (self.reference_price or Decimal('0.00')))
            self.igv_amount = base_amount * (self.igv_rate / 100)
        else:
            self.igv_amount = Decimal('0.00')
        
        # ISC
        if self.isc_rate > 0:
            base_amount = self.line_extension_amount if self.tax_category_code != 'Z' else (self.quantity * (self.reference_price or Decimal('0.00')))
            self.isc_amount = base_amount * (self.isc_rate / 100)
        else:
            self.isc_amount = Decimal('0.00')
        
        # ICBPER (Impuesto a las bolsas plásticas)
        if self.icbper_rate > 0:
            self.icbper_amount = self.quantity * self.icbper_rate
        else:
            self.icbper_amount = Decimal('0.00')
    
    def get_total_line_amount(self):
        """Calcula el total de la línea incluyendo impuestos"""
        line_amount = self.line_extension_amount or Decimal('0.00')
        igv_amount = self.igv_amount or Decimal('0.00')
        isc_amount = self.isc_amount or Decimal('0.00')
        icbper_amount = self.icbper_amount or Decimal('0.00')
        
        return line_amount + igv_amount + isc_amount + icbper_amount
    
    def is_free_item(self):
        """Verifica si el item es gratuito"""
        return self.tax_category_code == 'Z'
    
    def is_taxed_item(self):
        """Verifica si el item está gravado con IGV"""
        return self.tax_category_code == 'S'
    
    def get_unit_code_display_extended(self):
        """Retorna descripción extendida de la unidad de medida"""
        return dict(self.UNIT_CODE_CHOICES).get(self.unit_code, self.unit_code)
    
    def get_tax_category_display_extended(self):
        """Retorna descripción extendida de la categoría de impuesto"""
        return dict(self.TAX_CATEGORY_CHOICES).get(self.tax_category_code, self.tax_category_code)

    def save(self, *args, **kwargs):
        """Override del save para calcular automáticamente los montos"""
        # Calcular line_extension_amount si no se proporciona
        if self.line_extension_amount is None:
            if self.tax_category_code == 'Z':  # Gratuito
                self.line_extension_amount = Decimal('0.00')
                if not self.reference_price:
                    self.reference_price = self.unit_price
                    self.unit_price = Decimal('0.00')
            else:
                self.line_extension_amount = self.quantity * self.unit_price
        
        # Calcular IGV si no se proporciona
        if self.igv_amount is None:
            if self.tax_category_code == 'S':  # Solo gravado paga IGV
                base_amount = self.line_extension_amount if self.tax_category_code != 'Z' else (self.quantity * (self.reference_price or Decimal('0.00')))
                self.igv_amount = base_amount * (self.igv_rate / 100)
            else:
                self.igv_amount = Decimal('0.00')
        
        # Calcular ISC si aplica
        if self.isc_amount is None:
            if self.isc_rate > 0:
                base_amount = self.line_extension_amount if self.tax_category_code != 'Z' else (self.quantity * (self.reference_price or Decimal('0.00')))
                self.isc_amount = base_amount * (self.isc_rate / 100)
            else:
                self.isc_amount = Decimal('0.00')
        
        # Calcular ICBPER si aplica
        if self.icbper_amount is None:
            if self.icbper_rate > 0:
                self.icbper_amount = self.quantity * self.icbper_rate
            else:
                self.icbper_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Línea {self.line_number}: {self.description}"

    class Meta:
        verbose_name = "Línea de Factura"
        verbose_name_plural = "Líneas de Facturas"
        unique_together = ['invoice', 'line_number']
        ordering = ['line_number']

class InvoicePayment(TimeStampedModel):
    """Formas de pago de la factura"""
    PAYMENT_MEANS_CHOICES = [
        ('001', 'DEPÓSITO EN CUENTA'),
        ('002', 'GIRO'),
        ('003', 'TRANSFERENCIA DE FONDOS'),
        ('008', 'EFECTIVO, POR OPERACIONES EN LAS QUE NO EXISTE TRANSFERENCIA DE BIENES'),
        ('009', 'EFECTIVO, EN LOS DEMÁS CASOS'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    payment_means_code = models.CharField(max_length=3, choices=PAYMENT_MEANS_CHOICES)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto del Pago")
    
    def get_payment_means_display_extended(self):
        """Retorna descripción extendida del medio de pago"""
        return dict(self.PAYMENT_MEANS_CHOICES).get(self.payment_means_code, self.payment_means_code)
    
    def is_cash_payment(self):
        """Verifica si el pago es en efectivo"""
        return self.payment_means_code in ['008', '009']
    
    def is_electronic_payment(self):
        """Verifica si el pago es electrónico"""
        return self.payment_means_code in ['001', '003']

    def __str__(self):
        return f"{self.get_payment_means_code_display()}: {self.payment_amount}"

    class Meta:
        verbose_name = "Forma de Pago"
        verbose_name_plural = "Formas de Pago"