# api/views.py - VERSIÓN COMPLETA FINAL CON TODAS LAS FUNCIONALIDADES
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse, Http404
import os
import logging
from datetime import datetime, date
from decimal import Decimal

from core.models import Company, Customer, Product
from ubl_converter.models import Invoice, InvoiceLine, InvoicePayment
from ubl_converter.converter import UBLConverter
from digital_signature.signer import XMLDigitalSigner
from sunat_integration.client import SUNATWebServiceClient

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_invoice_test_scenarios(request):
    """
    Crear los 5 escenarios de prueba solicitados:
    1. Boleta con venta gravada, exonerada, con percepción, gratuita, bonificación
    """
    try:
        # Obtener o crear empresa de prueba
        company, created = Company.objects.get_or_create(
            ruc=settings.SUNAT_CONFIG['RUC'],
            defaults={
                'business_name': 'EMPRESA DE PRUEBAS SAC',
                'trade_name': 'EMPRESA PRUEBAS',
                'address': 'AV. PRINCIPAL 123',
                'district': 'LIMA',
                'province': 'LIMA',
                'department': 'LIMA',
                'ubigeo': '150101',
                'certificate_path': settings.SUNAT_CONFIG['CERTIFICATE_PATH'],
                'certificate_password': settings.SUNAT_CONFIG['CERTIFICATE_PASSWORD']
            }
        )
        
        # Crear cliente de prueba
        customer, created = Customer.objects.get_or_create(
            company=company,
            document_type='1',
            document_number='12345678',
            defaults={
                'business_name': 'CLIENTE DE PRUEBAS',
                'address': 'AV. CLIENTE 456',
                'district': 'LIMA',
                'province': 'LIMA',
                'department': 'LIMA'
            }
        )
        
        # Crear productos de prueba
        products_data = [
            {
                'code': 'PROD001',
                'description': 'PRODUCTO GRAVADO',
                'unit_price': Decimal('100.00'),
                'is_taxed': True,
                'tax_category_code': 'S'
            },
            {
                'code': 'PROD002', 
                'description': 'PRODUCTO EXONERADO',
                'unit_price': Decimal('50.00'),
                'is_taxed': False,
                'tax_category_code': 'E'
            },
            {
                'code': 'PROD003',
                'description': 'PRODUCTO GRATUITO',
                'unit_price': Decimal('0.00'),
                'is_taxed': False,
                'tax_category_code': 'Z'
            },
            {
                'code': 'SERV001',
                'description': 'SERVICIO CON PERCEPCION',
                'unit_price': Decimal('1000.00'),
                'is_taxed': True,
                'tax_category_code': 'S',
                'unit_code': 'ZZ'
            }
        ]
        
        products = []
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                company=company,
                code=prod_data['code'],
                defaults=prod_data
            )
            products.append(product)
        
        # ✅ CORREGIDO: Usar numeración automática para evitar duplicados
        with transaction.atomic():
            # Buscar siguiente número disponible para la serie B001
            existing_invoice = Invoice.objects.filter(
                company=company,
                document_type='03',
                series='B001'
            ).order_by('-number').first()
            
            next_number = (existing_invoice.number + 1) if existing_invoice else 1
            
            # Crear la boleta con número único
            invoice = Invoice.objects.create(
                company=company,
                customer=customer,
                document_type='03',  # Boleta de venta
                series='B001',
                number=next_number,  # ✅ Número único
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),  # Se calculará después
                observations=f'BOLETA DE PRUEBA #{next_number} - TODOS LOS ESCENARIOS'
            )
            
            # Línea 1: Producto gravado (S) - Calcular montos manualmente
            line1_value = Decimal('2.00') * Decimal('100.00')  # 200.00
            line1_igv = line1_value * Decimal('0.18')  # 36.00
            
            line1 = InvoiceLine.objects.create(
                invoice=invoice,
                line_number=1,
                product=products[0],
                product_code=products[0].code,
                description=products[0].description,
                quantity=Decimal('2.00'),
                unit_code='NIU',
                unit_price=Decimal('100.00'),
                line_extension_amount=line1_value,
                tax_category_code='S',
                igv_rate=Decimal('18.00'),
                igv_amount=line1_igv
            )
            
            # Línea 2: Producto exonerado (E)
            line2_value = Decimal('1.00') * Decimal('50.00')  # 50.00
            
            line2 = InvoiceLine.objects.create(
                invoice=invoice,
                line_number=2,
                product=products[1],
                product_code=products[1].code,
                description=products[1].description,
                quantity=Decimal('1.00'),
                unit_code='NIU',
                unit_price=Decimal('50.00'),
                line_extension_amount=line2_value,
                tax_category_code='E',
                tax_exemption_reason_code='20',  # Transferencias gratuitas
                igv_rate=Decimal('0.00'),
                igv_amount=Decimal('0.00')
            )
            
            # Línea 3: Producto gratuito (Z)
            line3 = InvoiceLine.objects.create(
                invoice=invoice,
                line_number=3,
                product=products[2],
                product_code=products[2].code,
                description=products[2].description + ' - BONIFICACION',
                quantity=Decimal('1.00'),
                unit_code='NIU',
                unit_price=Decimal('0.00'),
                line_extension_amount=Decimal('0.00'),  # Gratuito = 0
                reference_price=Decimal('30.00'),  # Precio de referencia
                tax_category_code='Z',
                igv_rate=Decimal('0.00'),
                igv_amount=Decimal('0.00')
            )
            
            # Línea 4: Servicio con percepción
            line4_value = Decimal('1.00') * Decimal('1000.00')  # 1000.00
            line4_igv = line4_value * Decimal('0.18')  # 180.00
            
            line4 = InvoiceLine.objects.create(
                invoice=invoice,
                line_number=4,
                product=products[3],
                product_code=products[3].code,
                description=products[3].description,
                quantity=Decimal('1.00'),
                unit_code='ZZ',
                unit_price=Decimal('1000.00'),
                line_extension_amount=line4_value,
                tax_category_code='S',
                igv_rate=Decimal('18.00'),
                igv_amount=line4_igv
            )
            
            # Configurar percepción (2% sobre servicios)
            invoice.perception_percentage = Decimal('2.00')
            invoice.perception_base_amount = Decimal('1000.00')
            invoice.perception_amount = invoice.perception_base_amount * (invoice.perception_percentage / 100)
            invoice.perception_code = '51'  # Percepción venta interna
            
            # Recalcular totales
            invoice.calculate_totals()
            
            # Agregar forma de pago
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code='009',  # Efectivo
                payment_amount=invoice.total_amount
            )
        
        return Response({
            'status': 'success',
            'message': 'Escenarios de prueba creados exitosamente',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'number_generated': next_number,
            'totals': {
                'total_taxed_amount': float(invoice.total_taxed_amount),
                'total_exempt_amount': float(invoice.total_exempt_amount), 
                'total_free_amount': float(invoice.total_free_amount),
                'igv_amount': float(invoice.igv_amount),
                'perception_amount': float(invoice.perception_amount),
                'total_amount': float(invoice.total_amount)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando escenarios de prueba: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error interno: {str(e)}',
            'suggestion': 'Revise la configuración de la base de datos y los settings'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_invoice_manual(request):
    """Crear factura manualmente desde el frontend"""
    try:
        data = request.data
        
        # Obtener o crear empresa
        company_data = data.get('company', {})
        company, created = Company.objects.get_or_create(
            ruc=company_data.get('ruc', settings.SUNAT_CONFIG['RUC']),
            defaults={
                'business_name': company_data.get('business_name', 'EMPRESA DE PRUEBAS SAC'),
                'address': company_data.get('address', 'AV. PRINCIPAL 123'),
                'district': 'LIMA',
                'province': 'LIMA',
                'department': 'LIMA',
                'ubigeo': '150101',
                'certificate_path': settings.SUNAT_CONFIG['CERTIFICATE_PATH'],
                'certificate_password': settings.SUNAT_CONFIG['CERTIFICATE_PASSWORD']
            }
        )
        
        # Obtener o crear cliente
        customer_data = data.get('customer', {})
        customer, created = Customer.objects.get_or_create(
            company=company,
            document_type=customer_data.get('document_type', '1'),
            document_number=customer_data.get('document_number', '12345678'),
            defaults={
                'business_name': customer_data.get('business_name', 'CLIENTE DE PRUEBAS'),
                'address': customer_data.get('address', 'AV. CLIENTE 456'),
                'district': 'LIMA',
                'province': 'LIMA',
                'department': 'LIMA'
            }
        )
        
        with transaction.atomic():
            # Datos del documento
            doc_data = data.get('document', {})
            
            # Buscar siguiente número disponible
            existing_invoice = Invoice.objects.filter(
                company=company,
                document_type=doc_data.get('document_type', '03'),
                series=doc_data.get('series', 'B001')
            ).order_by('-number').first()
            
            next_number = doc_data.get('number') or ((existing_invoice.number + 1) if existing_invoice else 1)
            
            # Crear factura
            invoice = Invoice.objects.create(
                company=company,
                customer=customer,
                document_type=doc_data.get('document_type', '03'),
                series=doc_data.get('series', 'B001'),
                number=int(next_number),
                issue_date=datetime.strptime(doc_data.get('issue_date'), '%Y-%m-%d').date() if doc_data.get('issue_date') else date.today(),
                currency_code=doc_data.get('currency_code', 'PEN'),
                operation_type_code='0101',
                total_amount=Decimal('0.00'),
                observations=doc_data.get('observations', '')
            )
            
            # Crear líneas
            for line_data in data.get('lines', []):
                tax_cat = line_data.get('tax_category_code', 'S')
                quantity = Decimal(str(line_data.get('quantity', 1)))
                unit_price = Decimal(str(line_data.get('unit_price', 0)))
                
                # Calcular montos según tipo de impuesto
                if tax_cat == 'Z':  # Gratuito
                    line_extension_amount = Decimal('0.00')
                    reference_price = unit_price
                    unit_price = Decimal('0.00')
                    igv_amount = Decimal('0.00')
                else:
                    line_extension_amount = quantity * unit_price
                    reference_price = Decimal('0.00')
                    igv_amount = line_extension_amount * Decimal('0.18') if tax_cat == 'S' else Decimal('0.00')
                
                InvoiceLine.objects.create(
                    invoice=invoice,
                    line_number=line_data.get('line_number', 1),
                    product_code=line_data.get('product_code', 'PROD001'),
                    description=line_data.get('description', 'Producto'),
                    quantity=quantity,
                    unit_code='NIU',
                    unit_price=unit_price,
                    reference_price=reference_price,
                    line_extension_amount=line_extension_amount,
                    tax_category_code=tax_cat,
                    igv_rate=Decimal('18.00') if tax_cat == 'S' else Decimal('0.00'),
                    igv_amount=igv_amount,
                    tax_exemption_reason_code='20' if tax_cat in ['E', 'O'] else None
                )
            
            # Recalcular totales
            invoice.calculate_totals()
            
            # Agregar forma de pago
            payment_data = data.get('payment', {})
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code=payment_data.get('payment_means_code', '009'),
                payment_amount=invoice.total_amount
            )
        
        return Response({
            'status': 'success',
            'message': 'Documento creado exitosamente',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'totals': {
                'total_taxed_amount': float(invoice.total_taxed_amount),
                'total_exempt_amount': float(invoice.total_exempt_amount),
                'total_free_amount': float(invoice.total_free_amount),
                'igv_amount': float(invoice.igv_amount),
                'total_amount': float(invoice.total_amount)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando documento manual: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_documents(request):
    """Listar documentos creados"""
    try:
        invoices = Invoice.objects.all().order_by('-created_at')[:50]  # Últimos 50
        
        documents = []
        for invoice in invoices:
            documents.append({
                'id': invoice.id,
                'document_type': invoice.document_type,
                'document_reference': invoice.full_document_name,
                'series': invoice.series,
                'number': invoice.number,
                'customer_name': invoice.customer.business_name,
                'total_amount': float(invoice.total_amount),
                'status': invoice.status,
                'created_at': invoice.created_at.isoformat(),
                'issue_date': invoice.issue_date.isoformat(),
                'xml_file': bool(invoice.xml_file),
                'zip_file': bool(invoice.zip_file),
                'cdr_file': bool(invoice.cdr_file)
            })
        
        return Response({
            'status': 'success',
            'results': documents,
            'count': len(documents)
        })
        
    except Exception as e:
        logger.error(f"Error listando documentos: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_file_content(request):
    """Obtener contenido de archivo XML, ZIP o CDR"""
    try:
        file_path = request.GET.get('path')
        if not file_path:
            return Response({
                'status': 'error',
                'message': response.get('error_message')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error consultando estado SUNAT: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def process_complete_flow(request, invoice_id):
    """Procesa el flujo completo - VERSIÓN MEJORADA PARA ERRORES 401"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        results = {
            'invoice_id': invoice.id,
            'steps': []
        }
        
        # Paso 1: Convertir a UBL
        try:
            converter = UBLConverter()
            xml_content = converter.convert_invoice_to_xml(invoice)
            xml_filename = f"{invoice.full_document_name}.xml"
            xml_file_path = converter.save_xml_to_file(xml_content, xml_filename)
            invoice.xml_file = xml_file_path
            invoice.status = 'PROCESSING'
            invoice.save()
            
            results['steps'].append({
                'step': 'ubl_conversion',
                'status': 'success',
                'message': 'XML UBL generado exitosamente'
            })
        except Exception as e:
            results['steps'].append({
                'step': 'ubl_conversion',
                'status': 'error',
                'message': str(e)
            })
            raise e
        
        # Paso 2: Firmar XML
        try:
            with open(invoice.xml_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            signer = XMLDigitalSigner()
            signed_xml = signer.sign_xml(xml_content, invoice.full_document_name)
            
            signed_filename = f"{invoice.full_document_name}_signed.xml"
            signed_file_path = os.path.join(settings.MEDIA_ROOT, 'xml_files', signed_filename)
            
            with open(signed_file_path, 'w', encoding='utf-8') as f:
                f.write(signed_xml)
            
            zip_filename = f"{invoice.full_document_name}.zip"
            zip_file_path = converter.create_zip_file(signed_file_path, zip_filename)
            
            invoice.xml_file = signed_file_path
            invoice.zip_file = zip_file_path
            invoice.status = 'SIGNED'
            invoice.save()
            
            results['steps'].append({
                'step': 'digital_signature',
                'status': 'success',
                'message': 'XML firmado exitosamente'
            })
        except Exception as e:
            results['steps'].append({
                'step': 'digital_signature',
                'status': 'error',
                'message': str(e)
            })
            raise e
        
        # Paso 3: Enviar a SUNAT (con manejo mejorado de errores 401)
        try:
            sunat_client = SUNATWebServiceClient()
            zip_filename = f"{invoice.full_document_name}.zip"
            
            if invoice.document_type in ['01', '03']:
                response = sunat_client.send_bill(invoice.zip_file, zip_filename)
            else:
                response = sunat_client.send_summary(invoice.zip_file, zip_filename)
            
            if response['status'] == 'success':
                invoice.status = 'SENT'
                
                if response.get('response_type') == 'cdr':
                    cdr_info = response.get('cdr_info', {})
                    invoice.status = 'ACCEPTED' if cdr_info.get('response_code') == '0' else 'REJECTED'
                    invoice.sunat_response_code = cdr_info.get('response_code')
                    invoice.sunat_response_description = cdr_info.get('response_description')
                    
                    if response.get('cdr_content'):
                        cdr_filename = f"R-{invoice.full_document_name}.zip"
                        cdr_path = os.path.join(settings.MEDIA_ROOT, 'cdr_files', cdr_filename)
                        os.makedirs(os.path.dirname(cdr_path), exist_ok=True)
                        
                        import base64
                        with open(cdr_path, 'wb') as f:
                            f.write(base64.b64decode(response['cdr_content']))
                        
                        invoice.cdr_file = cdr_path
                
                elif response.get('response_type') == 'ticket':
                    invoice.sunat_ticket = response.get('ticket')
                
                invoice.save()
                
                results['steps'].append({
                    'step': 'sunat_submission',
                    'status': 'success',
                    'message': 'Documento enviado a SUNAT exitosamente',
                    'sunat_response': response
                })
            else:
                # Manejar errores de SUNAT de forma más elegante
                error_msg = response.get('error_message', 'Error desconocido')
                
                if '401' in error_msg or 'Unauthorized' in error_msg:
                    # Error 401 - No marcar como error total
                    results['steps'].append({
                        'step': 'sunat_submission',
                        'status': 'warning',
                        'message': 'Error de autenticación SUNAT (normal con credenciales de prueba)',
                        'details': 'Documento generado y firmado correctamente. Error solo en autenticación.'
                    })
                    
                    # Mantener estado SIGNED en lugar de ERROR
                    invoice.sunat_response_description = 'Error 401 - Credenciales de prueba'
                    # No cambiar invoice.status a ERROR
                    
                else:
                    invoice.status = 'ERROR'
                    invoice.sunat_response_description = error_msg
                    
                    results['steps'].append({
                        'step': 'sunat_submission',
                        'status': 'error',
                        'message': error_msg
                    })
                
                invoice.save()
                
        except Exception as e:
            error_msg = str(e)
            
            if '401' in error_msg or 'Unauthorized' in error_msg:
                # Error 401 - Tratarlo como advertencia, no error fatal
                results['steps'].append({
                    'step': 'sunat_submission',
                    'status': 'warning',
                    'message': 'Error de autenticación SUNAT (normal con credenciales de prueba)',
                    'technical_details': error_msg
                })
                
                invoice.sunat_response_description = 'Error 401 - Credenciales de prueba'
                invoice.save()
                
                # No hacer raise para continuar el flujo
            else:
                results['steps'].append({
                    'step': 'sunat_submission',
                    'status': 'error',
                    'message': error_msg
                })
                raise e
        
        # Evaluar resultado final
        successful_steps = sum(1 for step in results['steps'] if step['status'] == 'success')
        warning_steps = sum(1 for step in results['steps'] if step['status'] == 'warning')
        
        if successful_steps >= 2:  # UBL + Firma mínimo
            if warning_steps > 0:
                results['overall_status'] = 'success_with_warnings'
                results['message'] = 'Flujo procesado exitosamente (errores de SUNAT por credenciales de prueba)'
            else:
                results['overall_status'] = 'success'
                results['message'] = 'Flujo completo procesado exitosamente'
        else:
            results['overall_status'] = 'error'
            results['message'] = 'Error en pasos críticos del flujo'
        
        results['final_invoice_status'] = invoice.status
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error en flujo completo: {str(e)}")
        results['overall_status'] = 'error'
        results['message'] = str(e)
        return Response(results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_invoice_status(request, invoice_id):
    """Obtiene el estado actual de una factura"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        return Response({
            'invoice_id': invoice.id,
            'document_reference': invoice.full_document_name,
            'status': invoice.status,
            'created_at': invoice.created_at,
            'updated_at': invoice.updated_at,
            'files': {
                'xml_file': invoice.xml_file,
                'zip_file': invoice.zip_file,
                'cdr_file': invoice.cdr_file
            },
            'sunat_info': {
                'ticket': invoice.sunat_ticket,
                'response_code': invoice.sunat_response_code,
                'response_description': invoice.sunat_response_description
            },
            'totals': {
                'total_taxed_amount': float(invoice.total_taxed_amount),
                'total_exempt_amount': float(invoice.total_exempt_amount),
                'total_free_amount': float(invoice.total_free_amount),
                'igv_amount': float(invoice.igv_amount),
                'perception_amount': float(invoice.perception_amount),
                'total_amount': float(invoice.total_amount)
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de factura: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_sunat_connection(request):
    """Prueba la conexión con SUNAT - VERSIÓN MEJORADA"""
    try:
        # Primero verificar configuración básica
        sunat_config = settings.SUNAT_CONFIG
        
        if not sunat_config.get('RUC'):
            return Response({
                'status': 'error',
                'message': 'Configuración SUNAT incompleta: RUC no configurado',
                'suggestion': 'Verifique el archivo .env'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Intentar crear cliente SUNAT con manejo de errores mejorado
        try:
            sunat_client = SUNATWebServiceClient()
            result = sunat_client.test_connection()
            
            # Interpretar el resultado
            if result['status'] == 'success':
                return Response({
                    'status': 'success',
                    'message': 'Conexión exitosa con SUNAT',
                    'environment': result.get('environment', 'UNKNOWN'),
                    'operations': result.get('operations', []),
                    'wsdl_url': result.get('wsdl_url'),
                    'note': 'Servicio SUNAT funcionando correctamente'
                })
            elif result['status'] == 'warning':
                # Error 401 es normal con credenciales de prueba
                return Response({
                    'status': 'warning',
                    'message': 'Conexión con advertencias (normal con credenciales de prueba)',
                    'environment': result.get('environment', 'BETA'),
                    'error_details': result.get('error_details'),
                    'suggestion': result.get('suggestion'),
                    'note': 'El error 401 es esperado con credenciales MODDATOS en BETA'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': result.get('message', 'Error desconocido'),
                    'environment': result.get('environment'),
                    'suggestion': 'Verifique la conexión a internet y configuración'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except ImportError as e:
            return Response({
                'status': 'error',
                'message': 'Error de dependencias: biblioteca SUNAT no disponible',
                'error_details': str(e),
                'suggestion': 'Ejecute: pip install zeep cryptography'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            error_msg = str(e)
            
            # Clasificar tipos de error comunes
            if '401' in error_msg or 'Unauthorized' in error_msg:
                return Response({
                    'status': 'warning',
                    'message': 'Error de autenticación SUNAT (normal con credenciales de prueba)',
                    'environment': 'BETA' if sunat_config.get('USE_BETA') else 'PRODUCCIÓN',
                    'error_details': error_msg,
                    'note': 'Este error es esperado al usar credenciales MODDATOS en ambiente BETA'
                })
            elif 'Connection' in error_msg or 'timeout' in error_msg:
                return Response({
                    'status': 'error',
                    'message': 'Error de conectividad',
                    'error_details': error_msg,
                    'suggestion': 'Verifique la conexión a internet'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Error en cliente SUNAT',
                    'error_details': error_msg,
                    'suggestion': 'Revise la configuración en settings.py'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error en test_sunat_connection: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Error interno del sistema',
            'error_details': str(e),
            'suggestion': 'Revise los logs del servidor para más detalles'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)status': 'error',
                'message': 'Parámetro path requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar que el archivo existe y está en la carpeta media
        full_path = os.path.join(settings.MEDIA_ROOT, file_path.replace('media/', ''))
        
        if not os.path.exists(full_path):
            raise Http404("Archivo no encontrado")
        
        # Leer contenido del archivo
        if full_path.endswith('.xml'):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='application/xml')
        elif full_path.endswith('.zip'):
            with open(full_path, 'rb') as f:
                content = f.read()
            return HttpResponse(content, content_type='application/zip')
        else:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='text/plain')
        
    except Exception as e:
        logger.error(f"Error obteniendo contenido de archivo: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def convert_to_ubl(request, invoice_id):
    """Convierte una factura a XML UBL 2.1"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Crear convertidor UBL
        converter = UBLConverter()
        
        # Convertir a XML
        xml_content = converter.convert_invoice_to_xml(invoice)
        
        # Guardar XML
        xml_filename = f"{invoice.full_document_name}.xml"
        xml_file_path = converter.save_xml_to_file(xml_content, xml_filename)
        
        # Actualizar registro
        invoice.xml_file = xml_file_path
        invoice.status = 'PROCESSING'
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'XML UBL generado exitosamente',
            'invoice_id': invoice.id,
            'xml_filename': xml_filename,
            'xml_path': xml_file_path,
            'preview': xml_content[:500] + '...' if len(xml_content) > 500 else xml_content
        })
        
    except Exception as e:
        logger.error(f"Error convirtiendo a UBL: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def sign_xml(request, invoice_id):
    """Firma digitalmente el XML de una factura"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if not invoice.xml_file:
            return Response({
                'status': 'error',
                'message': 'Primero debe generar el XML UBL'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Leer XML
        with open(invoice.xml_file, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Crear firmador digital
        signer = XMLDigitalSigner()
        
        # Firmar XML
        signed_xml = signer.sign_xml(xml_content, invoice.full_document_name)
        
        # Guardar XML firmado
        signed_filename = f"{invoice.full_document_name}_signed.xml"
        signed_file_path = os.path.join(settings.MEDIA_ROOT, 'xml_files', signed_filename)
        
        with open(signed_file_path, 'w', encoding='utf-8') as f:
            f.write(signed_xml)
        
        # Crear ZIP
        converter = UBLConverter()
        zip_filename = f"{invoice.full_document_name}.zip"
        zip_file_path = converter.create_zip_file(signed_file_path, zip_filename)
        
        # Actualizar registro
        invoice.xml_file = signed_file_path
        invoice.zip_file = zip_file_path
        invoice.status = 'SIGNED'
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'XML firmado exitosamente',
            'invoice_id': invoice.id,
            'signed_xml_path': signed_file_path,
            'zip_path': zip_file_path,
            'certificate_info': signer.get_certificate_info()
        })
        
    except Exception as e:
        logger.error(f"Error firmando XML: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_to_sunat(request, invoice_id):
    """Envía documento firmado a SUNAT - VERSIÓN MEJORADA PARA ERRORES 401"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if not invoice.zip_file:
            return Response({
                'status': 'error',
                'message': 'Primero debe firmar el XML'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Crear cliente SUNAT
            sunat_client = SUNATWebServiceClient()
            
            # Determinar método de envío según tipo de documento
            zip_filename = f"{invoice.full_document_name}.zip"
            
            if invoice.document_type in ['01', '03']:  # Facturas y boletas
                # Envío síncrono
                response = sunat_client.send_bill(invoice.zip_file, zip_filename)
            else:
                # Para otros tipos (resúmenes), envío asíncrono
                response = sunat_client.send_summary(invoice.zip_file, zip_filename)
            
        except Exception as sunat_error:
            # Manejar específicamente errores 401 de SUNAT
            error_msg = str(sunat_error)
            if "401" in error_msg or "Unauthorized" in error_msg:
                # Error 401 es normal con credenciales de prueba
                invoice.status = 'SIGNED'  # Mantener como firmado, no marcar error
                invoice.sunat_response_description = 'Error 401 - Credenciales de prueba (normal en ambiente BETA)'
                invoice.save()
                
                return Response({
                    'status': 'warning',
                    'message': 'Error de autenticación SUNAT (normal con credenciales de prueba)',
                    'invoice_id': invoice.id,
                    'sunat_response': {
                        'status': 'auth_error',
                        'error_message': 'Error 401 - Credenciales MODDATOS no válidas para envío real',
                        'note': 'El documento se generó y firmó correctamente. Error solo en envío a SUNAT.'
                    },
                    'suggestion': 'Para envío real a SUNAT necesitas credenciales válidas de producción',
                    'files_generated': {
                        'xml_signed': bool(invoice.xml_file),
                        'zip_created': bool(invoice.zip_file)
                    }
                })
            else:
                # Otros errores de SUNAT
                invoice.status = 'ERROR'
                invoice.sunat_response_description = error_msg
                invoice.save()
                
                return Response({
                    'status': 'error',
                    'message': f'Error en cliente SUNAT: {error_msg}',
                    'invoice_id': invoice.id
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Actualizar registro según respuesta
        if response['status'] == 'success':
            invoice.status = 'SENT'
            
            if response.get('response_type') == 'cdr':
                # Respuesta síncrona con CDR
                cdr_info = response.get('cdr_info', {})
                invoice.status = 'ACCEPTED' if cdr_info.get('response_code') == '0' else 'REJECTED'
                invoice.sunat_response_code = cdr_info.get('response_code')
                invoice.sunat_response_description = cdr_info.get('response_description')
                
                # Guardar CDR
                if response.get('cdr_content'):
                    cdr_filename = f"R-{invoice.full_document_name}.zip"
                    cdr_path = os.path.join(settings.MEDIA_ROOT, 'cdr_files', cdr_filename)
                    os.makedirs(os.path.dirname(cdr_path), exist_ok=True)
                    
                    import base64
                    with open(cdr_path, 'wb') as f:
                        f.write(base64.b64decode(response['cdr_content']))
                    
                    invoice.cdr_file = cdr_path
                
            elif response.get('response_type') == 'ticket':
                # Respuesta asíncrona con ticket
                invoice.sunat_ticket = response.get('ticket')
            
            invoice.save()
            
            return Response({
                'status': 'success',
                'message': 'Documento enviado a SUNAT exitosamente',
                'invoice_id': invoice.id,
                'sunat_response': response,
                'invoice_status': invoice.status
            })
        else:
            # Error en el envío
            invoice.status = 'ERROR'
            invoice.sunat_response_description = response.get('error_message')
            invoice.save()
            
            return Response({
                'status': 'error',
                'message': response.get('error_message'),
                'invoice_id': invoice.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error enviando a SUNAT: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_sunat_status(request, invoice_id):
    """Consulta el estado en SUNAT (para documentos con ticket)"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if not invoice.sunat_ticket:
            return Response({
                'status': 'error',
                'message': 'No hay ticket de SUNAT para consultar'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear cliente SUNAT
        sunat_client = SUNATWebServiceClient()
        
        # Consultar estado
        response = sunat_client.get_status(invoice.sunat_ticket)
        
        if response['status'] == 'success':
            # Actualizar estado según respuesta
            processing_status = response.get('processing_status')
            
            if processing_status == 'completed':
                invoice.status = 'ACCEPTED'
                invoice.sunat_response_code = '0'
                invoice.sunat_response_description = 'Procesado correctamente'
                
                # Guardar CDR si está disponible
                if response.get('content'):
                    cdr_filename = f"R-{invoice.full_document_name}.zip"
                    cdr_path = os.path.join(settings.MEDIA_ROOT, 'cdr_files', cdr_filename)
                    os.makedirs(os.path.dirname(cdr_path), exist_ok=True)
                    
                    import base64
                    with open(cdr_path, 'wb') as f:
                        f.write(base64.b64decode(response['content']))
                    
                    invoice.cdr_file = cdr_path
                
            elif processing_status == 'error':
                invoice.status = 'REJECTED'
                invoice.sunat_response_code = response.get('status_code')
                invoice.sunat_response_description = 'Procesado con errores'
            
            invoice.save()
            
            return Response({
                'status': 'success',
                'message': 'Estado consultado exitosamente',
                'invoice_id': invoice.id,
                'processing_status': processing_status,
                'sunat_response': response,
                'invoice_status': invoice.status
            })
        else:
            return Response({
                '