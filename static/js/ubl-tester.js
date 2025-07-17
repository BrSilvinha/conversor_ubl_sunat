// static/js/ubl-tester.js - JAVASCRIPT COMPLETO PARA EL CONVERSOR UBL 2.1

// ==================== CONFIGURACIÓN GLOBAL ====================
const API_BASE_URL = '/api';  // ✅ CORREGIDO: Sin puerto específico
let currentInvoiceId = null;
let currentDocuments = [];
let lineCounter = 0;

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Iniciando Conversor UBL 2.1');
    
    updateTimestamp();
    setInterval(updateTimestamp, 1000);
    
    // Establecer fecha actual
    const dateInput = document.getElementById('issueDate');
    if (dateInput) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
    
    // Agregar línea inicial
    addLine();
    
    // Evento para cargar documentos
    const documentsTab = document.getElementById('documents-tab');
    if (documentsTab) {
        documentsTab.addEventListener('shown.bs.tab', function() {
            refreshDocuments();
        });
    }
    
    logMessage('✅ Sistema iniciado correctamente', 'success');
});

function updateTimestamp() {
    const timestampElement = document.getElementById('timestamp');
    if (timestampElement) {
        timestampElement.textContent = new Date().toLocaleString();
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

// ==================== GESTIÓN DE LÍNEAS DE DETALLE ====================
function addLine() {
    lineCounter++;
    const tbody = document.getElementById('linesTableBody');
    
    if (!tbody) {
        console.error('❌ No se encontró tabla de líneas');
        return;
    }
    
    const row = document.createElement('tr');
    row.id = `line-${lineCounter}`;
    
    row.innerHTML = `
        <td>${lineCounter}</td>
        <td><input type="text" class="form-control form-control-sm" id="code-${lineCounter}" value="PROD${lineCounter.toString().padStart(3, '0')}" onchange="calculateLine(${lineCounter})"></td>
        <td><input type="text" class="form-control form-control-sm" id="desc-${lineCounter}" value="Producto ${lineCounter}" onchange="calculateLine(${lineCounter})"></td>
        <td><input type="number" class="form-control form-control-sm" id="qty-${lineCounter}" value="1" step="0.01" onchange="calculateLine(${lineCounter})"></td>
        <td><input type="number" class="form-control form-control-sm" id="price-${lineCounter}" value="100.00" step="0.01" onchange="calculateLine(${lineCounter})"></td>
        <td>
            <select class="form-select form-select-sm" id="taxType-${lineCounter}" onchange="calculateLine(${lineCounter})">
                <option value="S">Gravado (IGV)</option>
                <option value="E">Exonerado</option>
                <option value="O">Inafecto</option>
                <option value="Z">Gratuito</option>
            </select>
        </td>
        <td><span id="value-${lineCounter}">100.00</span></td>
        <td><span id="igv-${lineCounter}">18.00</span></td>
        <td><span id="total-${lineCounter}">118.00</span></td>
        <td>
            <button class="btn btn-danger btn-sm" onclick="removeLine(${lineCounter})">
                <i class="bi bi-trash"></i>
            </button>
        </td>
    `;
    
    tbody.appendChild(row);
    calculateLine(lineCounter);
    
    console.log(`➕ Línea ${lineCounter} agregada`);
}

function removeLine(lineId) {
    const row = document.getElementById(`line-${lineId}`);
    if (row) {
        row.remove();
        calculateTotals();
        console.log(`➖ Línea ${lineId} eliminada`);
    }
}

function calculateLine(lineId) {
    const qtyElement = document.getElementById(`qty-${lineId}`);
    const priceElement = document.getElementById(`price-${lineId}`);
    const taxTypeElement = document.getElementById(`taxType-${lineId}`);
    
    if (!qtyElement || !priceElement || !taxTypeElement) return;
    
    const qty = parseFloat(qtyElement.value) || 0;
    const price = parseFloat(priceElement.value) || 0;
    const taxType = taxTypeElement.value;
    
    let value = qty * price;
    let igv = 0;
    let total = value;
    
    if (taxType === 'S') { // Gravado
        igv = value * 0.18;
        total = value + igv;
    } else if (taxType === 'Z') { // Gratuito
        value = 0;
        igv = 0;
        total = 0;
    }
    
    document.getElementById(`value-${lineId}`).textContent = value.toFixed(2);
    document.getElementById(`igv-${lineId}`).textContent = igv.toFixed(2);
    document.getElementById(`total-${lineId}`).textContent = total.toFixed(2);
    
    calculateTotals();
}

function calculateTotals() {
    let totalTaxed = 0;
    let totalExempt = 0;
    let totalFree = 0;
    let totalIGV = 0;
    let grandTotal = 0;
    
    const rows = document.querySelectorAll('#linesTableBody tr');
    rows.forEach(row => {
        const lineId = row.id.split('-')[1];
        const taxTypeElement = document.getElementById(`taxType-${lineId}`);
        const valueElement = document.getElementById(`value-${lineId}`);
        const igvElement = document.getElementById(`igv-${lineId}`);
        const totalElement = document.getElementById(`total-${lineId}`);
        
        if (taxTypeElement && valueElement && igvElement && totalElement) {
            const taxType = taxTypeElement.value;
            const value = parseFloat(valueElement.textContent) || 0;
            const igv = parseFloat(igvElement.textContent) || 0;
            const total = parseFloat(totalElement.textContent) || 0;
            
            switch(taxType) {
                case 'S':
                    totalTaxed += value;
                    break;
                case 'E':
                case 'O':
                    totalExempt += value;
                    break;
                case 'Z':
                    totalFree += value;
                    break;
            }
            
            totalIGV += igv;
            grandTotal += total;
        }
    });
    
    // Actualizar elementos de totales
    const elements = {
        'totalTaxed': totalTaxed,
        'totalExempt': totalExempt,
        'totalFree': totalFree,
        'totalIGV': totalIGV,
        'grandTotal': grandTotal
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value.toFixed(2);
        }
    });
    
    // Actualizar monto de pago
    const paymentAmountElement = document.getElementById('paymentAmount');
    if (paymentAmountElement) {
        paymentAmountElement.value = grandTotal.toFixed(2);
    }
}

function loadTestScenario() {
    console.log('📋 Cargando escenario de prueba...');
    
    // Limpiar líneas existentes
    const tbody = document.getElementById('linesTableBody');
    if (tbody) {
        tbody.innerHTML = '';
    }
    lineCounter = 0;
    
    // Agregar líneas de prueba
    addLine();
    document.getElementById(`desc-${lineCounter}`).value = 'PRODUCTO GRAVADO';
    document.getElementById(`qty-${lineCounter}`).value = '2';
    document.getElementById(`price-${lineCounter}`).value = '100.00';
    document.getElementById(`taxType-${lineCounter}`).value = 'S';
    calculateLine(lineCounter);
    
    addLine();
    document.getElementById(`desc-${lineCounter}`).value = 'PRODUCTO EXONERADO';
    document.getElementById(`qty-${lineCounter}`).value = '1';
    document.getElementById(`price-${lineCounter}`).value = '50.00';
    document.getElementById(`taxType-${lineCounter}`).value = 'E';
    calculateLine(lineCounter);
    
    addLine();
    document.getElementById(`desc-${lineCounter}`).value = 'PRODUCTO GRATUITO - BONIFICACION';
    document.getElementById(`qty-${lineCounter}`).value = '1';
    document.getElementById(`price-${lineCounter}`).value = '30.00';
    document.getElementById(`taxType-${lineCounter}`).value = 'Z';
    calculateLine(lineCounter);
    
    logMessage('✅ Escenario de prueba cargado con 3 líneas', 'success');
}

// ==================== API FUNCTIONS ====================
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken') // Agregar CSRF token
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const data = await response.json();
        
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

// Función para obtener CSRF token
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

function showProgress(message, detail = '') {
    const progressModal = document.getElementById('progressModal');
    const messageElement = document.getElementById('progress-message');
    const detailElement = document.getElementById('progress-detail');
    
    if (messageElement) messageElement.textContent = message;
    if (detailElement) detailElement.textContent = detail;
    
    if (progressModal) {
        const modal = new bootstrap.Modal(progressModal);
        modal.show();
    }
}

function hideProgress() {
    const progressModal = document.getElementById('progressModal');
    if (progressModal) {
        const modal = bootstrap.Modal.getInstance(progressModal);
        if (modal) modal.hide();
    }
}

function logMessage(message, type = 'info', data = null) {
    const container = document.getElementById('logsContainer');
    if (!container) {
        console.log(`${type.toUpperCase()}: ${message}`, data);
        return;
    }
    
    const timestamp = new Date().toLocaleTimeString();
    
    let badgeClass = 'bg-primary';
    let icon = 'bi-info-circle';
    
    switch(type) {
        case 'success':
            badgeClass = 'bg-success';
            icon = 'bi-check-circle';
            break;
        case 'error':
            badgeClass = 'bg-danger';
            icon = 'bi-x-circle';
            break;
        case 'warning':
            badgeClass = 'bg-warning';
            icon = 'bi-exclamation-triangle';
            break;
    }

    const logEntry = document.createElement('div');
    logEntry.className = 'border-start border-3 border-secondary ps-3 mb-3';
    
    let content = `
        <div class="d-flex align-items-center mb-2">
            <span class="badge ${badgeClass} me-2">
                <i class="${icon}"></i> ${type.toUpperCase()}
            </span>
            <small class="text-muted">${timestamp}</small>
        </div>
        <div class="mb-2">${message}</div>
    `;

    if (data) {
        const dataId = `data-${Date.now()}`;
        content += `
            <div class="mt-2">
                <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${dataId}">
                    <i class="bi bi-code"></i> Ver Datos
                </button>
                <div class="collapse mt-2" id="${dataId}">
                    <pre class="bg-light p-3 rounded small"><code>${JSON.stringify(data, null, 2)}</code></pre>
                </div>
            </div>
        `;
    }

    logEntry.innerHTML = content;
    container.appendChild(logEntry);
    container.scrollTop = container.scrollHeight;
    
    // También log en consola
    console.log(`${type.toUpperCase()}: ${message}`, data);
}

function clearLogs() {
    const container = document.getElementById('logsContainer');
    if (container) {
        container.innerHTML = `
            <div class="text-muted text-center p-4">
                <i class="bi bi-info-circle fs-1"></i>
                <p class="mt-2">Los logs del sistema aparecerán aquí</p>
            </div>
        `;
    }
}

// ==================== CREAR DOCUMENTO ====================
async function createInvoice() {
    console.log('📄 Iniciando creación de documento...');
    showProgress('Creando documento...', 'Validando datos y creando en el sistema');
    
    try {
        // Recopilar datos del formulario con validación
        const requiredFields = {
            'companyRuc': 'RUC de empresa',
            'companyName': 'Nombre de empresa',
            'customerDocNumber': 'Documento del cliente',
            'customerName': 'Nombre del cliente',
            'documentSeries': 'Serie del documento',
            'issueDate': 'Fecha de emisión'
        };
        
        // Validar campos requeridos
        for (const [fieldId, fieldName] of Object.entries(requiredFields)) {
            const element = document.getElementById(fieldId);
            if (!element || !element.value.trim()) {
                hideProgress();
                logMessage(`❌ Campo requerido: ${fieldName}`, 'error');
                return;
            }
        }
        
        const invoiceData = {
            company: {
                ruc: document.getElementById('companyRuc').value.trim(),
                business_name: document.getElementById('companyName').value.trim(),
                address: document.getElementById('companyAddress').value.trim()
            },
            customer: {
                document_type: document.getElementById('customerDocType').value,
                document_number: document.getElementById('customerDocNumber').value.trim(),
                business_name: document.getElementById('customerName').value.trim(),
                address: document.getElementById('customerAddress').value.trim()
            },
            document: {
                document_type: document.getElementById('documentType').value,
                series: document.getElementById('documentSeries').value.trim(),
                number: document.getElementById('documentNumber').value || null,
                issue_date: document.getElementById('issueDate').value,
                currency_code: document.getElementById('currency').value,
                observations: document.getElementById('observations').value.trim()
            },
            lines: [],
            payment: {
                payment_means_code: document.getElementById('paymentMethod').value,
                payment_amount: document.getElementById('paymentAmount').value
            }
        };

        // Recopilar líneas
        const rows = document.querySelectorAll('#linesTableBody tr');
        if (rows.length === 0) {
            hideProgress();
            logMessage('❌ Debe agregar al menos una línea de detalle', 'error');
            return;
        }
        
        rows.forEach((row, index) => {
            const lineId = row.id.split('-')[1];
            invoiceData.lines.push({
                line_number: index + 1,
                product_code: document.getElementById(`code-${lineId}`).value.trim(),
                description: document.getElementById(`desc-${lineId}`).value.trim(),
                quantity: parseFloat(document.getElementById(`qty-${lineId}`).value),
                unit_price: parseFloat(document.getElementById(`price-${lineId}`).value),
                tax_category_code: document.getElementById(`taxType-${lineId}`).value
            });
        });

        console.log('📤 Enviando datos:', invoiceData);
        
        const response = await apiCall('/create-invoice-manual/', 'POST', invoiceData);
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ Documento creado exitosamente', 'success', response.data);
            currentInvoiceId = response.data.invoice_id;
            
            const processInput = document.getElementById('processInvoiceId');
            if (processInput) {
                processInput.value = currentInvoiceId;
            }
            
            // Cambiar a tab de documentos
            const documentsTab = document.getElementById('documents-tab');
            if (documentsTab) {
                const tab = new bootstrap.Tab(documentsTab);
                tab.show();
                refreshDocuments();
            }
        } else {
            logMessage('❌ Error creando documento', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión al crear documento', 'error', { error: error.message });
    }
}

// ==================== GESTIÓN DE DOCUMENTOS ====================
async function refreshDocuments() {
    console.log('🔄 Actualizando lista de documentos...');
    
    try {
        const response = await apiCall('/documents/');
        
        if (response.ok) {
            currentDocuments = response.data.results || response.data;
            displayDocuments();
            logMessage(`📄 ${currentDocuments.length} documentos cargados`, 'info');
        } else {
            logMessage('❌ Error cargando documentos', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión al cargar documentos', 'error', { error: error.message });
    }
}

function displayDocuments() {
    const tbody = document.getElementById('documentsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!currentDocuments || currentDocuments.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted p-4">
                    <i class="bi bi-inbox fs-1"></i><br>
                    No hay documentos creados
                </td>
            </tr>
        `;
        return;
    }

    currentDocuments.forEach(doc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${doc.id}</td>
            <td>
                <span class="badge ${doc.document_type === '01' ? 'bg-primary' : 'bg-success'}">
                    ${doc.document_type === '01' ? 'Factura' : 'Boleta'}
                </span>
            </td>
            <td>${doc.document_reference || doc.full_document_name || `${doc.series}-${doc.number}`}</td>
            <td>${doc.customer_name || 'N/A'}</td>
            <td>S/ ${parseFloat(doc.total_amount || 0).toFixed(2)}</td>
            <td>
                <span class="badge ${getStatusBadgeClass(doc.status)}">
                    ${doc.status || 'PENDING'}
                </span>
            </td>
            <td>${formatDate(doc.created_at || doc.issue_date)}</td>
            <td>
                ${doc.xml_file ? '<i class="bi bi-file-code text-success" title="XML"></i>' : '<i class="bi bi-file-code text-muted"></i>'}
                ${doc.zip_file ? '<i class="bi bi-file-zip text-warning ms-1" title="ZIP"></i>' : '<i class="bi bi-file-zip text-muted ms-1"></i>'}
                ${doc.cdr_file ? '<i class="bi bi-file-check text-primary ms-1" title="CDR"></i>' : '<i class="bi bi-file-check text-muted ms-1"></i>'}
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-primary btn-sm" onclick="selectForProcessing(${doc.id})" title="Procesar">
                        <i class="bi bi-gear"></i>
                    </button>
                    ${doc.xml_file ? `<button class="btn btn-success btn-sm" onclick="viewFile('${doc.xml_file}', 'XML')" title="Ver XML"><i class="bi bi-file-code"></i></button>` : ''}
                    ${doc.cdr_file ? `<button class="btn btn-warning btn-sm" onclick="viewFile('${doc.cdr_file}', 'CDR')" title="Ver CDR"><i class="bi bi-file-check"></i></button>` : ''}
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function getStatusBadgeClass(status) {
    switch(status) {
        case 'SIGNED': return 'bg-success';
        case 'ACCEPTED': return 'bg-success';
        case 'SENT': return 'bg-info';
        case 'PROCESSING': return 'bg-warning';
        case 'ERROR': return 'bg-danger';
        case 'REJECTED': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-PE');
}

function selectForProcessing(invoiceId) {
    currentInvoiceId = invoiceId;
    const processInput = document.getElementById('processInvoiceId');
    if (processInput) {
        processInput.value = invoiceId;
    }
    
    // Cambiar a tab de procesamiento
    const processTab = document.getElementById('process-tab');
    if (processTab) {
        const tab = new bootstrap.Tab(processTab);
        tab.show();
    }
    
    // Cargar detalles del documento
    loadDocumentDetails(invoiceId);
    
    logMessage(`📄 Documento ${invoiceId} seleccionado para procesamiento`, 'info');
}

async function loadDocumentDetails(invoiceId) {
    try {
        const response = await apiCall(`/invoice/${invoiceId}/status/`);
        
        if (response.ok) {
            displayDocumentDetails(response.data);
            displayFiles(response.data);
        } else {
            logMessage('❌ Error cargando detalles del documento', 'error', response.data);
        }
    } catch (error) {
        logMessage('❌ Error de conexión al cargar detalles', 'error', { error: error.message });
    }
}

function displayDocumentDetails(docData) {
    const container = document.getElementById('currentDocumentDetails');
    if (!container) return;
    
    container.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-primary">Documento ${docData.invoice_id}</h6>
                <table class="table table-sm">
                    <tr><td><strong>Referencia:</strong></td><td>${docData.document_reference || 'N/A'}</td></tr>
                    <tr><td><strong>Estado:</strong></td><td><span class="badge ${getStatusBadgeClass(docData.status)}">${docData.status}</span></td></tr>
                    <tr><td><strong>Creado:</strong></td><td>${formatDate(docData.created_at)}</td></tr>
                    <tr><td><strong>Actualizado:</strong></td><td>${formatDate(docData.updated_at)}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6 class="text-success">Totales</h6>
                <table class="table table-sm">
                    <tr><td>Gravado:</td><td>S/ ${parseFloat(docData.totals?.total_taxed_amount || 0).toFixed(2)}</td></tr>
                    <tr><td>Exonerado:</td><td>S/ ${parseFloat(docData.totals?.total_exempt_amount || 0).toFixed(2)}</td></tr>
                    <tr><td>IGV:</td><td>S/ ${parseFloat(docData.totals?.igv_amount || 0).toFixed(2)}</td></tr>
                    <tr><td><strong>Total:</strong></td><td><strong>S/ ${parseFloat(docData.totals?.total_amount || 0).toFixed(2)}</strong></td></tr>
                </table>
            </div>
        </div>
        
        ${docData.sunat_info?.response_code ? `
            <div class="alert alert-info mt-3">
                <h6>Información SUNAT</h6>
                <p class="mb-1"><strong>Código:</strong> ${docData.sunat_info.response_code}</p>
                <p class="mb-0"><strong>Descripción:</strong> ${docData.sunat_info.response_description || 'N/A'}</p>
                ${docData.sunat_info.ticket ? `<p class="mb-0"><strong>Ticket:</strong> ${docData.sunat_info.ticket}</p>` : ''}
            </div>
        ` : ''}
    `;
}

function displayFiles(docData) {
    const container = document.getElementById('filesViewer');
    if (!container) return;
    
    const files = [
        { type: 'XML', file: docData.files?.xml_file, icon: 'file-code', color: 'success' },
        { type: 'ZIP', file: docData.files?.zip_file, icon: 'file-zip', color: 'warning' },
        { type: 'CDR', file: docData.files?.cdr_file, icon: 'file-check', color: 'primary' }
    ];
    
    let filesHtml = '';
    files.forEach(fileInfo => {
        const available = fileInfo.file ? true : false;
        filesHtml += `
            <div class="col-md-4 mb-3">
                <div class="card ${available ? 'border-' + fileInfo.color : 'border-secondary'}">
                    <div class="card-body text-center">
                        <i class="bi bi-${fileInfo.icon} fs-1 ${available ? 'text-' + fileInfo.color : 'text-muted'}"></i>
                        <h6 class="mt-2">${fileInfo.type}</h6>
                        ${available ? 
                            `<button class="btn btn-${fileInfo.color} btn-sm" onclick="viewFile('${fileInfo.file}', '${fileInfo.type}')">
                                <i class="bi bi-eye"></i> Ver
                            </button>` :
                            '<span class="text-muted">No generado</span>'
                        }
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = filesHtml;
}

// ==================== VISOR DE ARCHIVOS ====================
async function viewFile(filePath, fileType) {
    try {
        const response = await fetch(`${API_BASE_URL}/file-content/?path=${encodeURIComponent(filePath)}`);
        
        if (response.ok) {
            const content = await response.text();
            
            document.getElementById('fileViewerTitle').textContent = `${fileType} - ${filePath.split('/').pop()}`;
            document.getElementById('fileViewerContent').textContent = content;
            
            const modal = new bootstrap.Modal(document.getElementById('fileViewerModal'));
            modal.show();
        } else {
            logMessage(`❌ Error cargando archivo ${fileType}`, 'error');
        }
    } catch (error) {
        logMessage(`❌ Error de conexión al cargar archivo ${fileType}`, 'error', { error: error.message });
    }
}

function downloadCurrentFile() {
    const content = document.getElementById('fileViewerContent').textContent;
    const title = document.getElementById('fileViewerTitle').textContent;
    const filename = title.split(' - ')[1] || 'archivo.txt';
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ==================== FUNCIONES DE PROCESAMIENTO ====================
async function testConnection() {
    console.log('🔌 Probando conexión...');
    showProgress('Probando conexión...', 'Verificando servidor y SUNAT');
    
    try {
        const response = await apiCall('/test-sunat-connection/');
        hideProgress();
        
        if (response.ok) {
            updateServerStatus('connected');
            if (response.data.status === 'warning') {
                logMessage('⚠️ Servidor conectado - Error 401 SUNAT normal con credenciales de prueba', 'warning', response.data);
            } else {
                logMessage('✅ Conexión exitosa', 'success', response.data);
            }
        } else {
            updateServerStatus('disconnected');
            logMessage('⚠️ Problemas de conexión', 'warning', response.data);
        }
    } catch (error) {
        hideProgress();
        updateServerStatus('disconnected');
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function createTestScenarios() {
    console.log('🧪 Creando escenarios de prueba...');
    showProgress('Creando escenarios de prueba...', 'Generando documento con todos los tipos de operaciones');
    
    try {
        const response = await apiCall('/create-test-scenarios/', 'POST');
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ Escenarios de prueba creados', 'success', response.data);
            currentInvoiceId = response.data.invoice_id;
            
            const processInput = document.getElementById('processInvoiceId');
            if (processInput) {
                processInput.value = currentInvoiceId;
            }
            
            refreshDocuments();
            loadDocumentDetails(currentInvoiceId);
        } else {
            logMessage('❌ Error creando escenarios', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function convertToUBL() {
    const invoiceId = document.getElementById('processInvoiceId').value;
    if (!invoiceId) {
        logMessage('⚠️ Ingrese un ID de documento', 'warning');
        return;
    }

    console.log(`🔄 Convirtiendo documento ${invoiceId} a UBL...`);
    showProgress('Convirtiendo a UBL XML...', 'Generando documento XML estándar UBL 2.1');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/convert-ubl/`, 'POST');
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ XML UBL generado exitosamente', 'success', response.data);
            loadDocumentDetails(invoiceId);
        } else {
            logMessage('❌ Error en conversión UBL', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function signXML() {
    const invoiceId = document.getElementById('processInvoiceId').value;
    if (!invoiceId) {
        logMessage('⚠️ Ingrese un ID de documento', 'warning');
        return;
    }

    console.log(`✍️ Firmando XML del documento ${invoiceId}...`);
    showProgress('Firmando XML...', 'Aplicando firma digital con certificado X.509');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/sign/`, 'POST');
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ XML firmado exitosamente', 'success', response.data);
            loadDocumentDetails(invoiceId);
        } else {
            logMessage('❌ Error en firma digital', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function sendToSUNAT() {
    const invoiceId = document.getElementById('processInvoiceId').value;
    if (!invoiceId) {
        logMessage('⚠️ Ingrese un ID de documento', 'warning');
        return;
    }

    console.log(`📤 Enviando documento ${invoiceId} a SUNAT...`);
    showProgress('Enviando a SUNAT...', 'Transmitiendo documento firmado');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/send-sunat/`, 'POST');
        hideProgress();
        
        if (response.ok || (response.data && response.data.status === 'warning')) {
            if (response.data.status === 'warning') {
                logMessage('⚠️ Error de autenticación SUNAT (normal con credenciales de prueba)', 'warning', response.data);
                logMessage('✅ Documento XML generado y firmado correctamente', 'success');
                logMessage('💡 Para envío real necesita credenciales válidas de producción', 'info');
            } else {
                logMessage('✅ Documento enviado a SUNAT', 'success', response.data);
            }
            loadDocumentDetails(invoiceId);
        } else {
            logMessage('❌ Error enviando a SUNAT', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function checkStatus() {
    const invoiceId = document.getElementById('processInvoiceId').value;
    if (!invoiceId) {
        logMessage('⚠️ Ingrese un ID de documento', 'warning');
        return;
    }

    console.log(`🔍 Consultando estado del documento ${invoiceId}...`);
    showProgress('Consultando estado...', 'Verificando estado actual del documento');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/status/`);
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ Estado consultado', 'success', response.data);
            displayDocumentDetails(response.data);
            displayFiles(response.data);
        } else {
            logMessage('❌ Error consultando estado', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

async function processCompleteFlow() {
    const invoiceId = document.getElementById('processInvoiceId').value;
    if (!invoiceId) {
        logMessage('⚠️ Ingrese un ID de documento', 'warning');
        return;
    }

    console.log(`🚀 Iniciando flujo completo para documento ${invoiceId}...`);
    showProgress('Procesando flujo completo...', 'Ejecutando: UBL → Firma → Envío SUNAT');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/process-complete/`, 'POST');
        hideProgress();
        
        if (response.ok) {
            const data = response.data;
            
            if (data.overall_status === 'success' || data.overall_status === 'success_with_warnings') {
                logMessage('✅ Flujo completo procesado exitosamente', 'success', data);
                
                if (data.overall_status === 'success_with_warnings') {
                    logMessage('💡 Nota: Errores de SUNAT son normales con credenciales de prueba', 'info');
                }
            } else {
                logMessage('⚠️ Flujo completado con errores', 'warning', data);
            }
            
            // Mostrar resumen de pasos
            if (data.steps) {
                logMessage('📋 Resumen de pasos:', 'info');
                data.steps.forEach((step, index) => {
                    const stepIcon = step.status === 'success' ? '✅' : 
                                   step.status === 'warning' ? '⚠️' : '❌';
                    const stepType = step.status === 'warning' ? 'warning' : step.status;
                    logMessage(`${stepIcon} Paso ${index + 1}: ${step.message}`, stepType);
                });
            }
            
            loadDocumentDetails(invoiceId);
        } else {
            logMessage('❌ Error en flujo completo', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión', 'error', { error: error.message });
    }
}

function showSunatHelp() {
    logMessage('📚 Ayuda - Sistema UBL 2.1', 'info', {
        'Error 401 SUNAT': 'Normal con credenciales de prueba MODDATOS',
        'Estado SIGNED': 'Documento listo - XML firmado correctamente',
        'Archivos generados': 'XML y ZIP se crean sin problemas',
        'CDR': 'Se recibe después del envío exitoso a SUNAT',
        'Para producción': 'Configurar credenciales reales en .env'
    });
    
    logMessage('🔧 Estados del sistema:', 'info', {
        'PENDING': 'Documento creado, esperando procesamiento',
        'PROCESSING': 'Generando XML UBL',
        'SIGNED': 'XML firmado digitalmente (listo para uso)',
        'SENT': 'Enviado a SUNAT exitosamente', 
        'ACCEPTED': 'Aceptado por SUNAT con CDR',
        'ERROR': 'Error en procesamiento'
    });
    
    logMessage('🎯 Flujo recomendado:', 'info', {
        '1. Crear documento': 'Usar formulario manual o escenarios de prueba',
        '2. Procesar': 'Convertir a UBL → Firmar → Enviar',
        '3. Verificar archivos': 'XML, ZIP y CDR generados',
        '4. Estado final': 'SIGNED = Sistema funcionando correctamente'
    });
}

// ==================== ATAJOS DE TECLADO ====================
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey) {
        switch(e.key) {
            case '1':
                e.preventDefault();
                createTestScenarios();
                break;
            case '2':
                e.preventDefault();
                if (currentInvoiceId) {
                    processCompleteFlow();
                } else {
                    logMessage('⚠️ Seleccione un documento primero', 'warning');
                }
                break;
            case '3':
                e.preventDefault();
                if (currentInvoiceId) {
                    checkStatus();
                } else {
                    logMessage('⚠️ Seleccione un documento primero', 'warning');
                }
                break;
            case 'l':
                e.preventDefault();
                clearLogs();
                break;
            case 'h':
                e.preventDefault();
                showSunatHelp();
                break;
        }
    }
});

// ==================== AUTO-INICIALIZACIÓN ====================
// Probar conexión automáticamente al cargar
setTimeout(() => {
    console.log('🔄 Probando conexión automática...');
    testConnection();
}, 2000);

// Log de inicialización final
console.log('🎉 Conversor UBL 2.1 cargado completamente');
console.log('📚 Atajos disponibles:');
console.log('   Ctrl+1: Crear escenarios de prueba');
console.log('   Ctrl+2: Procesar flujo completo');
console.log('   Ctrl+3: Consultar estado');
console.log('   Ctrl+L: Limpiar logs');
console.log('   Ctrl+H: Mostrar ayuda');