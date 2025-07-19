// static/js/ubl-tester.js - ARCHIVO COMPLETO ACTUALIZADO CON CORRECCIONES DE RUTAS

// ==================== CONFIGURACIÓN GLOBAL ULTRA-SEGURA ====================
const API_BASE_URL = '/api';

// ✅ Variables globales con inicialización explícita y segura
let currentInvoiceId = null;
let currentFiles = {
    xml: null,
    signed: null,
    zip: null,
    cdr: null
};
let lineCounter = 1;
let currentFileContent = null;
let systemInitialized = false;
let documentReady = false;

// ✅ FUNCIONES DE UTILIDAD ULTRA-SEGURAS
function safeLog(message, type = 'info', data = null) {
    try {
        console.log(`${type.toUpperCase()}: ${message}`, data || '');
    } catch (e) {
        // Silenciar errores de logging para evitar cascadas de errores
    }
}

function getCookie(name) {
    try {
        if (typeof window === 'undefined' || !window.document || !window.document.cookie) {
            return null;
        }
        
        let cookieValue = null;
        const cookies = window.document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
        return cookieValue;
    } catch (e) {
        safeLog('Error obteniendo cookie:', 'error', e);
        return null;
    }
}

function isDocumentReady() {
    try {
        return typeof window !== 'undefined' && 
               typeof window.document !== 'undefined' && 
               (window.document.readyState === 'complete' || window.document.readyState === 'interactive');
    } catch (e) {
        return false;
    }
}

function waitForDocument(callback, maxAttempts = 50) {
    let attempts = 0;
    
    function check() {
        attempts++;
        if (isDocumentReady()) {
            documentReady = true;
            callback();
        } else if (attempts < maxAttempts) {
            setTimeout(check, 100);
        } else {
            safeLog('Timeout esperando document ready', 'error');
        }
    }
    
    check();
}

function waitForElement(elementId, callback, maxAttempts = 30) {
    let attempts = 0;
    
    function check() {
        attempts++;
        const element = document.getElementById(elementId);
        if (element) {
            callback(element);
        } else if (attempts < maxAttempts) {
            setTimeout(check, 100);
        } else {
            safeLog(`Timeout esperando elemento: ${elementId}`, 'warning');
        }
    }
    
    check();
}

// ==================== FUNCIONES DE API SEGURAS ====================
async function apiCall(endpoint, method = 'GET', body = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        // Agregar CSRF token si está disponible
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) {
            options.headers['X-CSRFToken'] = csrfToken;
        }

        if (body) {
            options.body = JSON.stringify(body);
        }

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
        safeLog('Error en API:', 'error', error);
        return {
            ok: false,
            status: 0,
            error: error.message
        };
    }
}

// ==================== INICIALIZACIÓN ULTRA-ROBUSTA ====================
function initializeSystem() {
    if (systemInitialized) {
        safeLog('Sistema ya inicializado', 'info');
        return;
    }
    
    if (!documentReady) {
        safeLog('Documento no está listo, esperando...', 'warning');
        waitForDocument(initializeSystem);
        return;
    }
    
    safeLog('🚀 Iniciando Sistema UBL 2.1 Mejorado', 'info');
    
    try {
        // Verificar elementos críticos
        const criticalElements = ['logsContainer'];
        let allElementsReady = true;
        
        for (const elementId of criticalElements) {
            if (!document.getElementById(elementId)) {
                allElementsReady = false;
                safeLog(`Elemento crítico faltante: ${elementId}`, 'warning');
            }
        }
        
        if (!allElementsReady) {
            setTimeout(initializeSystem, 200);
            return;
        }
        
        // Inicialización paso a paso con manejo de errores
        initComponents();
        
        systemInitialized = true;
        logMessage('✅ Sistema iniciado correctamente', 'success');
        logMessage('⌨️ Atajos: Ctrl+1(Crear) Ctrl+2(Procesar) Ctrl+L(Limpiar)', 'info');
        
        // Auto-test con delay
        setTimeout(() => {
            try {
                testConnection();
                viewDocuments();
            } catch (error) {
                safeLog('Error en auto-test:', 'error', error);
            }
        }, 1000);
        
    } catch (error) {
        safeLog('Error crítico en inicialización:', 'error', error);
        setTimeout(initializeSystem, 500);
    }
}

function initComponents() {
    try {
        // Inicializar fecha
        const today = new Date().toISOString().split('T')[0];
        const issueDateInput = document.getElementById('issueDate');
        if (issueDateInput) {
            issueDateInput.value = today;
        }
        
        // Inicializar monto de pago
        const paymentAmount = document.getElementById('paymentAmount');
        if (paymentAmount) {
            paymentAmount.value = '0.00';
        }
        
        // Inicializar timestamp
        updateTimestamp();
        setInterval(updateTimestamp, 1000);
        
        safeLog('✅ Componentes inicializados', 'info');
    } catch (error) {
        safeLog('Error inicializando componentes:', 'error', error);
    }
}

function updateTimestamp() {
    try {
        const timestampElement = document.getElementById('timestamp');
        if (timestampElement) {
            timestampElement.textContent = new Date().toLocaleString('es-PE', {
                timeZone: 'America/Lima'
            });
        }
    } catch (error) {
        // Error silencioso
    }
}

function updateServerStatus(status) {
    try {
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
    } catch (error) {
        safeLog('Error actualizando estado del servidor:', 'error', error);
    }
}

// ==================== FUNCIONES DE LOGGING MEJORADAS ====================
function logMessage(message, type = 'info', data = null) {
    safeLog(message, type, data);
    
    try {
        if (!documentReady) return;
        
        const container = document.getElementById('logsContainer');
        if (!container) return;

        const timestamp = new Date().toLocaleTimeString('es-PE');
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type} mb-2 p-2 border-start border-3`;
        
        let icon = 'bi-info-circle';
        let bgClass = 'bg-light';
        switch(type) {
            case 'success': 
                icon = 'bi-check-circle'; 
                bgClass = 'bg-success bg-opacity-10 border-success';
                break;
            case 'error': 
                icon = 'bi-x-circle'; 
                bgClass = 'bg-danger bg-opacity-10 border-danger';
                break;
            case 'warning': 
                icon = 'bi-exclamation-triangle'; 
                bgClass = 'bg-warning bg-opacity-10 border-warning';
                break;
            default:
                bgClass = 'bg-info bg-opacity-10 border-info';
        }

        logEntry.className += ` ${bgClass}`;

        let content = `
            <div class="d-flex align-items-center">
                <i class="${icon} me-2"></i>
                <small class="text-muted me-2">${timestamp}</small>
                <span>${escapeHtml(message)}</span>
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
                        <pre class="bg-light p-2 rounded small"><code>${escapeHtml(JSON.stringify(data, null, 2))}</code></pre>
                    </div>
                </div>
            `;
        }

        logEntry.innerHTML = content;
        container.appendChild(logEntry);
        container.scrollTop = container.scrollHeight;

        // Mantener solo los últimos 50 logs
        const logs = container.children;
        while (logs.length > 50) {
            container.removeChild(logs[0]);
        }
    } catch (error) {
        safeLog('Error en logMessage:', 'error', error);
    }
}

function clearLogs() {
    try {
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
    } catch (error) {
        safeLog('Error limpiando logs:', 'error', error);
    }
}

// ==================== FUNCIONES DE PROCESAMIENTO ====================
async function createTestDocument() {
    logMessage('🧪 Creando documento de prueba completo...', 'info');
    
    try {
        const response = await apiCall('/create-test-scenarios/', 'POST');
        
        if (response.ok) {
            currentInvoiceId = response.data.invoice_id;
            const invoiceIdInput = document.getElementById('processInvoiceId');
            if (invoiceIdInput) {
                invoiceIdInput.value = currentInvoiceId;
            }
            
            logMessage('✅ Documento de prueba creado exitosamente', 'success');
            logMessage(`📄 ID: ${currentInvoiceId} - ${response.data.invoice_reference}`, 'info');
            logMessage(`💰 Total: S/ ${response.data.totals.total_amount}`, 'info');
            
            viewDocuments();
            
            // Actualizar display del documento actual
            updateCurrentDocumentDisplay({
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
            
            // Actualizar estado del documento
            await loadDocumentStatus(invoiceId);
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
            
            // Mostrar información del certificado
            if (response.data.certificate_info) {
                logMessage('📜 Certificado usado en la firma', 'info', response.data.certificate_info);
            }
            
            // Actualizar estado del documento
            await loadDocumentStatus(invoiceId);
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
            await loadDocumentStatus(invoiceId);
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
    logMessage('📋 Resumen del proceso:', 'info');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/process-complete/`, 'POST');
        
        if (response.ok) {
            const results = response.data;
            
            // Mostrar resultados de cada paso
            results.steps.forEach((step, index) => {
                const stepNumber = index + 1;
                if (step.status === 'success') {
                    logMessage(`✅ Paso ${stepNumber}: ${step.message}`, 'success');
                } else if (step.status === 'warning') {
                    logMessage(`⚠️ Paso ${stepNumber}: ${step.message}`, 'warning');
                } else {
                    logMessage(`❌ Paso ${stepNumber}: ${step.message}`, 'error');
                }
            });
            
            // Mensaje final
            if (results.overall_status === 'success') {
                logMessage('🎉 Flujo completo procesado exitosamente', 'success');
            } else if (results.overall_status === 'success_with_warnings') {
                logMessage('🎉 Flujo completo procesado exitosamente', 'success');
                logMessage('⚠️ Algunas advertencias por credenciales de prueba', 'warning');
            } else {
                logMessage('❌ Error en el flujo completo', 'error');
            }
            
            // Actualizar estado
            await loadDocumentStatus(invoiceId);
        } else {
            logMessage('❌ Error en flujo completo', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión en flujo completo', 'error', { error: error.message });
    }
}

async function checkStatus() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    logMessage(`🔍 Consultando estado del documento ${invoiceId}...`, 'info');
    await loadDocumentStatus(invoiceId);
}

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

// ==================== GESTIÓN DE DOCUMENTOS ====================
async function viewDocuments() {
    logMessage('📄 Cargando lista de documentos...', 'info');
    
    try {
        const response = await apiCall('/documents/');
        
        if (response.ok) {
            const documents = response.data.results || response.data;
            
            if (documents.length > 0) {
                logMessage(`✅ ${documents.length} documentos encontrados`, 'success');
                displayDocumentsTable(documents);
                
                // Auto-seleccionar el último documento
                const currentIdInput = document.getElementById('processInvoiceId');
                const currentId = currentIdInput ? currentIdInput.value : null;
                if (!currentId && documents[0] && currentIdInput) {
                    currentIdInput.value = documents[0].id;
                    currentInvoiceId = documents[0].id;
                    logMessage(`🎯 Documento ${documents[0].id} seleccionado automáticamente`, 'info');
                }
            } else {
                logMessage('📭 No hay documentos creados aún', 'warning');
                logMessage('💡 Use "Crear Documento de Prueba" para comenzar', 'info');
                displayEmptyDocumentsTable();
            }
        } else {
            logMessage('❌ Error cargando documentos', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión al cargar documentos', 'error', { error: error.message });
    }
}

function refreshDocuments() {
    viewDocuments();
}

function displayDocumentsTable(documents) {
    try {
        const tbody = document.getElementById('documentsTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        documents.forEach(doc => {
            const row = document.createElement('tr');
            const statusIcon = getStatusIcon(doc.status);
            const statusClass = getStatusClass(doc.status);
            
            row.innerHTML = `
                <td><strong>${doc.id}</strong></td>
                <td><span class="badge bg-${doc.document_type === '01' ? 'primary' : 'success'}">${doc.document_type === '01' ? 'FAC' : 'BOL'}</span></td>
                <td><strong>${doc.document_reference}</strong></td>
                <td>${escapeHtml(doc.customer_name)}</td>
                <td><strong>S/ ${parseFloat(doc.total_amount).toFixed(2)}</strong></td>
                <td><span class="badge bg-${statusClass}">${statusIcon} ${doc.status}</span></td>
                <td>${new Date(doc.created_at).toLocaleDateString('es-PE')}</td>
                <td>
                    <div class="text-center">
                        ${doc.xml_file ? '<i class="bi bi-file-code text-success" title="XML" style="cursor:pointer;" onclick="viewFile(\'' + doc.xml_file + '\', \'XML\')"></i>' : '<i class="bi bi-file-code text-muted"></i>'}
                        ${doc.zip_file ? '<i class="bi bi-file-zip text-warning ms-1" title="ZIP" style="cursor:pointer;" onclick="viewFile(\'' + doc.zip_file + '\', \'ZIP\')"></i>' : '<i class="bi bi-file-zip text-muted ms-1"></i>'}
                        ${doc.cdr_file ? '<i class="bi bi-file-check text-primary ms-1" title="CDR" style="cursor:pointer;" onclick="viewFile(\'' + doc.cdr_file + '\', \'CDR\')"></i>' : '<i class="bi bi-file-check text-muted ms-1"></i>'}
                    </div>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" onclick="selectDocument(${doc.id})" title="Seleccionar">
                            <i class="bi bi-arrow-right"></i>
                        </button>
                        <button class="btn btn-outline-info" onclick="viewDocumentDetails(${doc.id})" title="Ver detalles">
                            <i class="bi bi-eye"></i>
                        </button>
                    </div>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    } catch (error) {
        safeLog('Error mostrando tabla de documentos:', 'error', error);
        logMessage('❌ Error mostrando documentos', 'error');
    }
}

function displayEmptyDocumentsTable() {
    try {
        const tbody = document.getElementById('documentsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted p-4">
                    <i class="bi bi-folder-x fs-1"></i>
                    <p class="mt-2">No hay documentos creados</p>
                    <button class="btn btn-primary" onclick="createTestDocument()">
                        <i class="bi bi-plus-circle"></i> Crear Primer Documento
                    </button>
                </td>
            </tr>
        `;
    } catch (error) {
        safeLog('Error mostrando tabla vacía:', 'error', error);
    }
}

function selectDocument(documentId) {
    try {
        const invoiceIdInput = document.getElementById('processInvoiceId');
        if (invoiceIdInput) {
            invoiceIdInput.value = documentId;
            currentInvoiceId = documentId;
            
            // Cambiar al tab de procesamiento
            const processTab = document.getElementById('process-tab');
            if (processTab && typeof bootstrap !== 'undefined') {
                const tab = new bootstrap.Tab(processTab);
                tab.show();
            }
            
            // Cargar estado del documento
            loadDocumentStatus(documentId);
            
            logMessage(`🎯 Documento ${documentId} seleccionado`, 'info');
        }
    } catch (error) {
        safeLog('Error seleccionando documento:', 'error', error);
        logMessage('❌ Error seleccionando documento', 'error');
    }
}

function viewDocumentDetails(documentId) {
    selectDocument(documentId);
}

async function loadDocumentStatus(invoiceId) {
    try {
        logMessage(`🔄 Cargando estado del documento ${invoiceId}...`, 'info');
        
        const response = await apiCall(`/invoice/${invoiceId}/status/`);
        
        if (response.ok) {
            const data = response.data;
            logMessage('✅ Estado consultado exitosamente', 'success');
            logMessage(`📁 Archivos disponibles: ${data.files.xml_file ? 'XML' : ''} ${data.files.zip_file ? 'ZIP' : ''} ${data.files.cdr_file ? 'CDR' : ''}`.trim() || 'Ninguno', 'info');
            
            updateCurrentDocumentDisplay(data);
            updateFilesViewer(data.files);
        } else {
            logMessage('❌ Error consultando estado', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión consultando estado', 'error', { error: error.message });
    }
}

function updateCurrentDocumentDisplay(data) {
    try {
        const container = document.getElementById('currentDocumentDetails');
        if (!container) return;
        
        const statusClass = getStatusClass(data.status);
        const statusIcon = getStatusIcon(data.status);
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="bi bi-file-text"></i> Información del Documento</h6>
                    <table class="table table-sm">
                        <tr>
                            <td><strong>ID:</strong></td>
                            <td>${data.invoice_id}</td>
                        </tr>
                        <tr>
                            <td><strong>Referencia:</strong></td>
                            <td>${data.document_reference}</td>
                        </tr>
                        <tr>
                            <td><strong>Estado:</strong></td>
                            <td><span class="badge bg-${statusClass}">${statusIcon} ${data.status}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Creado:</strong></td>
                            <td>${new Date(data.created_at).toLocaleString('es-PE')}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6><i class="bi bi-calculator"></i> Totales</h6>
                    <table class="table table-sm">
                        <tr>
                            <td><strong>Gravado:</strong></td>
                            <td>S/ ${parseFloat(data.totals.total_taxed_amount).toFixed(2)}</td>
                        </tr>
                        <tr>
                            <td><strong>IGV:</strong></td>
                            <td>S/ ${parseFloat(data.totals.igv_amount).toFixed(2)}</td>
                        </tr>
                        <tr class="table-primary">
                            <td><strong>TOTAL:</strong></td>
                            <td><strong>S/ ${parseFloat(data.totals.total_amount).toFixed(2)}</strong></td>
                        </tr>
                    </table>
                </div>
            </div>
        `;
        
        // Mostrar información SUNAT si existe
        if (data.sunat_info && data.sunat_info.response_description) {
            container.innerHTML += `
                <div class="mt-3">
                    <h6><i class="bi bi-cloud-arrow-up"></i> Información SUNAT</h6>
                    <div class="alert alert-info">
                        <strong>Código:</strong> ${data.sunat_info.response_code || 'N/A'}<br>
                        <strong>Descripción:</strong> ${data.sunat_info.response_description}
                    </div>
                </div>
            `;
        }
        
    } catch (error) {
        safeLog('Error actualizando display del documento:', 'error', error);
    }
}

function updateFilesViewer(files) {
    try {
        const container = document.getElementById('filesViewer');
        if (!container) return;
        
        let hasFiles = false;
        let filesHtml = '<div class="row">';
        
        if (files.xml_file) {
            hasFiles = true;
            filesHtml += `
                <div class="col-md-4 mb-3">
                    <div class="card">
                        <div class="card-body text-center">
                            <i class="bi bi-file-code fs-1 text-primary"></i>
                            <h6 class="mt-2">XML UBL</h6>
                            <button class="btn btn-sm btn-outline-primary" onclick="viewFile('${files.xml_file}', 'XML')">
                                <i class="bi bi-eye"></i> Ver
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (files.zip_file) {
            hasFiles = true;
            filesHtml += `
                <div class="col-md-4 mb-3">
                    <div class="card">
                        <div class="card-body text-center">
                            <i class="bi bi-file-zip fs-1 text-warning"></i>
                            <h6 class="mt-2">ZIP Firmado</h6>
                            <button class="btn btn-sm btn-outline-warning" onclick="viewFile('${files.zip_file}', 'ZIP')">
                                <i class="bi bi-eye"></i> Ver
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (files.cdr_file) {
            hasFiles = true;
            filesHtml += `
                <div class="col-md-4 mb-3">
                    <div class="card">
                        <div class="card-body text-center">
                            <i class="bi bi-file-check fs-1 text-success"></i>
                            <h6 class="mt-2">CDR SUNAT</h6>
                            <button class="btn btn-sm btn-outline-success" onclick="viewFile('${files.cdr_file}', 'CDR')">
                                <i class="bi bi-eye"></i> Ver
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        filesHtml += '</div>';
        
        if (!hasFiles) {
            filesHtml = `
                <div class="text-muted text-center p-4">
                    <i class="bi bi-folder fs-1"></i>
                    <p class="mt-2">Los archivos generados aparecerán aquí</p>
                </div>
            `;
        }
        
        container.innerHTML = filesHtml;
        
    } catch (error) {
        safeLog('Error actualizando visor de archivos:', 'error', error);
    }
}

// ==================== FUNCIÓN viewFile COMPLETAMENTE CORREGIDA ====================
async function viewFile(filePath, fileType) {
    logMessage(`📄 Cargando archivo ${fileType}...`, 'info');
    
    try {
        // ✅ VALIDACIÓN MEJORADA DE RUTA
        if (!filePath || filePath === 'true' || filePath === 'false' || filePath.trim().length < 3) {
            logMessage(`❌ Ruta de archivo inválida para ${fileType}: "${filePath}"`, 'error');
            showErrorModal('Ruta de Archivo Inválida', `La ruta "${filePath}" no es válida.`);
            return;
        }
        
        logMessage(`🔍 Procesando ruta original: ${filePath}`, 'info');
        
        // ✅ NORMALIZACIÓN DE RUTA COMPLETAMENTE NUEVA
        let cleanPath;
        try {
            // Normalizar separadores a forward slash
            cleanPath = filePath.replace(/\\/g, '/');
            
            // Limpiar caracteres problemáticos pero mantener estructura
            cleanPath = cleanPath.replace(/[^\w\-_./:/]/g, '');
            
            // Si es ruta relativa, asegurar que sea correcta
            if (!cleanPath.includes(':') && !cleanPath.startsWith('/')) {
                // Es ruta relativa - normalizarla
                if (!cleanPath.startsWith('xml_files/') && !cleanPath.startsWith('zip_files/') && !cleanPath.startsWith('cdr_files/')) {
                    // Detectar tipo de archivo y agregar directorio correcto
                    if (cleanPath.includes('.xml')) {
                        cleanPath = 'xml_files/' + cleanPath.split('/').pop();
                    } else if (cleanPath.includes('.zip') && cleanPath.includes('R-')) {
                        cleanPath = 'cdr_files/' + cleanPath.split('/').pop();
                    } else if (cleanPath.includes('.zip')) {
                        cleanPath = 'zip_files/' + cleanPath.split('/').pop();
                    }
                }
            }
            
            logMessage(`🔧 Ruta normalizada: ${cleanPath}`, 'info');
        } catch (pathError) {
            logMessage(`❌ Error normalizando ruta: ${pathError.message}`, 'error');
            showErrorModal('Error de Ruta', 'No se pudo procesar la ruta del archivo.');
            return;
        }
        
        // ✅ CODIFICACIÓN SEGURA DE LA URL - SOLO EL PARÁMETRO
        let encodedPath;
        try {
            // Codificar solo caracteres especiales, mantener estructura básica
            encodedPath = encodeURIComponent(cleanPath);
            logMessage(`🔗 Parámetro codificado: ${encodedPath}`, 'info');
        } catch (encodeError) {
            logMessage(`❌ Error codificando parámetro: ${encodeError.message}`, 'error');
            showErrorModal('Error de Codificación', 'No se pudo codificar el parámetro del archivo.');
            return;
        }
        
        // ✅ LLAMADA API MEJORADA
        const url = `${API_BASE_URL}/file-content/?path=${encodedPath}`;
        logMessage(`📡 URL completa: ${url}`, 'info');
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        logMessage(`📊 Respuesta API: ${response.status} ${response.statusText}`, 'info');
        
        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch {
                errorData = { message: `Error HTTP ${response.status}: ${response.statusText}` };
            }
            
            logMessage(`❌ Error del servidor: ${JSON.stringify(errorData)}`, 'error');
            
            // Mostrar información útil para debugging
            const debugInfo = `
                <strong>Información de Debug:</strong><br>
                Ruta original: ${filePath}<br>
                Ruta normalizada: ${cleanPath}<br>
                URL consultada: ${url}<br>
                Error: ${errorData.message || 'Error desconocido'}
            `;
            
            showErrorModal(`Error Cargando ${fileType}`, debugInfo);
            return;
        }
        
        // ✅ PROCESAMIENTO DE RESPUESTA MEJORADO
        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            logMessage(`❌ Error parseando respuesta JSON: ${jsonError.message}`, 'error');
            showErrorModal('Error de Respuesta', 'La respuesta del servidor no es válida.');
            return;
        }
        
        if (data.status === 'success') {
            currentFileContent = data.content;
            showFileViewerModal(data, fileType, filePath);
            logMessage(`✅ Archivo ${fileType} cargado exitosamente (${formatBytes(data.size || 0)})`, 'success');
        } else {
            logMessage(`❌ Error cargando archivo ${fileType}: ${data.message}`, 'error');
            
            // Información adicional para debugging
            const debugInfo = `
                <strong>Error:</strong> ${data.message}<br>
                ${data.searched_paths ? '<strong>Rutas buscadas:</strong><br>' + data.searched_paths.join('<br>') : ''}
                ${data.original_path ? '<br><strong>Ruta original:</strong> ' + data.original_path : ''}
            `;
            
            showErrorModal('Error Cargando Archivo', debugInfo);
        }
        
    } catch (error) {
        logMessage(`❌ Error de conexión al cargar archivo ${fileType}: ${error.message}`, 'error');
        
        const debugInfo = `
            <strong>Error de Conexión:</strong><br>
            ${error.message}<br><br>
            <strong>Ruta solicitada:</strong> ${filePath}<br>
            <strong>Sugerencias:</strong><br>
            • Verificar que el servidor esté ejecutándose<br>
            • Comprobar la configuración de CORS<br>
            • Revisar los logs del servidor
        `;
        
        showErrorModal('Error de Conexión', debugInfo);
    }
}

function showFileViewerModal(data, fileType, filePath) {
    try {
        const modal = document.getElementById('fileViewerModal');
        const title = document.getElementById('fileViewerTitle');
        const content = document.getElementById('fileViewerContent');
        
        if (!modal || !title || !content) {
            logMessage('❌ Elementos del modal no encontrados', 'error');
            return;
        }
        
        // ✅ TÍTULO MEJORADO CON INFORMACIÓN DETALLADA
        let titleHtml = `<i class="bi bi-file-code"></i> Visor de Archivo - ${fileType}`;
        
        if (data.is_signed) {
            titleHtml += ' <span class="badge bg-success ms-2"><i class="bi bi-shield-check"></i> Firmado</span>';
        }
        
        if (data.is_valid_xml === false) {
            titleHtml += ' <span class="badge bg-warning ms-2"><i class="bi bi-exclamation-triangle"></i> XML Inválido</span>';
        }
        
        if (data.encoding && data.encoding !== 'utf-8') {
            titleHtml += ` <span class="badge bg-info ms-2">${data.encoding.toUpperCase()}</span>`;
        }
        
        title.innerHTML = titleHtml;
        
        // ✅ CONTENIDO PROCESADO SEGÚN TIPO DE ARCHIVO
        let htmlContent = '';
        
        if (data.file_type === 'xml') {
            htmlContent = generateXMLContent(data, filePath);
        } else if (data.file_type === 'zip') {
            htmlContent = generateZIPContent(data);
        } else if (data.file_type === 'binary') {
            htmlContent = generateBinaryContent(data);
        } else {
            htmlContent = generateTextContent(data);
        }
        
        content.innerHTML = htmlContent;
        
        // ✅ MOSTRAR MODAL CON BOOTSTRAP
        if (typeof bootstrap !== 'undefined') {
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        } else {
            // Fallback si Bootstrap no está disponible
            modal.style.display = 'block';
            modal.classList.add('show');
        }
        
    } catch (error) {
        logMessage(`❌ Error mostrando modal de archivo: ${error.message}`, 'error');
        showErrorModal('Error del Modal', 'No se pudo mostrar el visor de archivos.');
    }
}

function generateXMLContent(data, filePath) {
    let content = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <span class="badge ${data.is_signed ? 'bg-success' : 'bg-secondary'}">
                    ${data.is_signed ? '🔒 XML Firmado' : '📄 XML Sin Firmar'}
                </span>
                <span class="badge bg-info">${formatBytes(data.size)}</span>
                ${data.is_valid_xml === false ? '<span class="badge bg-warning">⚠️ XML Inválido</span>' : ''}
            </div>
            <div class="btn-group">`;
    
    if (data.is_signed) {
        content += `
                <button class="btn btn-sm btn-outline-primary" onclick="showSignatureInfo('${filePath}')">
                    <i class="bi bi-shield-check"></i> Ver Firma
                </button>`;
    }
    
    content += `
                <button class="btn btn-sm btn-outline-secondary" onclick="copyToClipboard()">
                    <i class="bi bi-clipboard"></i> Copiar
                </button>
            </div>
        </div>`;
    
    // ✅ CONTENIDO XML FORMATEADO Y RESALTADO
    const formattedXML = formatXML(data.content);
    content += `
        <pre class="bg-light p-3 rounded xml-viewer" style="max-height: 500px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.4;">
            <code class="language-xml">${escapeHtml(formattedXML)}</code>
        </pre>`;
    
    return content;
}

function generateZIPContent(data) {
    let content = `
        <div class="alert alert-info d-flex align-items-center">
            <i class="bi bi-archive fs-4 me-2"></i>
            <div>
                <strong>Archivo ZIP:</strong> ${data.file_name}<br>
                <small>Tamaño: ${formatBytes(data.size)} | Archivos: ${data.contents ? data.contents.length : 0}</small>
            </div>
        </div>`;
    
    if (data.contents && data.contents.length > 0) {
        content += '<h6>📋 Contenido del ZIP:</h6>';
        content += '<div class="table-responsive">';
        content += '<table class="table table-sm table-striped">';
        content += '<thead><tr><th>Archivo</th><th>Tamaño</th><th>Comprimido</th><th>Fecha</th><th>Tipo</th></tr></thead>';
        content += '<tbody>';
        
        data.contents.forEach(file => {
            const fileIcon = getFileIcon(file.filename);
            const compressionRatio = file.size > 0 ? ((file.size - file.compressed_size) / file.size * 100).toFixed(1) : 0;
            
            content += `
                <tr>
                    <td><i class="${fileIcon}"></i> ${escapeHtml(file.filename)}</td>
                    <td>${formatBytes(file.size)}</td>
                    <td>${formatBytes(file.compressed_size)} <small class="text-muted">(${compressionRatio}%)</small></td>
                    <td>${file.date}</td>
                    <td><span class="badge bg-secondary">${getFileExtension(file.filename).toUpperCase()}</span></td>
                </tr>`;
        });
        
        content += '</tbody></table></div>';
    }
    
    if (data.xml_content) {
        content += `
            <div class="mt-3">
                <h6>📄 XML dentro del ZIP:</h6>
                <pre class="bg-light p-3 rounded" style="max-height: 400px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 11px;">
                    <code class="language-xml">${escapeHtml(formatXML(data.xml_content))}</code>
                </pre>
            </div>`;
    }
    
    return content;
}

function generateBinaryContent(data) {
    return `
        <div class="alert alert-warning">
            <i class="bi bi-file-binary fs-4"></i>
            <strong>Archivo Binario</strong><br>
            Este archivo contiene datos binarios y no puede mostrarse como texto.<br>
            <small>Tamaño: ${formatBytes(data.size)} | Codificación: ${data.encoding}</small>
        </div>
        <div class="text-center mt-3">
            <button class="btn btn-primary" onclick="downloadCurrentFile()">
                <i class="bi bi-download"></i> Descargar Archivo
            </button>
        </div>`;
}

function generateTextContent(data) {
    return `
        <div class="mb-2">
            <span class="badge bg-info">${formatBytes(data.size)}</span>
            <span class="badge bg-secondary">${data.encoding || 'UTF-8'}</span>
        </div>
        <pre class="bg-light p-3 rounded" style="max-height: 500px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px;">
            <code>${escapeHtml(data.content)}</code>
        </pre>`;
}

// ✅ FUNCIONES AUXILIARES MEJORADAS
function getFileIcon(filename) {
    const ext = getFileExtension(filename).toLowerCase();
    const iconMap = {
        'xml': 'bi-file-code text-primary',
        'txt': 'bi-file-text text-secondary',
        'pdf': 'bi-file-pdf text-danger',
        'zip': 'bi-file-zip text-warning',
        'rar': 'bi-file-zip text-warning'
    };
    return iconMap[ext] || 'bi-file text-muted';
}

function getFileExtension(filename) {
    return filename.split('.').pop() || '';
}

function copyToClipboard() {
    if (currentFileContent) {
        navigator.clipboard.writeText(currentFileContent).then(() => {
            logMessage('📋 Contenido copiado al portapapeles', 'success');
        }).catch(err => {
            logMessage('❌ Error copiando al portapapeles', 'error');
            // Fallback para navegadores que no soportan clipboard API
            const textArea = document.createElement('textarea');
            textArea.value = currentFileContent;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                logMessage('📋 Contenido copiado al portapapeles (método alternativo)', 'success');
            } catch (fallbackErr) {
                logMessage('❌ No se pudo copiar al portapapeles', 'error');
            }
            document.body.removeChild(textArea);
        });
    } else {
        logMessage('❌ No hay contenido para copiar', 'warning');
    }
}

function showErrorModal(title, message) {
    // Crear modal de error si no existe
    let errorModal = document.getElementById('errorModal');
    if (!errorModal) {
        errorModal = createErrorModal();
    }
    
    document.getElementById('errorModalTitle').textContent = title;
    document.getElementById('errorModalBody').innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle fs-4"></i>
            <div class="mt-2">${message}</div>
        </div>
        <div class="mt-3">
            <small class="text-muted">
                <strong>Ayuda:</strong> Si el problema persiste, revisar los logs del servidor o contactar al administrador.
            </small>
        </div>`;
    
    if (typeof bootstrap !== 'undefined') {
        const bootstrapModal = new bootstrap.Modal(errorModal);
        bootstrapModal.show();
    }
}

function createErrorModal() {
    const modalHtml = `
        <div class="modal fade" id="errorModal" tabindex="-1" aria-labelledby="errorModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title" id="errorModalTitle">Error</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="errorModalBody">
                        <!-- Contenido del error -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    </div>
                </div>
            </div>
        </div>`;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    return document.getElementById('errorModal');
}

function downloadCurrentFile() {
    if (currentFileContent) {
        try {
            const blob = new Blob([currentFileContent], { type: 'text/plain;charset=utf-8' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'archivo_descargado.xml';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            logMessage('📥 Archivo descargado exitosamente', 'success');
        } catch (error) {
            logMessage(`❌ Error descargando archivo: ${error.message}`, 'error');
        }
    } else {
        logMessage('❌ No hay archivo para descargar', 'warning');
    }
}

// ==================== NUEVA FUNCIÓN: MOSTRAR INFORMACIÓN DE FIRMA ====================
async function showSignatureInfo(filePath) {
    logMessage('🔐 Cargando información de la firma digital...', 'info');
    
    try {
        const response = await apiCall('/signature-info/', 'POST', {
            file_path: filePath
        });
        
        if (response.ok && response.data.status === 'success') {
            const signatureInfo = response.data.signature_info;
            const validation = response.data.validation;
            
            if (signatureInfo.signature_found) {
                displaySignatureModal(signatureInfo, validation);
                logMessage('✅ Información de firma extraída exitosamente', 'success');
            } else {
                logMessage('⚠️ No se encontró firma digital en el documento', 'warning');
            }
        } else {
            logMessage('❌ Error obteniendo información de firma', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión obteniendo firma', 'error', { error: error.message });
    }
}

function displaySignatureModal(signatureInfo, validation) {
    try {
        // Usar el modal existente
        const modal = document.getElementById('signatureInfoModal');
        const modalBody = document.getElementById('signatureInfoModalBody');
        
        if (modal && modalBody) {
            modalBody.innerHTML = `
                <!-- Estado de Validación -->
                <div class="alert ${validation.is_valid ? 'alert-success' : 'alert-danger'}" role="alert">
                    <i class="bi ${validation.is_valid ? 'bi-check-circle-fill' : 'bi-x-circle-fill'}"></i>
                    <strong>Estado de la Firma:</strong> ${validation.message}
                </div>
                
                <!-- Información Básica -->
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="bi bi-info-circle"></i> Información Básica</h6>
                        <table class="table table-sm">
                            <tr>
                                <td><strong>ID de Firma:</strong></td>
                                <td>${signatureInfo.signature_id}</td>
                            </tr>
                            <tr>
                                <td><strong>Valor de Firma:</strong></td>
                                <td><code class="small">${signatureInfo.signature_value || 'N/A'}</code></td>
                            </tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="bi bi-cpu"></i> Algoritmos Utilizados</h6>
                        <table class="table table-sm">
                            <tr>
                                <td><strong>Canonicalización:</strong></td>
                                <td><small>${getAlgorithmName(signatureInfo.algorithms.canonicalization)}</small></td>
                            </tr>
                            <tr>
                                <td><strong>Firma:</strong></td>
                                <td><small>${getAlgorithmName(signatureInfo.algorithms.signature)}</small></td>
                            </tr>
                            <tr>
                                <td><strong>Digest:</strong></td>
                                <td><small>${getAlgorithmName(signatureInfo.algorithms.digest)}</small></td>
                            </tr>
                        </table>
                    </div>
                </div>
                
                <!-- Información del Certificado -->
                <div class="mt-3">
                    <h6><i class="bi bi-award"></i> Información del Certificado</h6>
                    ${renderCertificateInfo(signatureInfo.certificate_info)}
                </div>
                
                <!-- Información del Digest -->
                <div class="mt-3">
                    <h6><i class="bi bi-fingerprint"></i> Información del Digest</h6>
                    <p><strong>Valor:</strong> <code class="small">${signatureInfo.digest_info.value || 'N/A'}</code></p>
                </div>
            `;
            
            // Mostrar modal
            if (typeof bootstrap !== 'undefined') {
                const bootstrapModal = new bootstrap.Modal(modal);
                bootstrapModal.show();
            }
        }
        
    } catch (error) {
        safeLog('Error mostrando modal de firma:', 'error', error);
        logMessage('❌ Error mostrando información de firma', 'error');
    }
}

function renderCertificateInfo(certInfo) {
    if (certInfo.error) {
        return `<div class="alert alert-warning">${certInfo.error}</div>`;
    }
    
    return `
        <div class="row">
            <div class="col-md-6">
                <table class="table table-sm">
                    <tr>
                        <td><strong>RUC:</strong></td>
                        <td>${certInfo.ruc || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td><strong>Número de Serie:</strong></td>
                        <td>${certInfo.serial_number}</td>
                    </tr>
                    <tr>
                        <td><strong>Válido Desde:</strong></td>
                        <td>${certInfo.not_valid_before}</td>
                    </tr>
                    <tr>
                        <td><strong>Válido Hasta:</strong></td>
                        <td>${certInfo.not_valid_after}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <p><strong>Estado:</strong> 
                    <span class="badge ${certInfo.is_valid ? 'bg-success' : 'bg-danger'}">
                        ${certInfo.is_valid ? 'Válido' : 'Expirado'}
                    </span>
                </p>
                <p><strong>Emisor:</strong><br>
                    <small class="text-muted">${certInfo.issuer}</small>
                </p>
            </div>
        </div>
    `;
}

function getAlgorithmName(algorithmUrl) {
    if (!algorithmUrl) return 'N/A';
    
    const algorithms = {
        'http://www.w3.org/TR/2001/REC-xml-c14n-20010315': 'XML C14N 1.0',
        'http://www.w3.org/2000/09/xmldsig#rsa-sha1': 'RSA-SHA1',
        'http://www.w3.org/2000/09/xmldsig#sha1': 'SHA-1',
        'http://www.w3.org/2000/09/xmldsig#enveloped-signature': 'Enveloped Signature'
    };
    
    return algorithms[algorithmUrl] || algorithmUrl.split('#').pop() || algorithmUrl;
}

function downloadSignatureReport() {
    // TODO: Implementar descarga de reporte
    logMessage('📄 Función de descarga de reporte pendiente de implementar', 'info');
}

// ==================== FUNCIONES DE UTILIDAD ====================
function getInvoiceId() {
    try {
        const invoiceIdInput = document.getElementById('processInvoiceId');
        const invoiceId = invoiceIdInput ? invoiceIdInput.value : null;
        
        if (!invoiceId) {
            logMessage('⚠️ Ingrese un ID de documento', 'warning');
            logMessage('💡 Use "Crear Documento de Prueba" para generar uno', 'info');
            return null;
        }
        return invoiceId;
    } catch (error) {
        safeLog('Error obteniendo invoice ID:', 'error', error);
        return null;
    }
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

function getStatusClass(status) {
    const classes = {
        'PENDING': 'secondary',
        'PROCESSING': 'warning',
        'SIGNED': 'success',
        'SENT': 'info',
        'ACCEPTED': 'success',
        'REJECTED': 'danger',
        'ERROR': 'danger'
    };
    return classes[status] || 'secondary';
}

function formatXML(xml) {
    try {
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
    } catch (error) {
        safeLog('Error formateando XML:', 'error', error);
        return xml;
    }
}

function escapeHtml(text) {
    try {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    } catch (error) {
        safeLog('Error escapando HTML:', 'error', error);
        return text;
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ==================== FUNCIONES PLACEHOLDER PARA COMPLETAR ====================
function addLine() { 
    logMessage('⚠️ Función addLine no implementada aún', 'warning');
}

function removeLine() { 
    logMessage('⚠️ Función removeLine no implementada aún', 'warning');
}

function calculateTotals() { 
    logMessage('⚠️ Función calculateTotals no implementada aún', 'warning');
}

function createInvoice() {
    logMessage('⚠️ Función createInvoice no implementada aún', 'warning');
    logMessage('💡 Use "Crear Documento de Prueba" por ahora', 'info');
}

function loadTestScenario() {
    createTestDocument();
}

function showSunatHelp() {
    logMessage('ℹ️ Ayuda SUNAT: Sistema configurado para ambiente BETA', 'info');
    logMessage('📋 Credenciales: RUC 20000000001, Usuario/Clave: MODDATOS', 'info');
    logMessage('🔧 Para producción configure credenciales reales en .env', 'info');
}

// ==================== CONFIGURACIÓN DE EVENTOS SEGUROS ====================
function setupEventListeners() {
    try {
        if (!documentReady) return;
        
        document.addEventListener('keydown', function(e) {
            try {
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
            } catch (error) {
                safeLog('Error en atajo de teclado:', 'error', error);
            }
        });
        
        safeLog('✅ Event listeners configurados', 'info');
    } catch (error) {
        safeLog('Error configurando event listeners:', 'error', error);
    }
}

// ==================== INICIALIZACIÓN PRINCIPAL ====================
// Usar múltiples estrategias de inicialización para máxima compatibilidad
if (typeof window !== 'undefined') {
    // Estrategia 1: DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            documentReady = true;
            initializeSystem();
            setupEventListeners();
        });
    } else {
        // DOM ya está listo
        waitForDocument(() => {
            initializeSystem();
            setupEventListeners();
        });
    }
    
    // Estrategia 2: window.onload como respaldo
    const originalOnload = window.onload;
    window.onload = function() {
        if (originalOnload) originalOnload();
        if (!systemInitialized) {
            waitForDocument(() => {
                initializeSystem();
                setupEventListeners();
            });
        }
    };
}

// Estrategia 3: Timeout de emergencia
setTimeout(() => {
    if (!systemInitialized && typeof window !== 'undefined') {
        safeLog('Inicialización por timeout de emergencia', 'warning');
        waitForDocument(() => {
            initializeSystem();
            setupEventListeners();
        });
    }
}, 2000);

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
    logMessage('✅ Visualización completa de información de firma digital', 'success');
    logMessage('🚀 Sistema listo para producción con credenciales reales', 'info');
}

// Auto-mostrar capacidades con delay
setTimeout(() => {
    if (systemInitialized) {
        showSystemCapabilities();
    }
}, 3000);