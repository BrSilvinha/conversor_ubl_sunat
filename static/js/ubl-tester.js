// static/js/ubl-tester-enhanced.js - SISTEMA COMPLETO UBL 2.1 CON VALIDACIÓN DE FIRMA

// ==================== CONFIGURACIÓN GLOBAL ====================
const API_BASE_URL = '/api';
let currentInvoiceId = null;
let currentFiles = {
    xml: null,
    signed: null,
    zip: null,
    cdr: null
};

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Iniciando Sistema UBL 2.1 Completo');
    
    updateTimestamp();
    setInterval(updateTimestamp, 1000);
    
    // Auto-test de conexión
    setTimeout(() => {
        testConnection();
        viewDocuments(); // Auto-cargar documentos
    }, 1000);
    
    logMessage('✅ Sistema iniciado correctamente', 'success');
    logMessage('⌨️ Atajos: Ctrl+1(Crear) Ctrl+2(Procesar) Ctrl+3(Estado) Ctrl+V(Validar) Ctrl+L(Limpiar)', 'info');
});

function updateTimestamp() {
    const timestampElement = document.getElementById('timestamp');
    if (timestampElement) {
        timestampElement.textContent = new Date().toLocaleString('es-PE', {
            timeZone: 'America/Lima'
        });
    }
}

function updateServerStatus(status) {
    const statusElement = document.getElementById('server-status');
    if (statusElement) {
        if (status === 'connected') {
            statusElement.textContent = 'Conectado';
            statusElement.className = 'badge bg-success text-white';
        } else {
            statusElement.textContent = 'Desconectado';
            statusElement.className = 'badge bg-danger text-white';
        }
    }
}

// ==================== FUNCIONES DE API ====================
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        
        let data;
        try {
            data = await response.json();
        } catch (e) {
            data = { message: 'Error de respuesta del servidor', status: 'error' };
        }
        
        return {
            ok: response.ok,
            status: response.status,
            data: data
        };
    } catch (error) {
        console.error('❌ Error en API:', error);
        return {
            ok: false,
            status: 0,
            error: error.message
        };
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ==================== FUNCIONES DE LOGGING ====================
function logMessage(message, type = 'info', data = null) {
    const container = document.getElementById('logsContainer');
    if (!container) {
        console.log(`${type.toUpperCase()}: ${message}`, data);
        return;
    }

    const timestamp = new Date().toLocaleTimeString('es-PE');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    
    let icon = 'bi-info-circle';
    switch(type) {
        case 'success': icon = 'bi-check-circle'; break;
        case 'error': icon = 'bi-x-circle'; break;
        case 'warning': icon = 'bi-exclamation-triangle'; break;
    }

    let content = `
        <div class="d-flex align-items-center">
            <i class="${icon} me-2"></i>
            <small class="text-muted me-2">${timestamp}</small>
            <span>${message}</span>
        </div>
    `;

    if (data && typeof data === 'object') {
        const dataId = `data-${Date.now()}`;
        content += `
            <div class="mt-1">
                <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${dataId}">
                    <i class="bi bi-code"></i> Ver Datos
                </button>
                <div class="collapse mt-2" id="${dataId}">
                    <pre class="bg-light p-2 rounded small"><code>${JSON.stringify(data, null, 2)}</code></pre>
                </div>
            </div>
        `;
    }

    logEntry.innerHTML = content;
    container.appendChild(logEntry);
    container.scrollTop = container.scrollHeight;
    
    // También log en consola para debugging
    console.log(`${type.toUpperCase()}: ${message}`, data);

    // Mantener solo los últimos 50 logs
    const logs = container.children;
    while (logs.length > 50) {
        container.removeChild(logs[0]);
    }
}

function clearLogs() {
    const container = document.getElementById('logsContainer');
    if (container) {
        container.innerHTML = `
            <div class="text-muted text-center p-3">
                <i class="bi bi-info-circle fs-1"></i>
                <p class="mt-2">Los logs aparecerán aquí</p>
            </div>
        `;
    }
    logMessage('🧹 Logs limpiados', 'info');
}

// ==================== FUNCIONES PRINCIPALES ====================
async function testConnection() {
    logMessage('🔌 Probando conexión con servidor y SUNAT...', 'info');
    
    try {
        const response = await apiCall('/test-sunat-connection/');
        
        if (response.ok) {
            updateServerStatus('connected');
            
            const data = response.data;
            if (data.status === 'warning') {
                logMessage('⚠️ Servidor conectado - Error 401 SUNAT (normal con credenciales de prueba)', 'warning');
                logMessage('💡 El sistema funciona correctamente para generar y firmar XMLs', 'info');
            } else if (data.status === 'success') {
                logMessage('✅ Conexión exitosa con SUNAT', 'success');
                logMessage(`🌐 Ambiente: ${data.environment}`, 'info');
            }
        } else {
            updateServerStatus('disconnected');
            logMessage('⚠️ Problemas de conexión', 'warning', response.data);
        }
    } catch (error) {
        updateServerStatus('disconnected');
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function checkStatus() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    logMessage(`🔍 Consultando estado del documento ${invoiceId}...`, 'info');
    await loadDocumentStatus(invoiceId);
}

// ==================== FUNCIONES DE MANEJO DE ARCHIVOS ====================
async function loadDocumentStatus(invoiceId) {
    try {
        const response = await apiCall(`/invoice/${invoiceId}/status/`);
        
        if (response.ok) {
            const data = response.data;
            updateCurrentStatus(data);
            
            // Actualizar rutas de archivos
            if (data.files) {
                currentFiles.xml = data.files.xml_file;
                currentFiles.signed = data.files.xml_file; // El firmado reemplaza al original
                currentFiles.zip = data.files.zip_file;
                currentFiles.cdr = data.files.cdr_file;
            }
            
            logMessage('✅ Estado consultado exitosamente', 'success');
            
            // Log adicional sobre archivos disponibles
            const filesAvailable = [];
            if (data.files?.xml_file) filesAvailable.push('XML');
            if (data.files?.zip_file) filesAvailable.push('ZIP');
            if (data.files?.cdr_file) filesAvailable.push('CDR');
            
            if (filesAvailable.length > 0) {
                logMessage(`📁 Archivos disponibles: ${filesAvailable.join(', ')}`, 'info');
            }
        } else {
            logMessage('❌ Error consultando estado', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error cargando estado', 'error', { error: error.message });
    }
}

async function loadXMLFile(type) {
    const filePath = type === 'original' ? currentFiles.xml : currentFiles.signed;
    
    if (!filePath) {
        logMessage(`⚠️ No hay archivo ${type} disponible`, 'warning');
        return;
    }

    logMessage(`📄 Cargando archivo XML ${type}...`, 'info');

    try {
        const response = await fetch(`${API_BASE_URL}/file-content/?path=${encodeURIComponent(filePath)}`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.status === 'success') {
                const contentElement = document.getElementById(type === 'original' ? 'xml-content' : 'signed-content');
                if (contentElement) {
                    // Formatear XML con resaltado de sintaxis
                    const formattedXML = formatXML(data.content);
                    contentElement.innerHTML = `<pre><code class="language-xml">${escapeHtml(formattedXML)}</code></pre>`;
                    
                    // Aplicar highlighting si está disponible
                    if (typeof hljs !== 'undefined') {
                        hljs.highlightAll();
                    }
                    
                    // Si es XML firmado, resaltar las firmas
                    if (type === 'signed' && data.is_signed) {
                        highlightSignatureBlocks(contentElement);
                        logMessage('🔒 XML con firma digital detectada', 'success');
                    }
                    
                    // Mostrar estadísticas del archivo
                    const lines = data.content.split('\n').length;
                    const size = data.size || data.content.length;
                    logMessage(`📊 ${type} cargado: ${lines} líneas, ${formatBytes(size)}`, 'info');
                }
                
                logMessage(`✅ Archivo ${type} cargado exitosamente`, 'success');
            } else {
                logMessage(`❌ Error cargando archivo ${type}: ${data.message}`, 'error');
            }
        } else {
            logMessage(`❌ Error HTTP cargando archivo ${type}: ${response.status}`, 'error');
        }
    } catch (error) {
        logMessage(`❌ Error de conexión al cargar archivo ${type}`, 'error', { error: error.message });
    }
}

async function loadZIPFile() {
    if (!currentFiles.zip) {
        logMessage('⚠️ No hay archivo ZIP disponible', 'warning');
        return;
    }

    logMessage('📦 Analizando archivo ZIP...', 'info');

    try {
        const response = await fetch(`${API_BASE_URL}/file-content/?path=${encodeURIComponent(currentFiles.zip)}`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.status === 'success') {
                const container = document.getElementById('zip-content');
                
                let html = '<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>Archivo ZIP listo para envío a SUNAT</div>';
                html += '<h6>Contenido del ZIP:</h6>';
                html += '<ul class="list-group">';
                
                if (data.contents && data.contents.length > 0) {
                    data.contents.forEach(file => {
                        html += `
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <i class="bi bi-file-earmark-code me-2 text-primary"></i>
                                    <strong>${file.filename}</strong>
                                    <br><small class="text-muted">${formatBytes(file.size)} - ${file.date}</small>
                                </div>
                                <span class="badge bg-success">XML Firmado</span>
                            </li>
                        `;
                    });
                } else {
                    html += '<li class="list-group-item text-muted">No se pudo leer el contenido del ZIP</li>';
                }
                
                html += '</ul>';
                
                if (data.xml_content) {
                    html += '<div class="mt-3">';
                    html += '<h6><i class="bi bi-file-code me-2"></i>XML dentro del ZIP:</h6>';
                    html += '<div class="xml-viewer">';
                    html += `<pre><code class="language-xml">${escapeHtml(formatXML(data.xml_content))}</code></pre>`;
                    html += '</div></div>';
                }
                
                container.innerHTML = html;
                
                if (typeof hljs !== 'undefined') {
                    hljs.highlightAll();
                }
                
                logMessage('✅ Archivo ZIP analizado exitosamente', 'success');
                logMessage(`📦 Tamaño total: ${formatBytes(data.size)}`, 'info');
            } else {
                logMessage(`❌ Error analizando ZIP: ${data.message}`, 'error');
            }
        } else {
            logMessage('❌ Error cargando archivo ZIP', 'error');
        }
    } catch (error) {
        logMessage('❌ Error de conexión al cargar ZIP', 'error', { error: error.message });
    }
}

async function loadCDRFile() {
    if (!currentFiles.cdr) {
        logMessage('⚠️ No hay archivo CDR disponible', 'warning');
        logMessage('💡 El CDR se genera después del envío exitoso a SUNAT', 'info');
        return;
    }

    logMessage('📋 Cargando CDR de SUNAT...', 'info');

    try {
        const response = await fetch(`${API_BASE_URL}/file-content/?path=${encodeURIComponent(currentFiles.cdr)}`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.status === 'success') {
                const container = document.getElementById('cdr-content');
                
                let html = '<div class="alert alert-success">';
                html += '<i class="bi bi-check-circle me-2"></i>';
                html += '<strong>CDR (Constancia de Recepción) de SUNAT</strong><br>';
                html += '<small>Este archivo confirma que SUNAT recibió y procesó el documento</small>';
                html += '</div>';
                
                if (data.file_type === 'zip' && data.xml_content) {
                    html += '<h6><i class="bi bi-award me-2"></i>Respuesta de SUNAT:</h6>';
                    html += '<div class="xml-viewer">';
                    html += `<pre><code class="language-xml">${escapeHtml(formatXML(data.xml_content))}</code></pre>`;
                    html += '</div>';
                } else {
                    html += '<h6>Contenido del CDR:</h6>';
                    html += `<pre><code>${escapeHtml(data.content || 'Sin contenido disponible')}</code></pre>`;
                }
                
                container.innerHTML = html;
                
                if (typeof hljs !== 'undefined') {
                    hljs.highlightAll();
                }
                
                logMessage('✅ CDR cargado exitosamente', 'success');
                logMessage('🎉 Documento procesado completamente por SUNAT', 'success');
            } else {
                logMessage(`❌ Error cargando CDR: ${data.message}`, 'error');
            }
        } else {
            logMessage('❌ Error cargando archivo CDR', 'error');
        }
    } catch (error) {
        logMessage('❌ Error de conexión al cargar CDR', 'error', { error: error.message });
    }
}

// ==================== VALIDACIÓN DE FIRMA DIGITAL ====================
async function validateSignature() {
    const signedContent = document.querySelector('#signed-content pre code');
    if (!signedContent || !signedContent.textContent.trim()) {
        logMessage('⚠️ No hay contenido XML firmado para validar', 'warning');
        logMessage('💡 Primero genere y firme un documento', 'info');
        return;
    }

    logMessage('🔍 Validando firma digital XML-DSig...', 'info');

    try {
        const response = await apiCall('/validate-signature/', 'POST', {
            xml_content: signedContent.textContent
        });

        if (response.ok) {
            const data = response.data;
            
            const validationContainer = document.getElementById('signatureValidation');
            const resultsContainer = document.getElementById('signatureResults');
            
            let html = '<div class="row">';
            
            // Estado de la firma
            html += '<div class="col-md-6">';
            html += '<h6><i class="bi bi-shield-check me-2"></i>Estado de la Firma:</h6>';
            if (data.is_valid) {
                html += '<div class="alert alert-success"><i class="bi bi-shield-check me-2"></i><strong>Firma Digital Válida</strong></div>';
                html += '<p class="text-success">✅ La firma cumple con los estándares XML-DSig</p>';
            } else {
                html += '<div class="alert alert-danger"><i class="bi bi-shield-x me-2"></i><strong>Firma Digital Inválida</strong></div>';
            }
            html += `<p><strong>Mensaje:</strong> ${data.message}</p>`;
            html += '</div>';
            
            // Detalles técnicos
            html += '<div class="col-md-6">';
            html += '<h6><i class="bi bi-gear me-2"></i>Detalles Técnicos:</h6>';
            html += '<ul class="list-unstyled">';
            html += `<li><i class="bi bi-${data.validation_details.has_signature ? 'check-circle text-success' : 'x-circle text-danger'} me-2"></i>Contiene Firma: ${data.validation_details.has_signature ? 'Sí' : 'No'}</li>`;
            html += `<li><i class="bi bi-shield me-2"></i>Algoritmo: ${data.validation_details.signature_algorithm}</li>`;
            html += `<li><i class="bi bi-code me-2"></i>Canonicalización: ${data.validation_details.canonicalization}</li>`;
            html += '</ul>';
            html += '</div>';
            
            html += '</div>';
            
            // Información del certificado
            if (data.certificate_info) {
                html += '<div class="certificate-info mt-3">';
                html += '<h6><i class="bi bi-award me-2"></i>Información del Certificado Digital:</h6>';
                html += '<div class="row">';
                html += '<div class="col-md-6">';
                html += `<p><strong>RUC del Emisor:</strong> ${data.certificate_info.ruc || 'N/A'}</p>`;
                html += `<p><strong>Estado:</strong> <span class="badge bg-${data.certificate_info.is_valid ? 'success' : 'danger'}">${data.certificate_info.is_valid ? 'Válido' : 'Expirado'}</span></p>`;
                html += `<p><strong>Número de Serie:</strong> ${data.certificate_info.serial_number || 'N/A'}</p>`;
                html += '</div>';
                html += '<div class="col-md-6">';
                html += `<p><strong>Válido desde:</strong> ${new Date(data.certificate_info.not_valid_before).toLocaleDateString('es-PE')}</p>`;
                html += `<p><strong>Válido hasta:</strong> ${new Date(data.certificate_info.not_valid_after).toLocaleDateString('es-PE')}</p>`;
                html += '</div>';
                html += '</div>';
                html += `<p><strong>Emisor del Certificado:</strong><br><small class="text-muted">${data.certificate_info.issuer}</small></p>`;
                html += '</div>';
            }
            
            resultsContainer.innerHTML = html;
            validationContainer.classList.remove('d-none');
            
            if (data.is_valid) {
                logMessage('✅ Firma digital validada exitosamente', 'success');
                logMessage('🔒 El documento cumple con los estándares de SUNAT', 'success');
            } else {
                logMessage('⚠️ Firma digital inválida o problemática', 'warning');
            }
            
            // Log detalles técnicos
            logMessage('🔧 Validación técnica completada', 'info', data.validation_details);
            
        } else {
            logMessage('❌ Error validando firma', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión al validar firma', 'error', { error: error.message });
    }
}

// ==================== FUNCIONES DE GESTIÓN DE DOCUMENTOS ====================
async function viewDocuments() {
    logMessage('📄 Cargando lista de documentos...', 'info');
    
    try {
        const response = await apiCall('/documents/');
        
        if (response.ok) {
            const documents = response.data.results || response.data;
            
            if (documents.length > 0) {
                logMessage(`✅ ${documents.length} documentos encontrados`, 'success');
                
                // Mostrar los últimos 5 documentos
                documents.slice(0, 5).forEach((doc, index) => {
                    const statusIcon = getStatusIcon(doc.status);
                    logMessage(`${statusIcon} ID:${doc.id} ${doc.document_reference} [${doc.status}] S/${doc.total_amount}`, 'info');
                });
                
                // Auto-seleccionar el último documento si no hay uno seleccionado
                const currentId = document.getElementById('processInvoiceId').value;
                if (!currentId && documents[0]) {
                    document.getElementById('processInvoiceId').value = documents[0].id;
                    currentInvoiceId = documents[0].id;
                    logMessage(`🎯 Documento ${documents[0].id} seleccionado automáticamente`, 'info');
                }
            } else {
                logMessage('📭 No hay documentos creados aún', 'warning');
                logMessage('💡 Use "Crear Documento de Prueba" para comenzar', 'info');
            }
        } else {
            logMessage('❌ Error cargando documentos', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión al cargar documentos', 'error', { error: error.message });
    }
}

// ==================== FUNCIONES AUXILIARES ====================
function getInvoiceId() {
    const invoiceId = document.getElementById('processInvoiceId').value;
    if (!invoiceId) {
        logMessage('⚠️ Ingrese un ID de documento', 'warning');
        logMessage('💡 Use "Crear Documento de Prueba" para generar uno', 'info');
        return null;
    }
    return invoiceId;
}

function updateCurrentStatus(data) {
    const container = document.getElementById('currentStatus');
    if (!container) return;
    
    const statusColors = {
        'PENDING': 'secondary',
        'PROCESSING': 'warning', 
        'SIGNED': 'success',
        'SENT': 'info',
        'ACCEPTED': 'success',
        'REJECTED': 'danger',
        'ERROR': 'danger'
    };
    
    const color = statusColors[data.status] || 'secondary';
    
    container.innerHTML = `
        <h6 class="text-primary">
            <i class="bi bi-file-text me-2"></i>
            Documento ${data.invoice_id || data.invoice_reference || 'N/A'}
        </h6>
        <p class="mb-2">
            <span class="badge bg-${color}">${data.status || data.final_invoice_status}</span>
        </p>
        ${data.totals ? `
            <div class="row text-center">
                <div class="col-6">
                    <small class="text-muted">Total</small><br>
                    <strong>S/ ${parseFloat(data.totals.total_amount || 0).toFixed(2)}</strong>
                </div>
                <div class="col-6">
                    <small class="text-muted">IGV</small><br>
                    <strong>S/ ${parseFloat(data.totals.igv_amount || 0).toFixed(2)}</strong>
                </div>
            </div>
        ` : ''}
        ${data.files ? `
            <div class="mt-2 text-center">
                <small class="text-muted">
                    ${data.files.xml_file ? '<i class="bi bi-file-code text-success"></i>' : '<i class="bi bi-file-code text-muted"></i>'} XML
                    ${data.files.zip_file ? '<i class="bi bi-file-zip text-warning ms-2"></i>' : '<i class="bi bi-file-zip text-muted ms-2"></i>'} ZIP
                    ${data.files.cdr_file ? '<i class="bi bi-file-check text-primary ms-2"></i>' : '<i class="bi bi-file-check text-muted ms-2"></i>'} CDR
                </small>
            </div>
        ` : ''}
    `;
}

function getStatusIcon(status) {
    const icons = {
        'PENDING': '⏳',
        'PROCESSING': '🔄',
        'SIGNED': '✅',
        'SENT': '📤',
        'ACCEPTED': '🎉',
        'REJECTED': '❌',
        'ERROR': '💥'
    };
    return icons[status] || '📄';
}

function formatXML(xml) {
    const PADDING = ' '.repeat(2);
    const reg = /(>)(<)(\/*)/g;
    let formatted = xml.replace(reg, '$1\r\n$2$3');
    
    let pad = 0;
    return formatted.split('\r\n').map(line => {
        let indent = 0;
        if (line.match(/.+<\/\w[^>]*>$/)) {
            indent = 0;
        } else if (line.match(/^<\/\w/) && pad !== 0) {
            pad -= 1;
        } else if (line.match(/^<\w[^>]*[^\/]>.*$/)) {
            indent = 1;
        } else {
            indent = 0;
        }
        
        const padding = PADDING.repeat(pad);
        pad += indent;
        
        return padding + line;
    }).join('\r\n');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function highlightSignatureBlocks(container) {
    const xmlContent = container.innerHTML;
    
    // Resaltar bloques de firma XML-DSig
    const signatureRegex = /(&lt;ds:Signature[^&]*&gt;[\s\S]*?&lt;\/ds:Signature&gt;)/g;
    const highlighted = xmlContent.replace(signatureRegex, '<div class="xml-signature-block">🔒 BLOQUE DE FIRMA DIGITAL: $1</div>');
    
    container.innerHTML = highlighted;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function downloadContent(elementId, filename) {
    const element = document.getElementById(elementId);
    if (!element) {
        logMessage('❌ No hay contenido para descargar', 'error');
        return;
    }
    
    const content = element.textContent || element.innerText;
    if (!content.trim()) {
        logMessage('❌ No hay contenido para descargar', 'error');
        return;
    }
    
    const blob = new Blob([content], { type: 'text/xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    logMessage(`✅ Archivo ${filename} descargado`, 'success');
}

// ==================== ATAJOS DE TECLADO ====================
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey) {
        switch(e.key) {
            case '1':
                e.preventDefault();
                createTestDocument();
                break;
            case '2':
                e.preventDefault();
                if (getInvoiceId()) {
                    processCompleteFlow();
                }
                break;
            case '3':
                e.preventDefault();
                if (getInvoiceId()) {
                    checkStatus();
                }
                break;
            case 'v':
            case 'V':
                e.preventDefault();
                validateSignature();
                break;
            case 'l':
            case 'L':
                e.preventDefault();
                clearLogs();
                break;
            case 't':
            case 'T':
                e.preventDefault();
                testConnection();
                break;
            case 'd':
            case 'D':
                e.preventDefault();
                viewDocuments();
                break;
        }
    }
});

// ==================== FUNCIONES DE DEMOSTRACIÓN ====================
function showSystemCapabilities() {
    logMessage('🎯 Sistema UBL 2.1 - Capacidades:', 'info');
    logMessage('✅ Generación de XML UBL 2.1 estándar', 'success');
    logMessage('✅ Firma digital XML-DSig con certificados X.509', 'success');
    logMessage('✅ Validación de firmas digitales', 'success');
    logMessage('✅ Creación de ZIP para SUNAT', 'success');
    logMessage('✅ Integración con Web Services SUNAT', 'success');
    logMessage('✅ Procesamiento de CDR (Constancia de Recepción)', 'success');
    logMessage('✅ Soporte para múltiples tipos de documentos', 'success');
    logMessage('✅ Interfaz web completa para gestión', 'success');
    logMessage('🚀 Sistema listo para producción con credenciales reales', 'info');
}

// Auto-mostrar capacidades al inicio
setTimeout(() => {
    showSystemCapabilities();
}, 3000); conexión', 'error', { error: error.message });
    }
}

async function createTestDocument() {
    logMessage('🧪 Creando documento de prueba completo...', 'info');
    
    try {
        const response = await apiCall('/create-test-scenarios/', 'POST');
        
        if (response.ok) {
            currentInvoiceId = response.data.invoice_id;
            document.getElementById('processInvoiceId').value = currentInvoiceId;
            
            logMessage('✅ Documento de prueba creado exitosamente', 'success');
            logMessage(`📄 ID: ${currentInvoiceId} - ${response.data.invoice_reference}`, 'info');
            logMessage(`💰 Total: S/ ${response.data.totals.total_amount}`, 'info');
            
            updateCurrentStatus({
                invoice_id: currentInvoiceId,
                status: 'PENDING',
                totals: response.data.totals
            });
        } else {
            logMessage('❌ Error creando documento', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function convertToUBL() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    logMessage(`🔄 Convirtiendo documento ${invoiceId} a XML UBL 2.1...`, 'info');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/convert-ubl/`, 'POST');
        
        if (response.ok) {
            logMessage('✅ XML UBL generado exitosamente', 'success');
            currentFiles.xml = response.data.xml_path;
            
            // Auto-cargar XML en el visor
            loadXMLFile('original');
            
            // Cambiar a la pestaña de XML
            const xmlTab = new bootstrap.Tab(document.getElementById('xml-tab'));
            xmlTab.show();
        } else {
            logMessage('❌ Error en conversión UBL', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function signXML() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    logMessage(`✍️ Firmando digitalmente XML del documento ${invoiceId}...`, 'info');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/sign/`, 'POST');
        
        if (response.ok) {
            logMessage('✅ XML firmado exitosamente con certificado digital', 'success');
            logMessage('🔒 Firma digital aplicada según estándar XML-DSig', 'info');
            
            currentFiles.signed = response.data.signed_xml_path;
            currentFiles.zip = response.data.zip_path;
            
            // Cambiar a la pestaña de XML firmado
            const signedTab = new bootstrap.Tab(document.getElementById('signed-tab'));
            signedTab.show();
            
            // Auto-cargar XML firmado
            loadXMLFile('signed');
            
            // Mostrar información del certificado
            if (response.data.certificate_info) {
                logMessage('📜 Certificado usado en la firma', 'info', response.data.certificate_info);
            }
        } else {
            logMessage('❌ Error en firma digital', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function sendToSUNAT() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    logMessage(`📤 Enviando documento ${invoiceId} a SUNAT...`, 'info');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/send-sunat/`, 'POST');
        
        if (response.ok || (response.data && response.data.status === 'warning')) {
            if (response.data.status === 'warning') {
                logMessage('⚠️ Error de autenticación SUNAT (normal con credenciales de prueba)', 'warning');
                logMessage('✅ Documento XML generado y firmado correctamente', 'success');
                logMessage('💡 Para envío real a SUNAT necesita credenciales válidas de producción', 'info');
                logMessage('🔧 Documento listo para envío con credenciales reales', 'info');
            } else {
                logMessage('✅ Documento enviado a SUNAT exitosamente', 'success');
                if (response.data.sunat_response) {
                    logMessage('📨 Respuesta de SUNAT recibida', 'info', response.data.sunat_response);
                }
            }
            
            // Actualizar estado
            loadDocumentStatus(invoiceId);
        } else {
            logMessage('❌ Error enviando a SUNAT', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function processCompleteFlow() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    logMessage(`🚀 Iniciando flujo completo: UBL → Firma → SUNAT para documento ${invoiceId}...`, 'info');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/process-complete/`, 'POST');
        
        if (response.ok) {
            const data = response.data;
            
            // Mostrar resumen de pasos
            if (data.steps && data.steps.length > 0) {
                logMessage('📋 Resumen del proceso:', 'info');
                data.steps.forEach((step, index) => {
                    const stepIcon = step.status === 'success' ? '✅' : 
                                   step.status === 'warning' ? '⚠️' : '❌';
                    const stepType = step.status === 'warning' ? 'warning' : step.status;
                    logMessage(`${stepIcon} Paso ${index + 1}: ${step.message}`, stepType);
                });
            }
            
            if (data.overall_status === 'success' || data.overall_status === 'success_with_warnings') {
                logMessage('🎉 Flujo completo procesado exitosamente', 'success');
                
                if (data.overall_status === 'success_with_warnings') {
                    logMessage('💡 Nota: Errores de SUNAT son normales con credenciales de prueba', 'info');
                    logMessage('🎯 El sistema está funcionando correctamente', 'success');
                }
            } else {
                logMessage('⚠️ Flujo completado con errores', 'warning', data);
            }
            
            // Cargar archivos generados
            await loadDocumentStatus(invoiceId);
            
            // Mostrar XML firmado automáticamente
            const signedTab = new bootstrap.Tab(document.getElementById('signed-tab'));
            signedTab.show();
            setTimeout(() => loadXMLFile('signed'), 500);
            
        } else {
            logMessage('❌ Error en flujo completo', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de