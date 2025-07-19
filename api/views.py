# api/views.py - ARCHIVO COMPLETO CORREGIDO CON TODAS LAS FUNCIONES FALTANTES
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
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET

from core.models import Company, Customer, Product
from core.utils import (
    get_absolute_file_path, 
    find_file_in_media, 
    save_file_path_normalized,
    get_safe_file_path,
    repair_file_path
)
from ubl_converter.models import Invoice, InvoiceLine, InvoicePayment
from ubl_converter.converter import UBLConverter
from digital_signature.signer import XMLDigitalSigner
from sunat_integration.client import SUNATWebServiceClient

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def process_complete_flow(request, invoice_id):
    """Procesa el flujo completo: UBL → Firma → Envío SUNAT"""
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
            
            # ✅ GUARDAR RUTA NORMALIZADA
            invoice.xml_file = save_file_path_normalized(xml_file_path)
            invoice.status = 'PROCESSING'
            invoice.save()
            
            results['steps'].append({
                'step': 'ubl_conversion',
                'status': 'success',
                'message': 'XML UBL generado exitosamente',
                'file_path': invoice.xml_file
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
            # ✅ OBTENER RUTA ABSOLUTA SEGURA
            xml_absolute_path = get_safe_file_path(invoice.xml_file)
            
            if not xml_absolute_path or not os.path.exists(xml_absolute_path):
                raise FileNotFoundError(f"Archivo XML no encontrado: {invoice.xml_file}")
            
            with open(xml_absolute_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            signer = XMLDigitalSigner()
            signed_xml = signer.sign_xml(xml_content, invoice.full_document_name)
            
            signed_filename = f"{invoice.full_document_name}_signed.xml"
            signed_file_path = os.path.join(settings.MEDIA_ROOT, 'xml_files', signed_filename)
            
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(signed_file_path), exist_ok=True)
            
            with open(signed_file_path, 'w', encoding='utf-8') as f:
                f.write(signed_xml)
            
            zip_filename = f"{invoice.full_document_name}.zip"
            zip_file_path = converter.create_zip_file(signed_file_path, zip_filename)
            
            # ✅ GUARDAR RUTAS NORMALIZADAS
            invoice.xml_file = save_file_path_normalized(signed_file_path)
            invoice.zip_file = save_file_path_normalized(zip_file_path)
            invoice.status = 'SIGNED'
            invoice.save()
            
            results['steps'].append({
                'step': 'digital_signature',
                'status': 'success',
                'message': 'XML firmado exitosamente',
                'signed_file_path': invoice.xml_file,
                'zip_file_path': invoice.zip_file
            })
        except Exception as e:
            results['steps'].append({
                'step': 'digital_signature',
                'status': 'error',
                'message': str(e)
            })
            raise e
        
        # Paso 3: Enviar a SUNAT
        try:
            sunat_client = SUNATWebServiceClient()
            zip_filename = f"{invoice.full_document_name}.zip"
            
            # ✅ OBTENER RUTA ABSOLUTA SEGURA
            zip_absolute_path = get_safe_file_path(invoice.zip_file)
            
            if not zip_absolute_path or not os.path.exists(zip_absolute_path):
                raise FileNotFoundError(f"Archivo ZIP no encontrado: {invoice.zip_file}")
            
            if invoice.document_type in ['01', '03']:
                response = sunat_client.send_bill(zip_absolute_path, zip_filename)
            else:
                response = sunat_client.send_summary(zip_absolute_path, zip_filename)
            
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
                        
                        # ✅ GUARDAR RUTA NORMALIZADA
                        invoice.cdr_file = save_file_path_normalized(cdr_path)
                
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
                # Manejar errores de SUNAT
                error_msg = response.get('error_message', 'Error desconocido')
                
                if '401' in error_msg or 'Unauthorized' in error_msg:
                    results['steps'].append({
                        'step': 'sunat_submission',
                        'status': 'warning',
                        'message': 'Error de autenticación SUNAT (normal con credenciales de prueba)',
                        'details': 'Documento generado y firmado correctamente. Error solo en autenticación.'
                    })
                    
                    invoice.sunat_response_description = 'Error 401 - Credenciales de prueba'
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
                results['steps'].append({
                    'step': 'sunat_submission',
                    'status': 'warning',
                    'message': 'Error de autenticación SUNAT (normal con credenciales de prueba)',
                    'technical_details': error_msg
                })
                
                invoice.sunat_response_description = 'Error 401 - Credenciales de prueba'
                invoice.save()
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
    """Prueba la conexión con SUNAT"""
    try:
        # Verificar configuración básica
        sunat_config = settings.SUNAT_CONFIG
        
        if not sunat_config.get('RUC'):
            return Response({
                'status': 'error',
                'message': 'Configuración SUNAT incompleta: RUC no configurado',
                'suggestion': 'Verifique el archivo .env'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            sunat_client = SUNATWebServiceClient()
            result = sunat_client.test_connection()
            
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
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_invoice_test_scenarios(request):
    """
    Crear escenarios de prueba con boleta completa
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
                'unit_price': Decimal('30.00'),
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
        
        # Usar numeración automática para evitar duplicados
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
                number=next_number,
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),  # Se calculará después
                observations=f'BOLETA DE PRUEBA #{next_number} - TODOS LOS ESCENARIOS'
            )
            
            # Línea 1: Producto gravado (S)
            line1_value = Decimal('2.00') * Decimal('100.00')  # 200.00
            line1_igv = line1_value * Decimal('0.18')  # 36.00
            
            InvoiceLine.objects.create(
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
            
            InvoiceLine.objects.create(
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
                tax_exemption_reason_code='20',
                igv_rate=Decimal('0.00'),
                igv_amount=Decimal('0.00')
            )
            
            # Línea 3: Producto gratuito (Z)
            InvoiceLine.objects.create(
                invoice=invoice,
                line_number=3,
                product=products[2],
                product_code=products[2].code,
                description=products[2].description + ' - BONIFICACION',
                quantity=Decimal('1.00'),
                unit_code='NIU',
                unit_price=Decimal('0.00'),
                line_extension_amount=Decimal('0.00'),
                reference_price=Decimal('30.00'),
                tax_category_code='Z',
                igv_rate=Decimal('0.00'),
                igv_amount=Decimal('0.00')
            )
            
            # Línea 4: Servicio con percepción
            line4_value = Decimal('1.00') * Decimal('1000.00')  # 1000.00
            line4_igv = line4_value * Decimal('0.18')  # 180.00
            
            InvoiceLine.objects.create(
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
            invoice.perception_code = '51'
            
            # Recalcular totales
            invoice.calculate_totals()
            
            # Agregar forma de pago
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code='009',
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

# ======================================================
# FUNCIONES ESPECÍFICAS DE ESCENARIOS - NUEVAS FUNCIONES
# ======================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def create_scenario_gravada(request):
    """Crea escenario específico: Boleta con Venta Gravada (IGV 18%)"""
    try:
        company, customer = _get_or_create_test_entities()
        
        with transaction.atomic():
            next_number = _get_next_invoice_number(company, '03', 'B001')
            
            invoice = Invoice.objects.create(
                company=company,
                customer=customer,
                document_type='03',
                series='B001',
                number=next_number,
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),
                observations='ESCENARIO 1: VENTA GRAVADA CON IGV 18%'
            )
            
            # Crear producto gravado
            product = _get_or_create_product(company, 'GRAV001', 'PRODUCTO GRAVADO CON IGV', Decimal('85.00'), 'S')
            
            # Línea gravada
            line_value = Decimal('2.00') * Decimal('85.00')  # 170.00
            igv_amount = line_value * Decimal('0.18')  # 30.60
            
            InvoiceLine.objects.create(
                invoice=invoice,
                line_number=1,
                product=product,
                product_code=product.code,
                description=product.description,
                quantity=Decimal('2.00'),
                unit_code='NIU',
                unit_price=Decimal('85.00'),
                line_extension_amount=line_value,
                tax_category_code='S',
                igv_rate=Decimal('18.00'),
                igv_amount=igv_amount
            )
            
            invoice.calculate_totals()
            
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code='009',
                payment_amount=invoice.total_amount
            )
        
        return Response({
            'status': 'success',
            'message': 'Escenario Gravada creado exitosamente',
            'scenario': 'gravada',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'totals': {
                'subtotal': float(invoice.total_taxed_amount),
                'igv': float(invoice.igv_amount),
                'total': float(invoice.total_amount)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando escenario gravada: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_scenario_exonerada(request):
    """Crea escenario específico: Boleta con Venta Exonerada (Sin IGV)"""
    try:
        company, customer = _get_or_create_test_entities()
        
        with transaction.atomic():
            next_number = _get_next_invoice_number(company, '03', 'B001')
            
            invoice = Invoice.objects.create(
                company=company,
                customer=customer,
                document_type='03',
                series='B001',
                number=next_number,
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),
                observations='ESCENARIO 2: VENTA EXONERADA SIN IGV'
            )
            
            # Crear producto exonerado
            product = _get_or_create_product(company, 'EXON001', 'PRODUCTO EXONERADO DE IGV', Decimal('120.00'), 'E')
            
            # Línea exonerada
            line_value = Decimal('1.00') * Decimal('120.00')  # 120.00
            
            InvoiceLine.objects.create(
                invoice=invoice,
                line_number=1,
                product=product,
                product_code=product.code,
                description=product.description,
                quantity=Decimal('1.00'),
                unit_code='NIU',
                unit_price=Decimal('120.00'),
                line_extension_amount=line_value,
                tax_category_code='E',
                tax_exemption_reason_code='20',
                igv_rate=Decimal('0.00'),
                igv_amount=Decimal('0.00')
            )
            
            invoice.calculate_totals()
            
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code='009',
                payment_amount=invoice.total_amount
            )
        
        return Response({
            'status': 'success',
            'message': 'Escenario Exonerada creado exitosamente',
            'scenario': 'exonerada',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'totals': {
                'subtotal': float(invoice.total_exempt_amount),
                'igv': float(invoice.igv_amount),
                'total': float(invoice.total_amount)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando escenario exonerada: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_scenario_percepcion(request):
    """Crea escenario específico: Boleta con Percepción (2% sobre servicios)"""
    try:
        company, customer = _get_or_create_test_entities()
        
        with transaction.atomic():
            next_number = _get_next_invoice_number(company, '03', 'B001')
            
            invoice = Invoice.objects.create(
                company=company,
                customer=customer,
                document_type='03',
                series='B001',
                number=next_number,
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),
                observations='ESCENARIO 3: SERVICIO CON PERCEPCION 2%'
            )
            
            # Crear servicio con percepción
            product = _get_or_create_product(company, 'SERV002', 'SERVICIO PROFESIONAL CON PERCEPCION', Decimal('1500.00'), 'S', 'ZZ')
            
            # Línea de servicio
            line_value = Decimal('1.00') * Decimal('1500.00')  # 1500.00
            igv_amount = line_value * Decimal('0.18')  # 270.00
            
            InvoiceLine.objects.create(
                invoice=invoice,
                line_number=1,
                product=product,
                product_code=product.code,
                description=product.description,
                quantity=Decimal('1.00'),
                unit_code='ZZ',
                unit_price=Decimal('1500.00'),
                line_extension_amount=line_value,
                tax_category_code='S',
                igv_rate=Decimal('18.00'),
                igv_amount=igv_amount
            )
            
            # Configurar percepción
            invoice.perception_percentage = Decimal('2.00')
            invoice.perception_base_amount = line_value
            invoice.perception_amount = invoice.perception_base_amount * (invoice.perception_percentage / 100)
            invoice.perception_code = '51'
            
            invoice.calculate_totals()
            
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code='009',
                payment_amount=invoice.total_amount
            )
        
        return Response({
            'status': 'success',
            'message': 'Escenario Percepción creado exitosamente',
            'scenario': 'percepcion',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'totals': {
                'subtotal': float(invoice.total_taxed_amount),
                'igv': float(invoice.igv_amount),
                'percepcion': float(invoice.perception_amount),
                'total': float(invoice.total_amount)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando escenario percepción: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_scenario_gratuito(request):
    """Crea escenario específico: Boleta con Producto Gratuito"""
    try:
        company, customer = _get_or_create_test_entities()
        
        with transaction.atomic():
            next_number = _get_next_invoice_number(company, '03', 'B001')
            
            invoice = Invoice.objects.create(
                company=company,
                customer=customer,
                document_type='03',
                series='B001',
                number=next_number,
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),
                observations='ESCENARIO 4: PRODUCTO GRATUITO - MUESTRA'
            )
            
            # Crear producto gratuito
            product = _get_or_create_product(company, 'GRAT001', 'PRODUCTO GRATUITO - MUESTRA', Decimal('0.00'), 'Z')
            
            # Línea gratuita
            InvoiceLine.objects.create(
                invoice=invoice,
                line_number=1,
                product=product,
                product_code=product.code,
                description=product.description + ' - PROMOCIONAL',
                quantity=Decimal('3.00'),
                unit_code='NIU',
                unit_price=Decimal('0.00'),
                line_extension_amount=Decimal('0.00'),
                reference_price=Decimal('25.00'),  # Precio de referencia
                tax_category_code='Z',
                igv_rate=Decimal('0.00'),
                igv_amount=Decimal('0.00')
            )
            
            invoice.calculate_totals()
            
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code='009',
                payment_amount=invoice.total_amount
            )
        
        return Response({
            'status': 'success',
            'message': 'Escenario Gratuito creado exitosamente',
            'scenario': 'gratuito',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'totals': {
                'subtotal': float(invoice.total_free_amount),
                'igv': float(invoice.igv_amount),
                'total': float(invoice.total_amount)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando escenario gratuito: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_scenario_bonificacion(request):
    """Crea escenario específico: Boleta con Bonificación"""
    try:
        company, customer = _get_or_create_test_entities()
        
        with transaction.atomic():
            next_number = _get_next_invoice_number(company, '03', 'B001')
            
            invoice = Invoice.objects.create(
                company=company,
                customer=customer,
                document_type='03',
                series='B001',
                number=next_number,
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),
                observations='ESCENARIO 5: VENTA CON BONIFICACION'
            )
            
            # Producto normal
            product1 = _get_or_create_product(company, 'NORM001', 'PRODUCTO NORMAL', Decimal('50.00'), 'S')
            
            # Línea normal (gravada)
            line1_value = Decimal('2.00') * Decimal('50.00')  # 100.00
            line1_igv = line1_value * Decimal('0.18')  # 18.00
            
            InvoiceLine.objects.create(
                invoice=invoice,
                line_number=1,
                product=product1,
                product_code=product1.code,
                description=product1.description,
                quantity=Decimal('2.00'),
                unit_code='NIU',
                unit_price=Decimal('50.00'),
                line_extension_amount=line1_value,
                tax_category_code='S',
                igv_rate=Decimal('18.00'),
                igv_amount=line1_igv
            )
            
            # Producto bonificación
            product2 = _get_or_create_product(company, 'BONI001', 'PRODUCTO BONIFICACION', Decimal('0.00'), 'Z')
            
            # Línea bonificación (gratuita)
            InvoiceLine.objects.create(
                invoice=invoice,
                line_number=2,
                product=product2,
                product_code=product2.code,
                description=product2.description + ' - POR COMPRA',
                quantity=Decimal('1.00'),
                unit_code='NIU',
                unit_price=Decimal('0.00'),
                line_extension_amount=Decimal('0.00'),
                reference_price=Decimal('50.00'),  # Precio de referencia
                tax_category_code='Z',
                igv_rate=Decimal('0.00'),
                igv_amount=Decimal('0.00')
            )
            
            invoice.calculate_totals()
            
            InvoicePayment.objects.create(
                invoice=invoice,
                payment_means_code='009',
                payment_amount=invoice.total_amount
            )
        
        return Response({
            'status': 'success',
            'message': 'Escenario Bonificación creado exitosamente',
            'scenario': 'bonificacion',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'totals': {
                'subtotal_gravado': float(invoice.total_taxed_amount),
                'subtotal_gratuito': float(invoice.total_free_amount),
                'igv': float(invoice.igv_amount),
                'total': float(invoice.total_amount)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando escenario bonificación: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_all_test_scenarios(request):
    """Crea todos los escenarios de prueba de una vez"""
    try:
        results = []
        scenarios = ['gravada', 'exonerada', 'percepcion', 'gratuito', 'bonificacion']
        
        for scenario in scenarios:
            try:
                if scenario == 'gravada':
                    response = create_scenario_gravada(request)
                elif scenario == 'exonerada':
                    response = create_scenario_exonerada(request)
                elif scenario == 'percepcion':
                    response = create_scenario_percepcion(request)
                elif scenario == 'gratuito':
                    response = create_scenario_gratuito(request)
                elif scenario == 'bonificacion':
                    response = create_scenario_bonificacion(request)
                
                if response.status_code == 201:
                    results.append({
                        'scenario': scenario,
                        'status': 'success',
                        'data': response.data
                    })
                else:
                    results.append({
                        'scenario': scenario,
                        'status': 'error',
                        'message': response.data.get('message', 'Error desconocido')
                    })
                    
            except Exception as e:
                results.append({
                    'scenario': scenario,
                    'status': 'error',
                    'message': str(e)
                })
        
        successful = sum(1 for r in results if r['status'] == 'success')
        
        return Response({
            'status': 'success',
            'message': f'{successful} de {len(scenarios)} escenarios creados exitosamente',
            'results': results,
            'summary': {
                'total': len(scenarios),
                'successful': successful,
                'failed': len(scenarios) - successful
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creando todos los escenarios: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_test_data(request):
    """Resetea y limpia datos de prueba"""
    try:
        # Obtener empresa de prueba
        company = Company.objects.filter(ruc=settings.SUNAT_CONFIG['RUC']).first()
        
        if not company:
            return Response({
                'status': 'warning',
                'message': 'No hay datos de prueba para limpiar'
            })
        
        # Contar registros antes
        invoices_count = Invoice.objects.filter(company=company).count()
        customers_count = Customer.objects.filter(company=company).count()
        products_count = Product.objects.filter(company=company).count()
        
        # Eliminar datos de prueba
        with transaction.atomic():
            Invoice.objects.filter(company=company).delete()
            Customer.objects.filter(company=company).delete()
            Product.objects.filter(company=company).delete()
            company.delete()
        
        return Response({
            'status': 'success',
            'message': 'Datos de prueba eliminados exitosamente',
            'deleted': {
                'invoices': invoices_count,
                'customers': customers_count,
                'products': products_count,
                'companies': 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error reseteando datos de prueba: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def process_complete_scenario(request, scenario_type):
    """Procesa escenario completo (crear + procesar)"""
    try:
        # Crear el escenario
        if scenario_type == 'gravada':
            create_response = create_scenario_gravada(request)
        elif scenario_type == 'exonerada':
            create_response = create_scenario_exonerada(request)
        elif scenario_type == 'percepcion':
            create_scenario_percepcion(request)
        elif scenario_type == 'gratuito':
            create_response = create_scenario_gratuito(request)
        elif scenario_type == 'bonificacion':
            create_response = create_scenario_bonificacion(request)
        else:
            return Response({
                'status': 'error',
                'message': f'Tipo de escenario no válido: {scenario_type}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if create_response.status_code != 201:
            return create_response
        
        # Obtener el ID de la factura creada
        invoice_id = create_response.data['invoice_id']
        
        # Procesar flujo completo
        process_response = process_complete_flow(request, invoice_id)
        
        # Combinar resultados
        return Response({
            'status': 'success',
            'message': f'Escenario {scenario_type} creado y procesado',
            'scenario_type': scenario_type,
            'creation_result': create_response.data,
            'processing_result': process_response.data
        })
        
    except Exception as e:
        logger.error(f"Error procesando escenario completo {scenario_type}: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_scenario_info(request, scenario_type):
    """Información detallada de escenarios"""
    scenario_info = {
        'gravada': {
            'name': 'Venta Gravada',
            'description': 'Boleta con productos gravados con IGV 18%',
            'tax_category': 'S - Gravado',
            'igv_rate': '18%',
            'characteristics': [
                'Productos sujetos a IGV',
                'Aplica tarifa del 18%',
                'Base imponible = Valor de venta',
                'Total = Subtotal + IGV'
            ]
        },
        'exonerada': {
            'name': 'Venta Exonerada',
            'description': 'Boleta con productos exonerados de IGV',
            'tax_category': 'E - Exonerado',
            'igv_rate': '0%',
            'characteristics': [
                'Productos exonerados por ley',
                'No pagan IGV',
                'Código de exoneración requerido',
                'Total = Subtotal sin IGV'
            ]
        },
        'percepcion': {
            'name': 'Venta con Percepción',
            'description': 'Servicio con percepción del 2%',
            'tax_category': 'S - Gravado + Percepción',
            'igv_rate': '18% + 2% percepción',
            'characteristics': [
                'Servicios sujetos a percepción',
                'IGV del 18% + Percepción del 2%',
                'Aplica a servicios específicos',
                'Total = Subtotal + IGV + Percepción'
            ]
        },
        'gratuito': {
            'name': 'Producto Gratuito',
            'description': 'Productos entregados sin costo',
            'tax_category': 'Z - Gratuito',
            'igv_rate': '0%',
            'characteristics': [
                'Productos sin costo',
                'Precio de referencia requerido',
                'No genera IGV',
                'Total = 0.00'
            ]
        },
        'bonificacion': {
            'name': 'Venta con Bonificación',
            'description': 'Venta normal + producto bonificado',
            'tax_category': 'S + Z - Mixto',
            'igv_rate': '18% + 0%',
            'characteristics': [
                'Combina productos pagados y gratuitos',
                'IGV solo sobre productos pagados',
                'Bonificación con precio de referencia',
                'Total = Subtotal pagado + IGV'
            ]
        }
    }
    
    if scenario_type not in scenario_info:
        return Response({
            'status': 'error',
            'message': f'Tipo de escenario no válido: {scenario_type}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'status': 'success',
        'scenario_type': scenario_type,
        'info': scenario_info[scenario_type],
        'available_scenarios': list(scenario_info.keys())
    })

# =====================================================
# FUNCIONES AUXILIARES Y DE UTILIDAD
# =====================================================

def _get_or_create_test_entities():
    """Obtiene o crea entidades de prueba (empresa y cliente)"""
    # Empresa
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
    
    # Cliente
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
    
    return company, customer

def _get_next_invoice_number(company, document_type, series):
    """Obtiene el siguiente número de factura disponible"""
    existing_invoice = Invoice.objects.filter(
        company=company,
        document_type=document_type,
        series=series
    ).order_by('-number').first()
    
    return (existing_invoice.number + 1) if existing_invoice else 1

def _get_or_create_product(company, code, description, unit_price, tax_category_code, unit_code='NIU'):
    """Obtiene o crea un producto de prueba"""
    product, created = Product.objects.get_or_create(
        company=company,
        code=code,
        defaults={
            'description': description,
            'unit_price': unit_price,
            'is_taxed': tax_category_code == 'S',
            'is_free': tax_category_code == 'Z',
            'tax_category_code': tax_category_code,
            'unit_code': unit_code
        }
    )
    return product

# =====================================================
# FUNCIONES YA EXISTENTES - MANTENER SIN CAMBIOS
# =====================================================

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
            
            # Crear líneas de detalle
            lines_data = data.get('lines', [])
            for i, line_data in enumerate(lines_data, 1):
                # Extraer datos de la línea
                tax_category_code = line_data.get('tax_category_code', 'S')
                quantity = Decimal(str(line_data.get('quantity', 1)))
                unit_price = Decimal(str(line_data.get('unit_price', 0)))
                product_code = line_data.get('product_code', f'PROD{str(i).zfill(3)}')
                description = line_data.get('description', f'Producto {i}')
                line_number = line_data.get('line_number', i)
                
                # Calcular montos según tipo de impuesto
                if tax_category_code == 'Z':  # Gratuito
                    line_extension_amount = Decimal('0.00')
                    reference_price = unit_price if unit_price > 0 else Decimal('0.00')
                    actual_unit_price = Decimal('0.00')
                    igv_amount = Decimal('0.00')
                    igv_rate = Decimal('0.00')
                else:
                    line_extension_amount = quantity * unit_price
                    reference_price = Decimal('0.00')
                    actual_unit_price = unit_price
                    if tax_category_code == 'S':  # Gravado
                        igv_rate = Decimal('18.00')
                        igv_amount = line_extension_amount * Decimal('0.18')
                    else:  # Exonerado/Inafecto
                        igv_rate = Decimal('0.00')
                        igv_amount = Decimal('0.00')
                
                # Determinar código de exoneración si aplica
                tax_exemption_reason_code = None
                if tax_category_code in ['E', 'O']:
                    tax_exemption_reason_code = '20'
                
                # Crear línea de detalle
                InvoiceLine.objects.create(
                    invoice=invoice,
                    line_number=line_number,
                    product_code=product_code,
                    description=description,
                    quantity=quantity,
                    unit_code='NIU',
                    unit_price=actual_unit_price,
                    reference_price=reference_price,
                    line_extension_amount=line_extension_amount,
                    tax_category_code=tax_category_code,
                    igv_rate=igv_rate,
                    igv_amount=igv_amount,
                    tax_exemption_reason_code=tax_exemption_reason_code
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
        invoices = Invoice.objects.all().order_by('-created_at')[:50]
        
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
    """Obtener contenido de archivo XML, ZIP o CDR - VERSIÓN ULTRA-CORREGIDA"""
    try:
        file_path = request.GET.get('path')
        if not file_path:
            return Response({
                'status': 'error',
                'message': 'Parámetro path requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"📄 Solicitud de archivo: {file_path}")
        
        # ✅ VALIDACIONES MEJORADAS
        if file_path in ['true', 'false'] or len(file_path.strip()) < 3:
            return Response({
                'status': 'error',
                'message': f'Path inválido: "{file_path}"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ DECODIFICACIÓN SEGURA
        try:
            file_path = urllib.parse.unquote(file_path)
            logger.info(f"📄 Ruta decodificada: {file_path}")
        except Exception as decode_error:
            logger.error(f"Error decodificando ruta: {decode_error}")
            return Response({
                'status': 'error',
                'message': f'Error en formato de ruta: {str(decode_error)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ OBTENER RUTA ABSOLUTA USANDO FUNCIÓN CORREGIDA
        full_path = get_safe_file_path(file_path)
        
        if not full_path:
            logger.warning(f"❌ Archivo no encontrado con ruta segura: {file_path}")
            
            # ✅ BÚSQUEDA INTELIGENTE DE RESPALDO
            filename = os.path.basename(file_path)
            if not filename or '.' not in filename:
                # Intentar extraer filename de ruta malformada
                filename = repair_file_path(file_path)
            
            if filename and '.' in filename:
                logger.info(f"🔍 Buscando archivo por nombre: {filename}")
                found_path = find_file_in_media(filename)
                
                if found_path:
                    full_path = found_path
                    logger.info(f"✅ Archivo encontrado: {found_path}")
                else:
                    logger.error(f"❌ Archivo no encontrado: {filename}")
                    return Response({
                        'status': 'error',
                        'message': f'Archivo no encontrado: {filename}',
                        'original_path': file_path,
                        'searched_filename': filename
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'status': 'error',
                    'message': f'No se pudo extraer nombre de archivo válido de: {file_path}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ VERIFICACIÓN FINAL DE EXISTENCIA
        if not os.path.exists(full_path):
            logger.error(f"❌ Archivo no existe en ruta final: {full_path}")
            return Response({
                'status': 'error',
                'message': f'Archivo no existe: {os.path.basename(full_path)}',
                'resolved_path': full_path
            }, status=status.HTTP_404_NOT_FOUND)
        
        # ✅ PROCESAMIENTO SEGURO DEL ARCHIVO
        file_extension = os.path.splitext(full_path)[1].lower()
        file_size = os.path.getsize(full_path)
        
        logger.info(f"📄 Procesando archivo {file_extension} de {file_size} bytes: {full_path}")
        
        try:
            if file_extension == '.xml':
                return process_xml_file(full_path, file_size)
            elif file_extension == '.zip':
                return process_zip_file(full_path, file_size)
            else:
                return process_other_file(full_path, file_size)
                
        except Exception as process_error:
            logger.error(f"❌ Error procesando archivo {file_extension}: {process_error}")
            return Response({
                'status': 'error',
                'message': f'Error procesando archivo: {str(process_error)}',
                'file_type': file_extension,
                'file_path': full_path
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"❌ Error crítico en get_file_content: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error interno del servidor: {str(e)}',
            'path_requested': request.GET.get('path', 'N/A')
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def process_xml_file(file_path, file_size):
    """Procesa archivos XML de forma segura"""
    try:
        # Intentar diferentes codificaciones
        content = None
        encoding_used = None
        
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                encoding_used = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            return Response({
                'status': 'error',
                'message': 'No se pudo leer el archivo XML con ninguna codificación'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar si es XML válido
        is_valid_xml = True
        xml_error = None
        try:
            ET.fromstring(content)
        except ET.ParseError as e:
            is_valid_xml = False
            xml_error = str(e)
        
        # Verificar si está firmado
        is_signed = '<ds:Signature' in content or 'http://www.w3.org/2000/09/xmldsig#' in content
        
        response_data = {
            'status': 'success',
            'content': content,
            'file_type': 'xml',
            'file_name': os.path.basename(file_path),
            'is_signed': is_signed,
            'is_valid_xml': is_valid_xml,
            'size': len(content),
            'encoding': encoding_used
        }
        
        if xml_error:
            response_data['xml_error'] = xml_error
        
        logger.info(f"✅ XML procesado: {len(content)} caracteres, firmado: {is_signed}, válido: {is_valid_xml}")
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error procesando XML: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error procesando archivo XML: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def process_zip_file(file_path, file_size):
    """Procesa archivos ZIP de forma segura"""
    try:
        zip_contents = []
        xml_content = None
        
        # Verificar que el archivo ZIP no esté corrupto
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Verificar integridad
                zip_ref.testzip()
                
                # Obtener información de archivos
                for file_info in zip_ref.filelist:
                    zip_contents.append({
                        'filename': file_info.filename,
                        'size': file_info.file_size,
                        'compressed_size': file_info.compress_size,
                        'date': f"{file_info.date_time[0]}-{file_info.date_time[1]:02d}-{file_info.date_time[2]:02d}",
                        'compression_type': file_info.compress_type
                    })
                
                # Buscar y extraer XML
                xml_files = [f for f in zip_ref.namelist() if f.lower().endswith('.xml')]
                
                if xml_files:
                    xml_filename = xml_files[0]
                    try:
                        with zip_ref.open(xml_filename) as xml_file:
                            xml_bytes = xml_file.read()
                            
                            # Intentar decodificar el XML
                            for encoding in ['utf-8', 'utf-8-sig', 'latin-1']:
                                try:
                                    xml_content = xml_bytes.decode(encoding)
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if xml_content is None:
                                xml_content = "Error: No se pudo decodificar el XML"
                        
                        logger.info(f"✅ XML extraído del ZIP: {xml_filename}")
                    except Exception as xml_error:
                        logger.warning(f"⚠️ Error leyendo XML del ZIP: {xml_error}")
                        xml_content = f"Error leyendo {xml_filename}: {str(xml_error)}"
                
        except zipfile.BadZipFile:
            logger.error(f"❌ Archivo ZIP corrupto: {file_path}")
            return Response({
                'status': 'error',
                'message': 'Archivo ZIP corrupto o dañado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        response_data = {
            'status': 'success',
            'file_type': 'zip',
            'file_name': os.path.basename(file_path),
            'contents': zip_contents,
            'xml_content': xml_content,
            'size': file_size,
            'contains_xml': len(xml_files) > 0 if 'xml_files' in locals() else False
        }
        
        logger.info(f"✅ ZIP procesado exitosamente: {len(zip_contents)} archivos")
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error procesando ZIP: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error procesando archivo ZIP: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def process_other_file(file_path, file_size):
    """Procesa otros tipos de archivo"""
    try:
        # Intentar leer como texto
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return Response({
                'status': 'success',
                'content': content,
                'file_type': 'text',
                'file_name': os.path.basename(file_path),
                'size': file_size,
                'encoding': 'utf-8'
            })
            
        except UnicodeDecodeError:
            # Si no es texto, leer como binario
            try:
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                
                import base64
                content = base64.b64encode(binary_content).decode('utf-8')
                
                return Response({
                    'status': 'success',
                    'content': content,
                    'file_type': 'binary',
                    'file_name': os.path.basename(file_path),
                    'size': file_size,
                    'encoding': 'base64'
                })
                
            except Exception as binary_error:
                logger.error(f"❌ Error leyendo archivo binario: {binary_error}")
                return Response({
                    'status': 'error',
                    'message': f'Error leyendo archivo: {str(binary_error)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    except Exception as e:
        logger.error(f"❌ Error procesando archivo: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error procesando archivo: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def validate_xml_signature(request):
    """Valida la firma digital de un XML"""
    try:
        xml_content = request.data.get('xml_content')
        if not xml_content:
            return Response({
                'status': 'error',
                'message': 'Contenido XML requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from digital_signature.signer import XMLDigitalSigner
        signer = XMLDigitalSigner()
        
        is_valid, message = signer.verify_signature(xml_content)
        cert_info = signer.get_certificate_info()
        
        return Response({
            'status': 'success',
            'is_valid': is_valid,
            'message': message,
            'certificate_info': cert_info,
            'validation_details': {
                'has_signature': '<ds:Signature' in xml_content,
                'signature_algorithm': 'RSA-SHA1' if 'rsa-sha1' in xml_content else 'Unknown',
                'canonicalization': 'C14N' if 'c14n' in xml_content else 'Unknown'
            }
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Error validando firma: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def convert_to_ubl(request, invoice_id):
    """Convierte una factura a XML UBL 2.1"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        converter = UBLConverter()
        xml_content = converter.convert_invoice_to_xml(invoice)
        
        xml_filename = f"{invoice.full_document_name}.xml"
        xml_file_path = converter.save_xml_to_file(xml_content, xml_filename)
        
        # ✅ GUARDAR RUTA NORMALIZADA
        invoice.xml_file = save_file_path_normalized(xml_file_path)
        invoice.status = 'PROCESSING'
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'XML UBL generado exitosamente',
            'invoice_id': invoice.id,
            'xml_filename': xml_filename,
            'xml_path': invoice.xml_file,
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
                'message': 'Primero debe generar el XML UBL',
                'suggestion': 'Use el endpoint /convert-ubl/ antes de firmar',
                'invoice_id': invoice_id,
                'current_status': invoice.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ OBTENER RUTA ABSOLUTA SEGURA
        xml_absolute_path = get_safe_file_path(invoice.xml_file)
        
        if not xml_absolute_path or not os.path.exists(xml_absolute_path):
            logger.error(f"Archivo XML no encontrado: {invoice.xml_file} -> {xml_absolute_path}")
            return Response({
                'status': 'error',
                'message': 'Archivo XML no encontrado en el sistema',
                'suggestion': 'Regenere el XML UBL',
                'invoice_id': invoice_id
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Leer contenido del XML
        try:
            with open(xml_absolute_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except Exception as e:
            logger.error(f"Error leyendo archivo XML {xml_absolute_path}: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error leyendo archivo XML: {str(e)}',
                'invoice_id': invoice_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Proceder con la firma
        signer = XMLDigitalSigner()
        signed_xml = signer.sign_xml(xml_content, invoice.full_document_name)
        
        signed_filename = f"{invoice.full_document_name}_signed.xml"
        signed_file_path = os.path.join(settings.MEDIA_ROOT, 'xml_files', signed_filename)
        
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(signed_file_path), exist_ok=True)
        
        with open(signed_file_path, 'w', encoding='utf-8') as f:
            f.write(signed_xml)
        
        converter = UBLConverter()
        zip_filename = f"{invoice.full_document_name}.zip"
        zip_file_path = converter.create_zip_file(signed_file_path, zip_filename)
        
        # ✅ GUARDAR RUTAS NORMALIZADAS
        invoice.xml_file = save_file_path_normalized(signed_file_path)
        invoice.zip_file = save_file_path_normalized(zip_file_path)
        invoice.status = 'SIGNED'
        invoice.save()
        
        logger.info(f"XML firmado exitosamente para invoice {invoice_id}")
        
        return Response({
            'status': 'success',
            'message': 'XML firmado exitosamente',
            'invoice_id': invoice.id,
            'signed_xml_path': invoice.xml_file,
            'zip_path': invoice.zip_file,
            'certificate_info': signer.get_certificate_info()
        })
        
    except Exception as e:
        logger.error(f"Error firmando XML para invoice {invoice_id}: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error interno: {str(e)}',
            'invoice_id': invoice_id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_to_sunat(request, invoice_id):
    """Envía documento firmado a SUNAT"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if not invoice.zip_file:
            return Response({
                'status': 'error',
                'message': 'Primero debe firmar el XML',
                'suggestion': 'Use el endpoint /sign/ antes de enviar a SUNAT',
                'invoice_id': invoice_id,
                'current_status': invoice.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ OBTENER RUTA ABSOLUTA SEGURA
        zip_absolute_path = get_safe_file_path(invoice.zip_file)
        
        if not zip_absolute_path or not os.path.exists(zip_absolute_path):
            return Response({
                'status': 'error',
                'message': 'Archivo ZIP no encontrado',
                'invoice_id': invoice_id
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            sunat_client = SUNATWebServiceClient()
            zip_filename = f"{invoice.full_document_name}.zip"
            
            if invoice.document_type in ['01', '03']:
                response = sunat_client.send_bill(zip_absolute_path, zip_filename)
            else:
                response = sunat_client.send_summary(zip_absolute_path, zip_filename)
            
        except Exception as sunat_error:
            error_msg = str(sunat_error)
            logger.warning(f"Error SUNAT para invoice {invoice_id}: {error_msg}")
            
            if "401" in error_msg or "Unauthorized" in error_msg:
                invoice.status = 'SIGNED'
                invoice.sunat_response_description = 'Error 401 - Credenciales de prueba (normal en ambiente BETA)'
                invoice.save()
                
                return Response({
                    'status': 'warning',
                    'message': 'Error de autenticación SUNAT (normal con credenciales de prueba)',
                    'invoice_id': invoice.id,
                    'sunat_response': {
                        'status': 'auth_error',
                        'error_message': 'Error 401 - Credenciales MODDATOS no válidas para envío real',
                        'note': 'El documento se generó y firmó correctamente. Error solo en envío a SUNAT.',
                        'environment': 'BETA' if settings.SUNAT_CONFIG.get('USE_BETA') else 'PRODUCCIÓN'
                    },
                    'suggestion': 'Para envío real a SUNAT necesitas credenciales válidas de producción'
                })
            else:
                invoice.status = 'ERROR'
                invoice.sunat_response_description = error_msg
                invoice.save()
                
                return Response({
                    'status': 'error',
                    'message': f'Error en cliente SUNAT: {error_msg}',
                    'invoice_id': invoice.id
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Procesar respuesta exitosa
        if response and response.get('status') in ['success', 'warning']:
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
                        
                        # ✅ GUARDAR RUTA NORMALIZADA
                        invoice.cdr_file = save_file_path_normalized(cdr_path)
                
                elif response.get('response_type') == 'ticket':
                    invoice.sunat_ticket = response.get('ticket')
                
                invoice.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Documento enviado a SUNAT exitosamente',
                    'invoice_id': invoice.id,
                    'sunat_response': response,
                    'invoice_status': invoice.status
                })
        
        return Response({
            'status': 'error',
            'message': 'Error procesando respuesta de SUNAT',
            'invoice_id': invoice.id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error enviando a SUNAT invoice {invoice_id}: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error interno: {str(e)}',
            'invoice_id': invoice_id
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
        
        sunat_client = SUNATWebServiceClient()
        response = sunat_client.get_status(invoice.sunat_ticket)
        
        if response['status'] == 'success':
            processing_status = response.get('processing_status')
            
            if processing_status == 'completed':
                invoice.status = 'ACCEPTED'
                invoice.sunat_response_code = '0'
                invoice.sunat_response_description = 'Procesado correctamente'
                
                if response.get('content'):
                    cdr_filename = f"R-{invoice.full_document_name}.zip"
                    cdr_path = os.path.join(settings.MEDIA_ROOT, 'cdr_files', cdr_filename)
                    os.makedirs(os.path.dirname(cdr_path), exist_ok=True)
                    
                    import base64
                    with open(cdr_path, 'wb') as f:
                        f.write(base64.b64decode(response['content']))
                    
                    # ✅ GUARDAR RUTA NORMALIZADA
                    invoice.cdr_file = save_file_path_normalized(cdr_path)
                
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
                'status': 'error',
                'message': response.get('error_message'),
                'invoice_id': invoice.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error consultando estado SUNAT: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def get_signature_info(request):
    """Extrae y devuelve información detallada de la firma digital de un XML"""
    try:
        xml_content = request.data.get('xml_content')
        file_path = request.data.get('file_path')
        
        # Obtener contenido XML
        if xml_content:
            xml_data = xml_content
        elif file_path:
            # ✅ OBTENER RUTA ABSOLUTA SEGURA
            absolute_path = get_safe_file_path(file_path)
            
            if not absolute_path or not os.path.exists(absolute_path):
                return Response({
                    'status': 'error',
                    'message': 'Archivo XML no encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            with open(absolute_path, 'r', encoding='utf-8') as f:
                xml_data = f.read()
        else:
            return Response({
                'status': 'error',
                'message': 'Se requiere xml_content o file_path'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from digital_signature.signer import XMLDigitalSigner
        signer = XMLDigitalSigner()
        
        # Extraer información de la firma
        signature_info = signer.extract_signature_info(xml_data)
        
        if not signature_info:
            return Response({
                'status': 'error',
                'message': 'No se pudo extraer información de la firma'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar la firma
        is_valid, validation_message = signer.verify_signature(xml_data)
        
        return Response({
            'status': 'success',
            'signature_info': signature_info,
            'validation': {
                'is_valid': is_valid,
                'message': validation_message
            },
            'has_signature': signature_info.get('signature_found', False)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo información de firma: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)