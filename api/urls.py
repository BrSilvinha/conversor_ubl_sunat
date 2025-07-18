# api/urls.py - AGREGAR ESTA LÍNEA A LAS URLs EXISTENTES

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Endpoints principales del conversor UBL
    path('create-test-scenarios/', views.create_invoice_test_scenarios, name='create_test_scenarios'),
    path('create-invoice-manual/', views.create_invoice_manual, name='create_invoice_manual'),
    
    # Gestión de documentos
    path('documents/', views.list_documents, name='list_documents'),
    path('file-content/', views.get_file_content, name='get_file_content'),
    
    # Procesamiento de documentos
    path('invoice/<int:invoice_id>/convert-ubl/', views.convert_to_ubl, name='convert_to_ubl'),
    path('invoice/<int:invoice_id>/sign/', views.sign_xml, name='sign_xml'),
    path('invoice/<int:invoice_id>/send-sunat/', views.send_to_sunat, name='send_to_sunat'),
    path('invoice/<int:invoice_id>/check-status/', views.check_sunat_status, name='check_sunat_status'),
    path('invoice/<int:invoice_id>/process-complete/', views.process_complete_flow, name='process_complete_flow'),
    path('invoice/<int:invoice_id>/status/', views.get_invoice_status, name='get_invoice_status'),
    
    # Validación de firma digital
    path('validate-signature/', views.validate_xml_signature, name='validate_signature'),
    
    # ✅ NUEVO: Información detallada de la firma
    path('signature-info/', views.get_signature_info, name='get_signature_info'),
    
    # Utilidades
    path('test-sunat-connection/', views.test_sunat_connection, name='test_sunat_connection'),
]