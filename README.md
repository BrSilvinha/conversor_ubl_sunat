# 🧾 Conversor UBL 2.1 - Facturación Electrónica SUNAT

Un sistema completo para la generación, firma digital y envío de comprobantes electrónicos según los estándares UBL 2.1 de SUNAT (Perú).

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![SUNAT](https://img.shields.io/badge/SUNAT-Compatible-red.svg)](https://sunat.gob.pe)

## 📋 Tabla de Contenidos

- [🌟 Características](#-características)
- [🏗️ Arquitectura](#️-arquitectura)
- [📦 Instalación](#-instalación)
- [⚙️ Configuración](#️-configuración)
- [🚀 Uso](#-uso)
- [📚 API Reference](#-api-reference)
- [🔧 Desarrollo](#-desarrollo)
- [📸 Screenshots](#-screenshots)
- [🤝 Contribución](#-contribución)
- [📄 Licencia](#-licencia)

## 🌟 Características

### ✅ Funcionalidades Principales

- **📄 Generación UBL 2.1**: Conversión completa de datos de negocio a XML UBL 2.1
- **🔐 Firma Digital**: Firma XML-DSig con certificados X.509 según estándares SUNAT
- **📤 Integración SUNAT**: Envío automático a Web Services de SUNAT
- **📥 Procesamiento CDR**: Recepción y validación de Constancias de Recepción
- **🌐 API REST**: API completa para integración con sistemas externos
- **💻 Interfaz Web**: Panel de administración y testing integrado
- **📊 Dashboard**: Seguimiento completo del estado de documentos

### 🎯 Tipos de Documentos Soportados

- ✅ **Facturas Electrónicas** (01)
- ✅ **Boletas de Venta Electrónicas** (03)
- 🔄 **Notas de Crédito** (07) - _En desarrollo_
- 🔄 **Notas de Débito** (08) - _En desarrollo_

### 💰 Tipos de Operaciones

- **Gravadas** - Con IGV (18%)
- **Exoneradas** - Sin IGV por exoneración
- **Inafectas** - Sin IGV por inafectación
- **Gratuitas** - Sin costo (promociones, muestras)
- **Con Percepción** - Régimen de percepciones

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   External      │
│   (HTML/JS)     │────│   (Django)      │────│   (SUNAT)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼───┐ ┌───▼───┐ ┌───▼────┐
            │    UBL    │ │ Firma │ │ SUNAT  │
            │ Converter │ │Digital│ │Client  │
            └───────────┘ └───────┘ └────────┘
```

### 🧩 Componentes

1. **🏢 Core**: Modelos base (Company, Customer, Product)
2. **📄 UBL Converter**: Generación de XML UBL 2.1
3. **🔐 Digital Signature**: Firma XML-DSig con certificados
4. **📡 SUNAT Integration**: Cliente Web Services SUNAT
5. **🌐 API**: Endpoints REST para operaciones
6. **💻 Frontend**: Interfaz web para testing y administración

## 📦 Instalación

### 📋 Requisitos

- **Python** 3.9+
- **PostgreSQL** 12+
- **Certificado Digital** (formato .pfx)
- **Windows/Linux/macOS**

### 🔧 Instalación Paso a Paso

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/conversor-ubl-sunat.git
cd conversor-ubl-sunat
```

2. **Crear entorno virtual**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar base de datos PostgreSQL**
```sql
CREATE DATABASE conversor_ubl_db;
CREATE USER postgres WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE conversor_ubl_db TO postgres;
```

5. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

6. **Ejecutar migraciones**
```bash
python manage.py migrate
```

7. **Crear superusuario**
```bash
python manage.py createsuperuser
```

8. **Ejecutar servidor**
```bash
python manage.py runserver
```

## ⚙️ Configuración

### 📄 Archivo .env

```env
# Django Settings
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=conversor_ubl_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

# SUNAT Configuration
SUNAT_USE_BETA=True
SUNAT_RUC=20000000001
SUNAT_USERNAME=MODDATOS
SUNAT_PASSWORD=MODDATOS

# Certificado Digital
SUNAT_CERTIFICATE_PATH=media/certificates/certificado.pfx
SUNAT_CERTIFICATE_PASSWORD=tu_password_certificado

# Configuraciones Opcionales
ENABLE_STRICT_VALIDATION=False
VALIDATE_RUC_CHECKSUM=False
SUNAT_REQUEST_TIMEOUT=30
```

### 🔑 Certificado Digital

1. **Obtener certificado** de un PSC autorizado por SUNAT
2. **Colocar archivo .pfx** en `media/certificates/`
3. **Configurar ruta y contraseña** en `.env`

### 🏢 Configuración Inicial

1. **Acceder al admin**: `http://localhost:8000/admin/`
2. **Crear empresa**: Datos del emisor
3. **Configurar series**: Numeración de documentos
4. **Agregar productos**: Catálogo de productos/servicios

## 🚀 Uso

### 💻 Interfaz Web

Accede a `http://localhost:8000/` para usar la interfaz web:

1. **📝 Crear Documento**: Formulario para crear facturas/boletas
2. **📄 Mis Documentos**: Lista de documentos creados
3. **⚙️ Procesar**: Conversión UBL → Firma → SUNAT
4. **📊 Logs**: Seguimiento de operaciones

### 🔄 Flujo Completo

```mermaid
graph LR
    A[Crear Documento] --> B[Generar UBL XML]
    B --> C[Firmar Digitalmente]
    C --> D[Enviar a SUNAT]
    D --> E[Recibir CDR]
    E --> F[Documento Aceptado]
```

### 🎯 Ejemplos de Uso

#### 📝 Crear Documento de Prueba

```bash
# Usar la interfaz web o API
POST /api/create-test-scenarios/
```

#### ⚙️ Procesar Documento

```bash
# Flujo completo automático
POST /api/invoice/{id}/process-complete/

# O paso a paso:
POST /api/invoice/{id}/convert-ubl/    # 1. Generar UBL
POST /api/invoice/{id}/sign/           # 2. Firmar
POST /api/invoice/{id}/send-sunat/     # 3. Enviar
```

## 📚 API Reference

### 🔗 Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/create-test-scenarios/` | Crear documento de prueba |
| `POST` | `/api/create-invoice-manual/` | Crear documento manual |
| `GET` | `/api/documents/` | Listar documentos |
| `GET` | `/api/invoice/{id}/status/` | Estado del documento |
| `POST` | `/api/invoice/{id}/convert-ubl/` | Generar XML UBL |
| `POST` | `/api/invoice/{id}/sign/` | Firmar digitalmente |
| `POST` | `/api/invoice/{id}/send-sunat/` | Enviar a SUNAT |
| `POST` | `/api/invoice/{id}/process-complete/` | Flujo completo |
| `GET` | `/api/file-content/?path={path}` | Ver contenido de archivo |
| `GET` | `/api/test-sunat-connection/` | Probar conexión SUNAT |

### 📊 Respuestas de API

#### ✅ Respuesta Exitosa
```json
{
  "status": "success",
  "message": "Documento procesado exitosamente",
  "invoice_id": 123,
  "document_reference": "B001-00000001",
  "files": {
    "xml_file": "xml_files/documento.xml",
    "zip_file": "zip_files/documento.zip",
    "cdr_file": "cdr_files/R-documento.zip"
  }
}
```

#### ❌ Respuesta de Error
```json
{
  "status": "error",
  "message": "Descripción del error",
  "error_code": "ERR001",
  "suggestion": "Verificar configuración"
}
```

## 🔧 Desarrollo

### 🛠️ Setup de Desarrollo

1. **Instalar dependencias de desarrollo**
```bash
pip install -r requirements-dev.txt
```

2. **Configurar pre-commit hooks**
```bash
pre-commit install
```

3. **Ejecutar tests**
```bash
python manage.py test
```

### 📁 Estructura del Proyecto

```
conversor_ubl_sunat/
├── 📁 api/                     # API REST endpoints
├── 📁 core/                    # Modelos base
├── 📁 digital_signature/       # Firma digital XML-DSig
├── 📁 logs/                    # Archivos de log
├── 📁 media/                   # Archivos generados
│   ├── 📁 certificates/        # Certificados digitales
│   ├── 📁 xml_files/          # XMLs UBL generados
│   ├── 📁 zip_files/          # ZIPs firmados
│   └── 📁 cdr_files/          # CDRs de SUNAT
├── 📁 static/                  # Archivos estáticos
├── 📁 sunat_integration/       # Cliente SUNAT
├── 📁 templates/              # Templates HTML
├── 📁 ubl_converter/          # Generador UBL 2.1
├── 📄 .env                    # Variables de entorno
├── 📄 manage.py              # Script de Django
└── 📄 requirements.txt       # Dependencias Python
```

### 🔍 Debugging

#### 📊 Logs del Sistema

```bash
# Ver logs en tiempo real
tail -f logs/django.log
tail -f logs/ubl_converter.log
tail -f logs/sunat_integration.log
```

#### 🛠️ Django Debug Toolbar

Para desarrollo, activar Django Debug Toolbar en `settings.py`:

```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### 🧪 Testing

#### 🎯 Tests Unitarios

```bash
# Ejecutar todos los tests
python manage.py test

# Tests específicos
python manage.py test ubl_converter.tests
python manage.py test digital_signature.tests
```

#### 🔄 Tests de Integración

```bash
# Test completo del flujo
python manage.py test api.tests.test_complete_flow
```

## 📸 Screenshots

### 🏠 Dashboard Principal
![Dashboard](docs/images/dashboard.png)

### 📝 Crear Documento
![Crear Documento](docs/images/create-document.png)

### ⚙️ Procesar Documento
![Procesar](docs/images/process-document.png)

### 📊 Estado de Documentos
![Estado](docs/images/document-status.png)

## 🚨 Troubleshooting

### ❓ Problemas Comunes

#### 🔐 Error de Certificado
```
Error: No se pudo cargar el certificado
Solución: Verificar ruta y contraseña del certificado en .env
```

#### 📡 Error de Conexión SUNAT
```
Error: 401 Unauthorized
Solución: Verificar credenciales SUNAT (normal en ambiente BETA)
```

#### 📄 Error en Rutas de Archivos
```
Error: Archivo no encontrado
Solución: Verificar permisos de escritura en directorio media/
```

### 🔧 Comandos Útiles

```bash
# Limpiar archivos generados
find media/ -name "*.xml" -delete
find media/ -name "*.zip" -delete

# Resetear base de datos
python manage.py flush
python manage.py migrate

# Recolectar archivos estáticos
python manage.py collectstatic
```

## 📈 Roadmap

### 🎯 Próximas Versiones

- [ ] **v2.0**: Notas de Crédito y Débito
- [ ] **v2.1**: Guías de Remisión
- [ ] **v2.2**: Retenciones y Percepciones
- [ ] **v2.3**: Facturación masiva
- [ ] **v3.0**: Microservicios y escalabilidad

### 🚀 Mejoras Planeadas

- **📱 App Móvil**: React Native
- **☁️ Cloud Deploy**: Docker + Kubernetes
- **📊 Analytics**: Dashboard avanzado
- **🔄 Webhooks**: Notificaciones automáticas
- **🌍 Multi-país**: Soporte para otros países

## 🤝 Contribución

### 💡 Cómo Contribuir

1. **Fork** el proyecto
2. **Crear rama** para feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** cambios (`git commit -m 'Add some AmazingFeature'`)
4. **Push** a la rama (`git push origin feature/AmazingFeature`)
5. **Abrir Pull Request**

### 📝 Guías de Contribución

- **🧹 Código limpio**: Seguir PEP 8
- **📝 Documentación**: Comentar código complejo
- **🧪 Tests**: Agregar tests para nuevas funcionalidades
- **📊 Logs**: Usar logging apropiado

### 🐛 Reportar Bugs

- **📋 Descripción** detallada del problema
- **🔄 Pasos** para reproducir
- **💻 Entorno** (OS, Python version, etc.)
- **📊 Logs** relevantes

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

```
MIT License

Copyright (c) 2024 Tu Nombre

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🙏 Agradecimientos

- **🏛️ SUNAT** - Por la documentación técnica
- **🌐 UBL TC** - Por los estándares UBL
- **🐍 Django Community** - Por el framework
- **👥 Contribuidores** - Por hacer posible este proyecto

---

<div align="center">

**⭐ Si este proyecto te ha sido útil, por favor considera darle una estrella en GitHub ⭐**

[🏠 Inicio](#-conversor-ubl-21---facturación-electrónica-sunat) • [📋 Características](#-características) • [📦 Instalación](#-instalación) • [📚 API](#-api-reference) • [🤝 Contribuir](#-contribución)

</div>