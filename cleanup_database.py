# cleanup_database.py - Script para limpiar datos de prueba
# UBICACIÓN: raíz del proyecto (mismo nivel que manage.py)

import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conversor_ubl.settings')
django.setup()

from ubl_converter.models import Invoice, InvoiceLine, InvoicePayment
from core.models import Company, Customer, Product

def cleanup_test_data():
    """Limpia todos los datos de prueba"""
    try:
        print("🧹 Iniciando limpieza de datos de prueba...")
        
        # Eliminar facturas de prueba
        test_invoices = Invoice.objects.filter(
            company__ruc='23022479065'  # RUC de prueba
        )
        
        count_invoices = test_invoices.count()
        test_invoices.delete()
        
        # Eliminar productos de prueba
        test_products = Product.objects.filter(
            company__ruc='23022479065'
        )
        count_products = test_products.count()
        test_products.delete()
        
        # Eliminar clientes de prueba
        test_customers = Customer.objects.filter(
            company__ruc='23022479065'
        )
        count_customers = test_customers.count()
        test_customers.delete()
        
        # Eliminar empresa de prueba (esto eliminará todo en cascada)
        test_company = Company.objects.filter(ruc='23022479065')
        count_companies = test_company.count()
        test_company.delete()
        
        print(f"✅ Limpieza completada:")
        print(f"   - Facturas eliminadas: {count_invoices}")
        print(f"   - Productos eliminados: {count_products}")
        print(f"   - Clientes eliminados: {count_customers}")
        print(f"   - Empresas eliminadas: {count_companies}")
        
    except Exception as e:
        print(f"❌ Error en limpieza: {str(e)}")

def cleanup_all_test_companies():
    """Limpia todas las empresas de prueba con varios RUCs"""
    try:
        print("🧹 Limpiando todas las empresas de prueba...")
        
        # RUCs de prueba comunes
        test_rucs = [
            '23022479065',
            '20000000000',
            '10123456789',
            '12345678901'
        ]
        
        total_deleted = 0
        for ruc in test_rucs:
            test_companies = Company.objects.filter(ruc=ruc)
            count = test_companies.count()
            if count > 0:
                test_companies.delete()
                print(f"   - Empresa con RUC {ruc}: {count} registros eliminados")
                total_deleted += count
        
        print(f"✅ Total empresas de prueba eliminadas: {total_deleted}")
        
    except Exception as e:
        print(f"❌ Error en limpieza completa: {str(e)}")

def reset_sequences():
    """Reinicia las secuencias de la base de datos"""
    try:
        from django.core.management import call_command
        print("🔄 Reiniciando secuencias de la base de datos...")
        call_command('sqlsequencereset', 'core', 'ubl_converter')
        print("✅ Secuencias reiniciadas")
    except Exception as e:
        print(f"⚠️ No se pudieron reiniciar las secuencias: {str(e)}")

if __name__ == "__main__":
    print("🚀 Script de limpieza de datos de prueba")
    print("=" * 50)
    
    # Opción 1: Limpieza específica del RUC principal
    cleanup_test_data()
    
    # Opción 2: Limpieza completa de todos los RUCs de prueba
    cleanup_all_test_companies()
    
    # Opción 3: Reiniciar secuencias
    reset_sequences()
    
    print("=" * 50)
    print("✅ Limpieza completada. Ahora puede crear nuevos escenarios de prueba.")
    print("💡 Ejecute: python manage.py runserver")