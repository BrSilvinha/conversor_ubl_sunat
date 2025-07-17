# ubl_converter/admin.py - VERSIÓN COMPLETA Y CORREGIDA
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from .models import Invoice, InvoiceLine, InvoicePayment

class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ['line_extension_amount', 'igv_amount', 'total_line_display']
    fields = [
        'line_number', 
        'product_code', 
        'description', 
        'quantity', 
        'unit_code',
        'unit_price', 
        'tax_category_code',
        'line_extension_amount',
        'igv_amount',
        'total_line_display'
    ]
    
    def total_line_display(self, obj):
        if obj.pk:
            total = obj.get_total_line_amount()
            return format_html('<strong>S/ {:.2f}</strong>', total)
        return '-'
    total_line_display.short_description = 'Total Línea'

class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0
    fields = ['payment_means_code', 'payment_amount']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'document_id_display',
        'company_ruc', 
        'customer_name_short',
        'total_amount_display',
        'status_display', 
        'issue_date',
        'files_status',
        'sunat_status'
    ]
    list_filter = [
        'document_type', 
        'status', 
        'currency_code', 
        'company', 
        'issue_date',
        'created_at'
    ]
    search_fields = [
        'series', 
        'number', 
        'customer__business_name', 
        'customer__document_number',
        'company__business_name',
        'company__ruc',
        'sunat_ticket'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'correlation_id', 
        'full_document_name',
        'document_id',
        'files_summary',
        'totals_summary',
        'sunat_summary'
    ]
    list_per_page = 25
    date_hierarchy = 'issue_date'
    
    fieldsets = (
        ('Identificación del Documento', {
            'fields': (
                'correlation_id', 
                'full_document_name',
                'company', 
                'document_type', 
                'series', 
                'number'
            ),
            'classes': ('wide',)
        }),
        ('Cliente y Fechas', {
            'fields': (
                'customer', 
                'issue_date', 
                'due_date', 
                'currency_code', 
                'operation_type_code'
            ),
        }),
        ('Totales Calculados', {
            'fields': ('totals_summary',),
            'classes': ('collapse',)
        }),
        ('Totales Detallados', {
            'fields': (
                'total_taxed_amount', 
                'total_exempt_amount', 
                'total_unaffected_amount',
                'total_free_amount',
                'igv_amount',
                'isc_amount',
                'icbper_amount',
                'perception_amount',
                'total_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Percepción/Retención', {
            'fields': (
                'perception_base_amount',
                'perception_percentage', 
                'perception_code'
            ),
            'classes': ('collapse',)
        }),
        ('Estado del Procesamiento', {
            'fields': ('status',),
        }),
        ('Archivos Generados', {
            'fields': ('files_summary', 'xml_file', 'zip_file', 'cdr_file'),
            'classes': ('collapse',)
        }),
        ('Respuesta SUNAT', {
            'fields': ('sunat_summary', 'sunat_ticket', 'sunat_response_code', 'sunat_response_description'),
            'classes': ('collapse',)
        }),
        ('Información Adicional', {
            'fields': ('observations',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [InvoiceLineInline, InvoicePaymentInline]
    
    def document_id_display(self, obj):
        doc_type_colors = {
            '01': 'primary',  # Factura
            '03': 'success',  # Boleta
            '07': 'warning',  # Nota Crédito
            '08': 'danger',   # Nota Débito
        }
        color = doc_type_colors.get(obj.document_type, 'secondary')
        type_name = 'FAC' if obj.document_type == '01' else 'BOL'
        
        return format_html(
            '<span class="badge badge-{}">{}</span><br><strong>{}</strong>',
            color,
            type_name,
            obj.document_id
        )
    document_id_display.short_description = 'Documento'
    
    def company_ruc(self, obj):
        return obj.company.ruc if obj.company else '-'
    company_ruc.short_description = 'RUC Emisor'
    
    def customer_name_short(self, obj):
        if obj.customer:
            name = obj.customer.business_name[:25]
            if len(obj.customer.business_name) > 25:
                name += '...'
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                name,
                obj.customer.document_number
            )
        return '-'
    customer_name_short.short_description = 'Cliente'
    
    def total_amount_display(self, obj):
        symbol = obj.get_currency_symbol()
        return format_html(
            '<strong>{} {:.2f}</strong>',
            symbol,
            obj.total_amount
        )
    total_amount_display.short_description = 'Total'
    
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
    
    def files_status(self, obj):
        files = []
        if obj.xml_file:
            files.append('<span class="badge badge-success">XML</span>')
        if obj.zip_file:
            files.append('<span class="badge badge-warning">ZIP</span>')
        if obj.cdr_file:
            files.append('<span class="badge badge-primary">CDR</span>')
        
        if not files:
            files.append('<span class="badge badge-secondary">Sin archivos</span>')
        
        return format_html(' '.join(files))
    files_status.short_description = 'Archivos'
    
    def sunat_status(self, obj):
        if obj.sunat_response_code:
            if obj.sunat_response_code == '0':
                return format_html('<span class="badge badge-success">Aceptado</span>')
            else:
                return format_html('<span class="badge badge-danger">Rechazado</span>')
        elif obj.sunat_ticket:
            return format_html('<span class="badge badge-info">En proceso</span>')
        elif obj.status in ['SENT', 'PROCESSING']:
            return format_html('<span class="badge badge-warning">Enviado</span>')
        else:
            return format_html('<span class="badge badge-secondary">No enviado</span>')
    sunat_status.short_description = 'SUNAT'
    
    def files_summary(self, obj):
        files_info = []
        
        if obj.xml_file:
            files_info.append(f'📄 XML: {obj.xml_file.split("/")[-1]}')
        else:
            files_info.append('📄 XML: No generado')
            
        if obj.zip_file:
            files_info.append(f'📦 ZIP: {obj.zip_file.split("/")[-1]}')
        else:
            files_info.append('📦 ZIP: No generado')
            
        if obj.cdr_file:
            files_info.append(f'📋 CDR: {obj.cdr_file.split("/")[-1]}')
        else:
            files_info.append('📋 CDR: No recibido')
        
        return format_html('<br>'.join(files_info))
    files_summary.short_description = 'Resumen de Archivos'
    
    def totals_summary(self, obj):
        symbol = obj.get_currency_symbol()
        lines = [
            f'💰 Gravado: {symbol} {obj.total_taxed_amount:.2f}',
            f'💰 Exonerado: {symbol} {obj.total_exempt_amount:.2f}',
            f'💰 Gratuito: {symbol} {obj.total_free_amount:.2f}',
            f'📊 IGV: {symbol} {obj.igv_amount:.2f}',
        ]
        
        if obj.perception_amount > 0:
            lines.append(f'📈 Percepción: {symbol} {obj.perception_amount:.2f}')
            
        lines.append(f'💳 <strong>TOTAL: {symbol} {obj.total_amount:.2f}</strong>')
        
        return format_html('<br>'.join(lines))
    totals_summary.short_description = 'Resumen de Totales'
    
    def sunat_summary(self, obj):
        lines = []
        
        if obj.sunat_ticket:
            lines.append(f'🎫 Ticket: {obj.sunat_ticket}')
            
        if obj.sunat_response_code:
            lines.append(f'📊 Código: {obj.sunat_response_code}')
            
        if obj.sunat_response_description:
            lines.append(f'📝 Descripción: {obj.sunat_response_description[:100]}')
            
        if not lines:
            lines.append('ℹ️ Sin información de SUNAT')
        
        return format_html('<br>'.join(lines))
    sunat_summary.short_description = 'Resumen SUNAT'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company', 'customer')
    
    actions = ['recalculate_totals', 'reset_processing_status']
    
    def recalculate_totals(self, request, queryset):
        """Recalcula los totales de las facturas seleccionadas"""
        count = 0
        for invoice in queryset:
            invoice.calculate_totals()
            count += 1
        
        self.message_user(
            request,
            f'Totales recalculados para {count} documento(s).'
        )
    recalculate_totals.short_description = "Recalcular totales"
    
    def reset_processing_status(self, request, queryset):
        """Resetea el estado de procesamiento a PENDING"""
        count = queryset.update(status='PENDING')
        
        self.message_user(
            request,
            f'Estado reseteado para {count} documento(s).'
        )
    reset_processing_status.short_description = "Resetear estado a PENDING"

@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_document',
        'line_number', 
        'description_short', 
        'quantity', 
        'unit_price',
        'tax_category_display',
        'total_line_amount_display'
    ]
    list_filter = [
        'tax_category_code', 
        'unit_code', 
        'invoice__company',
        'invoice__document_type',
        'created_at'
    ]
    search_fields = [
        'description', 
        'product_code', 
        'invoice__series', 
        'invoice__number',
        'invoice__customer__business_name'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at',
        'total_line_amount_display',
        'tax_amounts_summary'
    ]
    list_per_page = 50
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('invoice', 'line_number', 'product', 'product_code', 'description'),
            'classes': ('wide',)
        }),
        ('Cantidad y Precio', {
            'fields': ('quantity', 'unit_code', 'unit_price', 'reference_price'),
        }),
        ('Valores Calculados', {
            'fields': ('line_extension_amount', 'total_line_amount_display'),
        }),
        ('Configuración de Impuestos', {
            'fields': (
                'tax_category_code', 
                'tax_exemption_reason_code',
                'tax_amounts_summary'
            ),
        }),
        ('Montos de Impuestos', {
            'fields': (
                ('igv_rate', 'igv_amount'),
                ('isc_rate', 'isc_amount'),
                ('icbper_rate', 'icbper_amount')
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def invoice_document(self, obj):
        return obj.invoice.document_id if obj.invoice else '-'
    invoice_document.short_description = 'Documento'
    
    def description_short(self, obj):
        return obj.description[:40] + '...' if len(obj.description) > 40 else obj.description
    description_short.short_description = 'Descripción'
    
    def tax_category_display(self, obj):
        colors = {
            'S': 'success',  # Gravado
            'E': 'warning',  # Exonerado
            'O': 'info',     # Inafecto
            'Z': 'primary',  # Gratuito
        }
        color = colors.get(obj.tax_category_code, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_tax_category_code_display()
        )
    tax_category_display.short_description = 'Tipo Impuesto'
    
    def total_line_amount_display(self, obj):
        total = obj.get_total_line_amount()
        return format_html('<strong>S/ {:.2f}</strong>', total)
    total_line_amount_display.short_description = 'Total Línea'
    
    def tax_amounts_summary(self, obj):
        amounts = []
        
        if obj.igv_amount and obj.igv_amount > 0:
            amounts.append(f'IGV: S/ {obj.igv_amount:.2f}')
            
        if obj.isc_amount and obj.isc_amount > 0:
            amounts.append(f'ISC: S/ {obj.isc_amount:.2f}')
            
        if obj.icbper_amount and obj.icbper_amount > 0:
            amounts.append(f'ICBPER: S/ {obj.icbper_amount:.2f}')
        
        if not amounts:
            amounts.append('Sin impuestos aplicados')
            
        return format_html('<br>'.join(amounts))
    tax_amounts_summary.short_description = 'Resumen de Impuestos'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invoice', 'invoice__company', 'product')

@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_document',
        'payment_means_display',
        'payment_amount_display',
        'created_at'
    ]
    list_filter = [
        'payment_means_code',
        'invoice__company',
        'invoice__document_type',
        'created_at'
    ]
    search_fields = [
        'invoice__series',
        'invoice__number',
        'invoice__customer__business_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50
    
    fieldsets = (
        ('Información del Pago', {
            'fields': ('invoice', 'payment_means_code', 'payment_amount'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def invoice_document(self, obj):
        if obj.invoice:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:ubl_converter_invoice_change', args=[obj.invoice.pk]),
                obj.invoice.document_id
            )
        return '-'
    invoice_document.short_description = 'Documento'
    
    def payment_means_display(self, obj):
        payment_colors = {
            '001': 'primary',   # Depósito
            '002': 'info',      # Giro
            '003': 'success',   # Transferencia
            '008': 'warning',   # Efectivo sin transferencia
            '009': 'secondary', # Efectivo otros casos
        }
        color = payment_colors.get(obj.payment_means_code, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_payment_means_code_display()
        )
    payment_means_display.short_description = 'Medio de Pago'
    
    def payment_amount_display(self, obj):
        return format_html('<strong>S/ {:.2f}</strong>', obj.payment_amount)
    payment_amount_display.short_description = 'Monto'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invoice', 'invoice__company')

# Personalización adicional del admin site para UBL
admin.site.site_header = "Conversor UBL 2.1 - Administración"
admin.site.site_title = "UBL Admin"
admin.site.index_title = "Panel de Administración del Conversor UBL"

# Agregar estadísticas al dashboard (opcional)
def dashboard_stats(request):
    """Función para mostrar estadísticas en el dashboard"""
    from django.db.models import Count, Sum
    
    stats = {
        'total_invoices': Invoice.objects.count(),
        'invoices_signed': Invoice.objects.filter(status='SIGNED').count(),
        'invoices_accepted': Invoice.objects.filter(status='ACCEPTED').count(),
        'total_amount': Invoice.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'invoices_by_type': Invoice.objects.values('document_type').annotate(count=Count('id')),
        'invoices_by_status': Invoice.objects.values('status').annotate(count=Count('id'))
    }
    return stats