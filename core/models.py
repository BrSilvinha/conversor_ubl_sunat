# core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
import uuid

class TimeStampedModel(models.Model):
    """Modelo base con timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Company(TimeStampedModel):
    """Información de la empresa emisora"""
    ruc = models.CharField(
        max_length=11,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{11}$',
                message='RUC debe tener exactamente 11 dígitos'
            )
        ]
    )
    business_name = models.CharField(max_length=500, verbose_name="Razón Social")
    trade_name = models.CharField(max_length=500, blank=True, null=True, verbose_name="Nombre Comercial")
    
    # Dirección
    address_type_code = models.CharField(max_length=4, default='0000')
    address = models.CharField(max_length=500, verbose_name="Dirección")
    district = models.CharField(max_length=100, verbose_name="Distrito")
    province = models.CharField(max_length=100, verbose_name="Provincia") 
    department = models.CharField(max_length=100, verbose_name="Departamento")
    country_code = models.CharField(max_length=2, default='PE')
    ubigeo = models.CharField(max_length=6, blank=True, null=True)
    
    # Configuración
    is_active = models.BooleanField(default=True)
    certificate_path = models.CharField(max_length=500, blank=True, null=True)
    certificate_password = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.ruc} - {self.business_name}"

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

class Customer(TimeStampedModel):
    """Información del cliente/receptor"""
    DOCUMENT_TYPE_CHOICES = [
        ('0', 'DOC.TRIB.NO.DOM.SIN.RUC'),
        ('1', 'DNI'),
        ('4', 'CARNET DE EXTRANJERIA'), 
        ('6', 'RUC'),
        ('7', 'PASAPORTE'),
        ('A', 'CEDULA DIPLOMATICA DE IDENTIDAD'),
        ('B', 'DOC.IDENT.PAIS.RESIDENCIA-NO.D'),
        ('C', 'TAX IDENTIFICATION NUMBER - TIN – DOC TRIB PP.NN'),
        ('D', 'IDENTIFICATION NUMBER - IN – DOC TRIB PP. JJ'),
        ('E', 'TAM- TARJETA ANDINA DE MIGRACION'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customers')
    document_type = models.CharField(max_length=1, choices=DOCUMENT_TYPE_CHOICES)
    document_number = models.CharField(max_length=15)
    business_name = models.CharField(max_length=500, verbose_name="Razón Social")
    trade_name = models.CharField(max_length=500, blank=True, null=True, verbose_name="Nombre Comercial")
    
    # Dirección
    address = models.CharField(max_length=500, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    country_code = models.CharField(max_length=2, default='PE')
    
    # Email para envío automático
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.document_number} - {self.business_name}"

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        unique_together = ['company', 'document_type', 'document_number']

class Product(TimeStampedModel):
    """Catálogo de productos/servicios"""
    UNIT_CODE_CHOICES = [
        ('NIU', 'UNIDAD (BIENES)'),
        ('ZZ', 'UNIDAD (SERVICIOS)'),
        ('KGM', 'KILOGRAMO'),
        ('MTR', 'METRO'),
        ('LTR', 'LITRO'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    code = models.CharField(max_length=50, verbose_name="Código del Producto")
    description = models.CharField(max_length=500, verbose_name="Descripción")
    unit_code = models.CharField(max_length=3, choices=UNIT_CODE_CHOICES, default='NIU')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio Unitario")
    
    # Configuración de impuestos
    is_taxed = models.BooleanField(default=True, verbose_name="Afecto a IGV")
    is_free = models.BooleanField(default=False, verbose_name="Gratuito")
    
    # Códigos SUNAT
    tax_category_code = models.CharField(max_length=10, default='S', verbose_name="Código de Categoría Tributaria")
    tax_exemption_reason_code = models.CharField(max_length=2, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.description}"

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        unique_together = ['company', 'code']

class ProcessingStatus(models.TextChoices):
    """Estados de procesamiento de documentos"""
    PENDING = 'PENDING', 'Pendiente'
    PROCESSING = 'PROCESSING', 'Procesando'
    SIGNED = 'SIGNED', 'Firmado'
    SENT = 'SENT', 'Enviado a SUNAT'
    ACCEPTED = 'ACCEPTED', 'Aceptado'
    REJECTED = 'REJECTED', 'Rechazado'
    ERROR = 'ERROR', 'Error'

class DocumentSeries(TimeStampedModel):
    """Series de documentos por empresa"""
    DOCUMENT_TYPE_CHOICES = [
        ('01', 'FACTURA'),
        ('03', 'BOLETA DE VENTA'),
        ('07', 'NOTA DE CREDITO'),
        ('08', 'NOTA DE DEBITO'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='document_series')
    document_type = models.CharField(max_length=2, choices=DOCUMENT_TYPE_CHOICES)
    series = models.CharField(max_length=4)
    current_number = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def get_next_number(self):
        """Obtiene el siguiente número correlativo"""
        self.current_number += 1
        self.save()
        return self.current_number

    def __str__(self):
        return f"{self.company.ruc} - {self.series} ({self.get_document_type_display()})"

    class Meta:
        verbose_name = "Serie de Documento"
        verbose_name_plural = "Series de Documentos"
        unique_together = ['company', 'document_type', 'series']

class DocumentLog(TimeStampedModel):
    """Log de procesamiento de documentos"""
    correlation_id = models.UUIDField(default=uuid.uuid4, unique=True)
    document_type = models.CharField(max_length=2)
    document_id = models.CharField(max_length=50)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING)
    operation = models.CharField(max_length=50)
    
    # Archivos
    xml_file = models.CharField(max_length=500, blank=True, null=True)
    zip_file = models.CharField(max_length=500, blank=True, null=True)
    cdr_file = models.CharField(max_length=500, blank=True, null=True)
    
    # Información adicional
    sunat_ticket = models.CharField(max_length=50, blank=True, null=True)
    sunat_response_code = models.CharField(max_length=10, blank=True, null=True)
    sunat_response_description = models.TextField(blank=True, null=True)
    
    # Métricas
    processing_duration = models.PositiveIntegerField(blank=True, null=True, help_text="Duración en milisegundos")
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.document_id} - {self.status}"

    class Meta:
        verbose_name = "Log de Documento"
        verbose_name_plural = "Logs de Documentos"
        ordering = ['-created_at']