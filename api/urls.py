# api/urls.py - ARCHIVO COMPLETO CON TODOS LOS ENDPOINTS

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # ================================
    # ENDPOINTS PRINCIPALES DEL CONVERSOR UBL
    # ================================
    
    # Creación de documentos
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
    path('signature-info/', views.get_signature_info, name='get_signature_info'),
    
    # Utilidades
    path('test-sunat-connection/', views.test_sunat_connection, name='test_sunat_connection'),
    
    # ================================
    # NUEVOS ENDPOINTS PARA LOS 5 ESCENARIOS ESPECÍFICOS
    # ================================
    
    # Escenario 1: Boleta con Venta Gravada (IGV 18%)
    path('create-scenario-gravada/', views.create_scenario_gravada, name='create_scenario_gravada'),
    
    # Escenario 2: Boleta con Venta Exonerada (Sin IGV)
    path('create-scenario-exonerada/', views.create_scenario_exonerada, name='create_scenario_exonerada'),
    
    # Escenario 3: Boleta con Percepción (2% sobre servicios)
    path('create-scenario-percepcion/', views.create_scenario_percepcion, name='create_scenario_percepcion'),
    
    # Escenario 4: Boleta con Producto Gratuito
    path('create-scenario-gratuito/', views.create_scenario_gratuito, name='create_scenario_gratuito'),
    
    # Escenario 5: Boleta con Bonificación
    path('create-scenario-bonificacion/', views.create_scenario_bonificacion, name='create_scenario_bonificacion'),
    
    # ================================
    # ENDPOINTS AUXILIARES PARA ESCENARIOS
    # ================================
    
    # Crear todos los escenarios de una vez
    path('create-all-scenarios/', views.create_all_test_scenarios, name='create_all_scenarios'),
    
    # Resetear y limpiar datos de prueba
    path('reset-test-data/', views.reset_test_data, name='reset_test_data'),
    
    # Procesar escenario completo (crear + procesar)
    path('process-scenario/<str:scenario_type>/', views.process_complete_scenario, name='process_complete_scenario'),
    
    # Información detallada de escenarios
    path('scenario-info/<str:scenario_type>/', views.get_scenario_info, name='get_scenario_info'),
]