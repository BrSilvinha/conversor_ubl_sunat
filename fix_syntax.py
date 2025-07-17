#!/usr/bin/env python3
"""
Script de solución rápida para el error de sintaxis en converter.py
Ejecutar desde la raíz del proyecto Django
"""

import os
import sys

def fix_converter_file():
    """Corrige el archivo converter.py eliminando la línea problemática"""
    
    converter_path = os.path.join('ubl_converter', 'converter.py')
    
    if not os.path.exists(converter_path):
        print(f"❌ Error: No se encuentra el archivo {converter_path}")
        print("   Asegúrate de ejecutar este script desde la raíz del proyecto")
        return False
    
    print(f"🔍 Analizando archivo: {converter_path}")
    
    try:
        # Leer el archivo
        with open(converter_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Buscar la línea problemática
        problematic_line = None
        fixed_lines = []
        
        for i, line in enumerate(lines, 1):
            if 'raise - operaciones gravadas' in line:
                problematic_line = i
                print(f"🔧 Encontrada línea problemática en línea {i}: {line.strip()}")
                # Reemplazar con comentario
                fixed_lines.append(f"        # ✅ CORREGIDO: Línea problemática removida (línea {i})\n")
            else:
                fixed_lines.append(line)
        
        if problematic_line:
            # Crear backup
            backup_path = converter_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"💾 Backup creado en: {backup_path}")
            
            # Escribir archivo corregido
            with open(converter_path, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            
            print(f"✅ Archivo corregido exitosamente")
            print(f"   - Línea problemática en línea {problematic_line} removida")
            print(f"   - Backup guardado como {backup_path}")
            return True
        else:
            print("ℹ️  No se encontró la línea problemática específica")
            
            # Buscar otras posibles líneas problemáticas
            syntax_issues = []
            for i, line in enumerate(lines, 1):
                if line.strip().startswith('raise -') and 'operaciones' in line:
                    syntax_issues.append((i, line.strip()))
            
            if syntax_issues:
                print("🔍 Se encontraron posibles problemas de sintaxis:")
                for line_num, line_content in syntax_issues:
                    print(f"   Línea {line_num}: {line_content}")
                return False
            else:
                print("✅ No se encontraron problemas de sintaxis obvios")
                return True
                
    except Exception as e:
        print(f"❌ Error procesando archivo: {e}")
        return False

def test_syntax():
    """Prueba si el archivo tiene sintaxis válida de Python"""
    converter_path = os.path.join('ubl_converter', 'converter.py')
    
    print("\n🧪 Probando sintaxis del archivo...")
    
    try:
        with open(converter_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Intentar compilar el código
        compile(content, converter_path, 'exec')
        print("✅ Sintaxis válida")
        return True
        
    except SyntaxError as e:
        print(f"❌ Error de sintaxis encontrado:")
        print(f"   Línea {e.lineno}: {e.text.strip() if e.text else 'N/A'}")
        print(f"   Error: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Script de Solución Rápida - Error de Sintaxis")
    print("=" * 50)
    
    # Verificar si estamos en el directorio correcto
    if not os.path.exists('manage.py'):
        print("❌ Error: No se encuentra manage.py")
        print("   Ejecuta este script desde la raíz del proyecto Django")
        sys.exit(1)
    
    # Probar sintaxis antes de corregir
    print("📋 Estado inicial:")
    syntax_ok_before = test_syntax()
    
    if syntax_ok_before:
        print("✅ El archivo ya tiene sintaxis válida")
        print("💡 Si sigues teniendo problemas, puede ser otro tipo de error")
    else:
        print("\n🔧 Iniciando corrección...")
        
        # Intentar corregir
        if fix_converter_file():
            print("\n📋 Estado después de la corrección:")
            syntax_ok_after = test_syntax()
            
            if syntax_ok_after:
                print("\n🎉 ¡Corrección exitosa!")
                print("✅ El archivo ahora tiene sintaxis válida")
                print("\n📝 Próximos pasos:")
                print("   1. python manage.py runserver")
                print("   2. Probar la API con: python test_api.py")
            else:
                print("\n⚠️  La corrección no fue suficiente")
                print("   Puede haber otros errores de sintaxis")
        else:
            print("❌ No se pudo corregir automáticamente")
    
    print("\n" + "=" * 50)
    print("📁 Archivos importantes:")
    print(f"   - Archivo principal: ubl_converter/converter.py")
    print(f"   - Backup (si se creó): ubl_converter/converter.py.backup")
    print("   - Logs: logs/django.log")

if __name__ == "__main__":
    main()