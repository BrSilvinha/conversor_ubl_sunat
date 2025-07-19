# api/views.py - VERSIÓN MULTI-USUARIO CON AUTENTICACIÓN
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse, Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
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

# ==================== AUTENTICACIÓN ====================
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def login_user(request):
    """Login de usuario"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'status': 'error',
                'message': 'Usuario y contraseña requeridos'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return Response({
                'status': 'success',
                'message': 'Login exitoso',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout de usuario"""
    try:
        logout(request)
        return Response({
            'status': 'success',
            'message': 'Logout exitoso'
        })
    except Exception as e:
        logger.error(f"Error en logout: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Obtiene información del usuario actual"""
    try:
        user = request.user
        return Response({
            'status': 'success',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            }
        })
    except Exception as e:
        logger.error(f"Error obteniendo usuario actual: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def register_user(request):
    """Registro de nuevo usuario"""
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if not username or not email or not password:
            return Response({
                'status': 'error',
                'message': 'Usuario, email y contraseña son requeridos'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({
                'status': 'error',
                'message': 'El usuario ya existe'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'status': 'error',
                'message': 'El email ya está registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        return Response({
            'status': 'success',
            'message': 'Usuario registrado exitosamente',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error en registro: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== FUNCIONES AUXILIARES ====================
def get_user_companies(user):
    """Obtiene las empresas del usuario actual"""
    if user.is_superuser:
        return Company.objects.all()
    else:
        # Por simplicidad, cada usuario tendrá una empresa basada en su username
        # En un sistema real, tendrías una relación Many-to-Many
        company, created = Company.objects.get_or_create(
            ruc=f"2{str(user.id).zfill(10)}"[:11],  # Generar RUC único basado en user ID
            defaults={
                'business_name': f'EMPRESA {user.username.upper()} SAC',
                'trade_name': f'EMPRESA {user.username.upper()}',
                'address': 'AV. PRINCIPAL 123',
                'district': 'LIMA',
                'province': 'LIMA',
                'department': 'LIMA',
                'ubigeo': '150101',
                'certificate_path': settings.SUNAT_CONFIG['CERTIFICATE_PATH'],
                'certificate_password': settings.SUNAT_CONFIG['CERTIFICATE_PASSWORD']
            }
        )
        return Company.objects.filter(id=company.id)

def get_user_invoices(user):
    """Obtiene las facturas del usuario actual"""
    companies = get_user_companies(user)
    return Invoice.objects.filter(company__in=companies)

# ==================== VISTAS PRINCIPALES ====================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_complete_flow(request, invoice_id):
    """Procesa el flujo completo: UBL → Firma → Envío SUNAT"""
    try:
        # Verificar que la factura pertenece al usuario
        user_invoices = get_user_invoices(request.user)
        invoice = get_object_or_404(user_invoices, id=invoice_id)
        
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
            xml_absolute_path = get_safe_file_path(invoice.xml_file)
            
            if not xml_absolute_path or not os.path.exists(xml_absolute_path):
                raise FileNotFoundError(f"Archivo XML no encontrado: {invoice.xml_file}")
            
            with open(xml_absolute_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            signer = XMLDigitalSigner()
            signed_xml = signer.sign_xml(xml_content, invoice.full_document_name)
            
            signed_filename = f"{invoice.full_document_name}_signed.xml"
            signed_file_path = os.path.join(settings.MEDIA_ROOT, 'xml_files', signed_filename)
            
            os.makedirs(os.path.dirname(signed_file_path), exist_ok=True)
            
            with open(signed_file_path, 'w', encoding='utf-8') as f:
                f.write(signed_xml)
            
            zip_filename = f"{invoice.full_document_name}.zip"
            zip_file_path = converter.create_zip_file(signed_file_path, zip_filename)
            
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
@permission_classes([IsAuthenticated])
def get_invoice_status(request, invoice_id):
    """Obtiene el estado actual de una factura"""
    try:
        user_invoices = get_user_invoices(request.user)
        invoice = get_object_or_404(user_invoices, id=invoice_id)
        
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
@permission_classes([IsAuthenticated])
def create_invoice_test_scenarios(request):
    """Crear escenarios de prueba con boleta completa"""
    try:
        # Obtener empresa del usuario
        companies = get_user_companies(request.user)
        company = companies.first()
        
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
                document_type='03',
                series='B001',
                number=next_number,
                issue_date=date.today(),
                currency_code='PEN',
                operation_type_code='0101',
                total_amount=Decimal('0.00'),
                observations=f'BOLETA DE PRUEBA #{next_number} - USUARIO: {request.user.username}'
            )
            
            # Líneas de detalle (mismo código anterior)
            line1_value = Decimal('2.00') * Decimal('100.00')
            line1_igv = line1_value * Decimal('0.18')
            
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
            
            line2_value = Decimal('1.00') * Decimal('50.00')
            
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
            
            line4_value = Decimal('1.00') * Decimal('1000.00')
            line4_igv = line4_value * Decimal('0.18')
            
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
            
            invoice.perception_percentage = Decimal('2.00')
            invoice.perception_base_amount = Decimal('1000.00')
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
            'message': 'Escenarios de prueba creados exitosamente',
            'invoice_id': invoice.id,
            'invoice_reference': invoice.full_document_name,
            'number_generated': next_number,
            'user': request.user.username,
            'company': company.business_name,
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_documents(request):
    """Listar documentos del usuario"""
    try:
        user_invoices = get_user_invoices(request.user)
        invoices = user_invoices.order_by('-created_at')[:50]
        
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
            'count': len(documents),
            'user': request.user.username
        })
        
    except Exception as e:
        logger.error(f"Error listando documentos: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== RESTO DE VISTAS (igual que antes pero con autenticación) ====================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_file_content(request):
    """Obtener contenido de archivo XML, ZIP o CDR"""
    try:
        file_path = request.GET.get('path')
        if not file_path:
            return Response({
                'status': 'error',
                'message': 'Parámetro path requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"📄 Solicitud de archivo: {file_path}")
        
        if file_path in ['true', 'false'] or len(file_path.strip()) < 3:
            return Response({
                'status': 'error',
                'message': f'Path inválido: "{file_path}"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            file_path = urllib.parse.unquote(file_path)
            logger.info(f"📄 Ruta decodificada: {file_path}")
        except Exception as decode_error:
            logger.error(f"Error decodificando ruta: {decode_error}")
            return Response({
                'status': 'error',
                'message': f'Error en formato de ruta: {str(decode_error)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        full_path = get_safe_file_path(file_path)
        
        if not full_path:
            logger.warning(f"❌ Archivo no encontrado con ruta segura: {file_path}")
            
            filename = os.path.basename(file_path)
            if not filename or '.' not in filename:
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
        
        if not os.path.exists(full_path):
            logger.error(f"❌ Archivo no existe en ruta final: {full_path}")
            return Response({
                'status': 'error',
                'message': f'Archivo no existe: {os.path.basename(full_path)}',
                'resolved_path': full_path
            }, status=status.HTTP_404_NOT_FOUND)
        
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

# Funciones auxiliares para procesar archivos (mismas que antes)
def process_xml_file(file_path, file_size):
    """Procesa archivos XML de forma segura"""
    try:
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
        
        is_valid_xml = True
        xml_error = None
        try:
            ET.fromstring(content)
        except ET.ParseError as e:
            is_valid_xml = False
            xml_error = str(e)
        
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
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.testzip()
                
                for file_info in zip_ref.filelist:
                    zip_contents.append({
                        'filename': file_info.filename,
                        'size': file_info.file_size,
                        'compressed_size': file_info.compress_size,
                        'date': f"{file_info.date_time[0]}-{file_info.date_time[1]:02d}-{file_info.date_time[2]:02d}",
                        'compression_type': file_info.compress_type
                    })
                
                xml_files = [f for f in zip_ref.namelist() if f.lower().endswith('.xml')]
                
                if xml_files:
                    xml_filename = xml_files[0]
                    try:
                        with zip_ref.open(xml_filename) as xml_file:
                            xml_bytes = xml_file.read()
                            
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

# Agregar las demás vistas con autenticación...
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_to_ubl(request, invoice_id):
    """Convierte una factura a XML UBL 2.1"""
    try:
        user_invoices = get_user_invoices(request.user)
        invoice = get_object_or_404(user_invoices, id=invoice_id)
        
        converter = UBLConverter()
        xml_content = converter.convert_invoice_to_xml(invoice)
        
        xml_filename = f"{invoice.full_document_name}.xml"
        xml_file_path = converter.save_xml_to_file(xml_content, xml_filename)
        
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
@permission_classes([IsAuthenticated])
def sign_xml(request, invoice_id):
    """Firma digitalmente el XML de una factura"""
    try:
        user_invoices = get_user_invoices(request.user)
        invoice = get_object_or_404(user_invoices, id=invoice_id)
        
        if not invoice.xml_file:
            return Response({
                'status': 'error',
                'message': 'Primero debe generar el XML UBL',
                'suggestion': 'Use el endpoint /convert-ubl/ antes de firmar',
                'invoice_id': invoice_id,
                'current_status': invoice.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        xml_absolute_path = get_safe_file_path(invoice.xml_file)
        
        if not xml_absolute_path or not os.path.exists(xml_absolute_path):
            logger.error(f"Archivo XML no encontrado: {invoice.xml_file} -> {xml_absolute_path}")
            return Response({
                'status': 'error',
                'message': 'Archivo XML no encontrado en el sistema',
                'suggestion': 'Regenere el XML UBL',
                'invoice_id': invoice_id
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        signer = XMLDigitalSigner()
        signed_xml = signer.sign_xml(xml_content, invoice.full_document_name)
        
        signed_filename = f"{invoice.full_document_name}_signed.xml"
        signed_file_path = os.path.join(settings.MEDIA_ROOT, 'xml_files', signed_filename)
        
        os.makedirs(os.path.dirname(signed_file_path), exist_ok=True)
        
        with open(signed_file_path, 'w', encoding='utf-8') as f:
            f.write(signed_xml)
        
        converter = UBLConverter()
        zip_filename = f"{invoice.full_document_name}.zip"
        zip_file_path = converter.create_zip_file(signed_file_path, zip_filename)
        
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
@permission_classes([IsAuthenticated])
def send_to_sunat(request, invoice_id):
    """Envía documento firmado a SUNAT"""
    try:
        user_invoices = get_user_invoices(request.user)
        invoice = get_object_or_404(user_invoices, id=invoice_id)
        
        if not invoice.zip_file:
            return Response({
                'status': 'error',
                'message': 'Primero debe firmar el XML',
                'suggestion': 'Use el endpoint /sign/ antes de enviar a SUNAT',
                'invoice_id': invoice_id,
                'current_status': invoice.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_signature_info(request):
    """Extrae y devuelve información detallada de la firma digital de un XML"""
    try:
        xml_content = request.data.get('xml_content')
        file_path = request.data.get('file_path')
        
        if xml_content:
            xml_data = xml_content
        elif file_path:
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
        
        signature_info = signer.extract_signature_info(xml_data)
        
        if not signature_info:
            return Response({
                'status': 'error',
                'message': 'No se pudo extraer información de la firma'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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