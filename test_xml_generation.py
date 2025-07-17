# test_xml_generation.py - Script para probar generación XML
# UBICACIÓN: raíz del proyecto (mismo nivel que manage.py)

import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conversor_ubl.settings')
django.setup()

from ubl_converter.models import Invoice
from ubl_converter.converter import UBLConverter
import xml.etree.ElementTree as ET

def test_xml_generation():
    """Prueba la generación de XML para detectar errores de atributos duplicados"""
    try:
        print("🧪 Iniciando prueba de generación XML...")
        
        # Buscar la última factura creada
        invoice = Invoice.objects.order_by('-id').first()
        
        if not invoice:
            print("❌ No se encontraron facturas en la base de datos")
            print("💡 Ejecute primero: python manage.py shell")
            print("   Luego cree una factura usando el API")
            return
        
        print(f"📄 Probando factura: {invoice.full_document_name}")
        print(f"   - Tipo: {invoice.get_document_type_display()}")
        print(f"   - Serie: {invoice.series}")
        print(f"   - Número: {invoice.number}")
        print(f"   - Total: {invoice.total_amount}")
        
        # Crear convertidor
        converter = UBLConverter()
        
        # Intentar generar XML
        print("\n🔄 Generando XML UBL...")
        xml_content = converter.convert_invoice_to_xml(invoice)
        
        # Validar que el XML sea válido
        print("✅ XML generado exitosamente")
        
        # Intentar parsear el XML para verificar validez
        try:
            root = ET.fromstring(xml_content)
            print("✅ XML es válido y parseable")
            
            # Mostrar información básica del XML
            print(f"\n📋 Información del XML:")
            print(f"   - Elemento raíz: {root.tag}")
            print(f"   - Namespaces: {len(root.attrib)} atributos")
            
            # Contar elementos
            all_elements = root.findall('.//*')
            print(f"   - Total elementos: {len(all_elements)}")
            
            # Verificar elementos importantes
            ubl_version = root.find('.//{*}UBLVersionID')
            if ubl_version is not None:
                print(f"   - Versión UBL: {ubl_version.text}")
            
            doc_id = root.find('.//{*}ID')
            if doc_id is not None:
                print(f"   - ID Documento: {doc_id.text}")
            
            # Verificar líneas de detalle
            lines = root.findall('.//{*}InvoiceLine')
            print(f"   - Líneas de detalle: {len(lines)}")
            
        except ET.ParseError as e:
            print(f"❌ Error parseando XML: {e}")
            return False
        
        # Guardar XML de prueba
        test_filename = f"TEST_{invoice.full_document_name}.xml"
        xml_path = converter.save_xml_to_file(xml_content, test_filename)
        print(f"\n💾 XML guardado en: {xml_path}")
        
        # Mostrar preview del XML
        print(f"\n📜 Preview del XML (primeros 500 caracteres):")
        print("-" * 60)
        print(xml_content[:500] + "..." if len(xml_content) > 500 else xml_content)
        print("-" * 60)
        
        print("\n✅ Prueba de generación XML completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de XML: {str(e)}")
        print(f"   Tipo de error: {type(e).__name__}")
        
        # Información adicional para debugging
        if "duplicate attribute" in str(e):
            print("\n🔍 Error de atributo duplicado detectado:")
            print("   Esto indica que hay atributos XML repetidos")
            print("   Verifique el código del convertidor UBL")
        
        return False

def test_all_invoices():
    """Prueba la generación XML para todas las facturas"""
    try:
        print("🧪 Probando generación XML para todas las facturas...")
        
        invoices = Invoice.objects.all()
        if not invoices:
            print("❌ No hay facturas para probar")
            return
        
        print(f"📊 Encontradas {invoices.count()} facturas")
        
        converter = UBLConverter()
        success_count = 0
        error_count = 0
        
        for invoice in invoices:
            try:
                print(f"\n🔄 Probando: {invoice.full_document_name}")
                xml_content = converter.convert_invoice_to_xml(invoice)
                
                # Verificar que el XML sea parseable
                ET.fromstring(xml_content)
                print(f"   ✅ OK")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                error_count += 1
        
        print(f"\n📊 Resultados:")
        print(f"   ✅ Exitosas: {success_count}")
        print(f"   ❌ Con errores: {error_count}")
        print(f"   📈 Tasa de éxito: {(success_count/(success_count+error_count)*100):.1f}%")
        
    except Exception as e:
        print(f"❌ Error en prueba masiva: {str(e)}")

if __name__ == "__main__":
    print("🚀 Script de Prueba de Generación XML")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        test_all_invoices()
    else:
        test_xml_generation()
    
    print("=" * 50)
    print("✅ Prueba completada")
    print("\n💡 Uso:")
    print("   python test_xml_generation.py        # Probar última factura")
    print("   python test_xml_generation.py --all  # Probar todas las facturas")