# core/admin.py - VERSIÓN COMPLETA Y CORREGIDA
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Company, Customer, Product, DocumentSeries, DocumentLog

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['ruc', 'business_name', 'trade_name', 'department', 'is_active', 'created_at']
    list_filter = ['is_active', 'department', 'province', 'created_at']
    search_fields = ['ruc', 'business_name', 'trade_name']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 20
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('ruc', 'business_name', 'trade_name', 'is_active'),
            'classes': ('wide',)
        }),
        ('Dirección', {
            'fields': (
                'address_type_code',
                'address', 
                'district', 
                'province', 
                'department', 
                'ubigeo', 
                'country_code'
            ),
            'classes': ('collapse',)
        }),
        ('Certificado Digital', {
            'fields': ('certificate_path', 'certificate_password'),
            'classes': ('collapse',),
            'description': 'Configuración del certificado digital para firma XML'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('customers', 'products')
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'certificate_password':
            kwargs['widget'] = admin.widgets.AdminTextInputWidget(attrs={'type': 'password'})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'document_number', 
        'business_name', 
        'document_type_display', 
        'company_link', 
        'district',
        'is_active',
        'created_at'
    ]
    list_filter = ['document_type', 'company', 'is_active', 'country_code', 'created_at']
    search_fields = ['document_number', 'business_name', 'trade_name', 'email']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    
    fieldsets = (
        ('Identificación', {
            'fields': ('company', 'document_type', 'document_number'),
            'classes': ('wide',)
        }),
        ('Información Personal/Empresarial', {
            'fields': ('business_name', 'trade_name', 'email'),
        }),
        ('Dirección', {
            'fields': ('address', 'district', 'province', 'department', 'country_code'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def document_type_display(self, obj):
        type_colors = {
            '1': 'primary',  # DNI
            '6': 'success',  # RUC
            '4': 'warning',  # CE
            '7': 'info',     # Pasaporte
        }
        color = type_colors.get(obj.document_type, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_document_type_display()
        )
    document_type_display.short_description = 'Tipo Documento'
    
    def company_link(self, obj):
        if obj.company:
            url = reverse('admin:core_company_change', args=[obj.company.pk])
            return format_html('<a href="{}">{}</a>', url, obj.company.business_name[:30])
        return '-'
    company_link.short_description = 'Empresa'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'code', 
        'description_short', 
        'unit_price_display', 
        'tax_status', 
        'unit_code',
        'company_link', 
        'is_active'
    ]
    list_filter = [
        'is_taxed', 
        'is_free', 
        'tax_category_code', 
        'unit_code',
        'company', 
        'is_active',
        'created_at'
    ]
    search_fields = ['code', 'description', 'company__business_name']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 30
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('company', 'code', 'description'),
            'classes': ('wide',)
        }),
        ('Precio y Unidad', {
            'fields': ('unit_price', 'unit_code'),
        }),
        ('Configuración Tributaria', {
            'fields': (
                'is_taxed', 
                'is_free', 
                'tax_category_code', 
                'tax_exemption_reason_code'
            ),
            'description': 'Configuración de impuestos para el producto'
        }),
        ('Estado', {
            'fields': ('is_active',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Descripción'
    
    def unit_price_display(self, obj):
        return format_html('S/ <strong>{:.2f}</strong>', obj.unit_price)
    unit_price_display.short_description = 'Precio'
    
    def tax_status(self, obj):
        if obj.is_free:
            return format_html('<span class="badge badge-info">Gratuito</span>')
        elif obj.is_taxed:
            return format_html('<span class="badge badge-success">Gravado</span>')
        else:
            return format_html('<span class="badge badge-warning">Exonerado</span>')
    tax_status.short_description = 'Estado Tributario'
    
    def company_link(self, obj):
        if obj.company:
            url = reverse('admin:core_company_change', args=[obj.company.pk])
            return format_html('<a href="{}">{}</a>', url, obj.company.ruc)
        return '-'
    company_link.short_description = 'Empresa'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')

@admin.register(DocumentSeries)
class DocumentSeriesAdmin(admin.ModelAdmin):
    list_display = [
        'company_ruc', 
        'document_type_display', 
        'series', 
        'current_number', 
        'next_number_preview',
        'is_active'
    ]
    list_filter = ['document_type', 'company', 'is_active', 'created_at']
    search_fields = ['series', 'company__ruc', 'company__business_name']
    readonly_fields = ['created_at', 'updated_at', 'next_number_preview']
    list_per_page = 25
    
    fieldsets = (
        ('Configuración', {
            'fields': ('company', 'document_type', 'series'),
            'classes': ('wide',)
        }),
        ('Numeración', {
            'fields': ('current_number', 'next_number_preview'),
            'description': 'El próximo número se asignará automáticamente'
        }),
        ('Estado', {
            'fields': ('is_active',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def company_ruc(self, obj):
        return obj.company.ruc if obj.company else '-'
    company_ruc.short_description = 'RUC'
    
    def document_type_display(self, obj):
        type_colors = {
            '01': 'primary',  # Factura
            '03': 'success',  # Boleta
            '07': 'warning',  # Nota Crédito
            '08': 'danger',   # Nota Débito
        }
        color = type_colors.get(obj.document_type, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_document_type_display()
        )
    document_type_display.short_description = 'Tipo'
    
    def next_number_preview(self, obj):
        next_num = obj.current_number + 1
        return format_html('<strong>{}-{:08d}</strong>', obj.series, next_num)
    next_number_preview.short_description = 'Próximo Número'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')

@admin.register(DocumentLog)
class DocumentLogAdmin(admin.ModelAdmin):
    list_display = [
        'correlation_id_short',
        'document_id', 
        'company_ruc', 
        'status_display', 
        'operation', 
        'processing_time',
        'created_at'
    ]
    list_filter = [
        'status', 
        'operation', 
        'document_type', 
        'company',
        'created_at'
    ]
    search_fields = [
        'document_id', 
        'correlation_id', 
        'company__ruc',
        'sunat_ticket'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'correlation_id',
        'processing_duration_display'
    ]
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Identificación', {
            'fields': ('correlation_id', 'document_type', 'document_id', 'company'),
            'classes': ('wide',)
        }),
        ('Estado del Proceso', {
            'fields': ('status', 'operation'),
        }),
        ('Archivos Generados', {
            'fields': ('xml_file', 'zip_file', 'cdr_file'),
            'classes': ('collapse',)
        }),
        ('Respuesta SUNAT', {
            'fields': (
                'sunat_ticket', 
                'sunat_response_code', 
                'sunat_response_description'
            ),
            'classes': ('collapse',)
        }),
        ('Métricas', {
            'fields': ('processing_duration', 'processing_duration_display'),
            'classes': ('collapse',)
        }),
        ('Errores', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def correlation_id_short(self, obj):
        return str(obj.correlation_id)[:8] + '...'
    correlation_id_short.short_description = 'Correlation ID'
    
    def company_ruc(self, obj):
        return obj.company.ruc if obj.company else '-'
    company_ruc.short_description = 'RUC'
    
    def status_display(self, obj):
        status_colors = {
            'PENDING': 'secondary',
            'PROCESSING': 'warning',
            'SIGNED': 'info',
            'SENT': 'primary',
            'ACCEPTED': 'success',
            'REJECTED': 'danger',
            'ERROR': 'danger',
        }
        color = status_colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.status
        )
    status_display.short_description = 'Estado'
    
    def processing_time(self, obj):
        if obj.processing_duration:
            if obj.processing_duration < 1000:
                return f"{obj.processing_duration}ms"
            else:
                return f"{obj.processing_duration/1000:.2f}s"
        return '-'
    processing_time.short_description = 'Tiempo'
    
    def processing_duration_display(self, obj):
        if obj.processing_duration:
            return f"{obj.processing_duration} milisegundos"
        return "No disponible"
    processing_duration_display.short_description = 'Duración del Procesamiento'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')

# Personalización del admin site
admin.site.site_header = "Conversor UBL 2.1 - Administración"
admin.site.site_title = "UBL Admin"
admin.site.index_title = "Panel de Administración del Conversor UBL"

# CSS personalizado para badges (agregar al final del archivo)
class Media:
    css = {
        'all': ('admin/css/custom_admin.css',)
    }