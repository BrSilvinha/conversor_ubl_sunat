// ubl-tester.js - JavaScript para el frontend del Conversor UBL 2.1
// Configuración
const API_BASE_URL = 'http://localhost:8000/api';
let currentInvoiceId = null;
let progressModal = null;

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    progressModal = new bootstrap.Modal(document.getElementById('progressModal'));
    updateTimestamp();
    setInterval(updateTimestamp, 1000);
    logMessage('Sistema iniciado. Listo para pruebas.', 'info');
});

// ==================== UTILIDADES ====================
function updateTimestamp() {
    document.getElementById('timestamp').textContent = new Date().toLocaleString();
}

function showProgress(message, detail = '') {
    document.getElementById('progress-message').textContent = message;
    document.getElementById('progress-detail').textContent = detail;
    progressModal.show();
}

function hideProgress() {
    progressModal.hide();
}

function updateServerStatus(status) {
    const statusElement = document.getElementById('server-status');
    if (status === 'connected') {
        statusElement.textContent = 'Conectado';
        statusElement.className = 'badge bg-success text-white';
    } else {
        statusElement.textContent = 'Desconectado';
        statusElement.className = 'badge bg-danger text-white';
    }
}

function logMessage(message, type = 'info', data = null) {
    const container = document.getElementById('response-container');
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
                <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${dataId}" aria-expanded="false">
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
}

function clearLogs() {
    const container = document.getElementById('response-container');
    container.innerHTML = `
        <div class="text-muted text-center p-4">
            <i class="bi bi-info-circle fs-1"></i>
            <p class="mt-2">Logs limpiados. Los resultados aparecerán aquí.</p>
        </div>
    `;
}

function updateInvoiceInfo(invoiceData) {
    currentInvoiceId = invoiceData.invoice_id;
    document.getElementById('invoiceId').value = currentInvoiceId;
    
    const infoCard = document.getElementById('invoice-info');
    const detailsDiv = document.getElementById('invoice-details');
    
    detailsDiv.innerHTML = `
        <div class="row">
            <div class="col-12">
                <h6 class="text-primary">ID: ${invoiceData.invoice_id}</h6>
                <p class="mb-2"><strong>Referencia:</strong> ${invoiceData.invoice_reference || invoiceData.document_reference || 'N/A'}</p>
                <p class="mb-2"><strong>Estado:</strong> 
                    <span class="badge bg-info">${invoiceData.status || 'N/A'}</span>
                </p>
            </div>
        </div>
        ${invoiceData.totals ? `
            <div class="row mt-2">
                <div class="col-12">
                    <h6>Totales:</h6>
                    <ul class="list-unstyled small">
                        <li>• Gravado: S/ ${parseFloat(invoiceData.totals.total_taxed_amount || 0).toFixed(2)}</li>
                        <li>• Exonerado: S/ ${parseFloat(invoiceData.totals.total_exempt_amount || 0).toFixed(2)}</li>
                        <li>• IGV: S/ ${parseFloat(invoiceData.totals.igv_amount || 0).toFixed(2)}</li>
                        <li>• Percepción: S/ ${parseFloat(invoiceData.totals.perception_amount || 0).toFixed(2)}</li>
                        <li><strong>Total: S/ ${parseFloat(invoiceData.totals.total_amount || 0).toFixed(2)}</strong></li>
                    </ul>
                </div>
            </div>
        ` : ''}
        ${invoiceData.files ? `
            <div class="row mt-2">
                <div class="col-12">
                    <h6>Archivos:</h6>
                    <ul class="list-unstyled small">
                        <li>• XML: ${invoiceData.files.xml_file ? '✅ Generado' : '❌ No generado'}</li>
                        <li>• ZIP: ${invoiceData.files.zip_file ? '✅ Generado' : '❌ No generado'}</li>
                        <li>• CDR: ${invoiceData.files.cdr_file ? '✅ Generado' : '❌ No generado'}</li>
                    </ul>
                </div>
            </div>
        ` : ''}
        ${invoiceData.sunat_info && invoiceData.sunat_info.response_code ? `
            <div class="row mt-2">
                <div class="col-12">
                    <h6>SUNAT:</h6>
                    <p class="small mb-1"><strong>Código:</strong> ${invoiceData.sunat_info.response_code}</p>
                    <p class="small mb-0"><strong>Descripción:</strong> ${invoiceData.sunat_info.response_description || 'N/A'}</p>
                </div>
            </div>
        ` : ''}
    `;
    
    infoCard.style.display = 'block';
}

function getInvoiceId() {
    const invoiceId = document.getElementById('invoiceId').value;
    if (!invoiceId) {
        logMessage('⚠️ Por favor ingrese un ID de factura o cree escenarios de prueba primero', 'warning');
        return null;
    }
    return invoiceId;
}

// ==================== API FUNCTIONS ====================
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
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
        return {
            ok: false,
            status: 0,
            error: error.message
        };
    }
}

// ==================== TEST FUNCTIONS ====================
async function testConnection() {
    showProgress('Probando conexión con el servidor...', 'Verificando estado del sistema');
    
    try {
        // Probar conexión básica
        const response = await apiCall('/test-sunat-connection/');
        hideProgress();
        
        if (response.ok) {
            updateServerStatus('connected');
            logMessage('✅ Conexión exitosa con el servidor', 'success', response.data);
            
            // Mostrar información específica del ambiente
            const data = response.data;
            if (data.environment) {
                logMessage(`🌐 Ambiente: ${data.environment}`, 'info');
            }
            if (data.operations && data.operations.length > 0) {
                logMessage(`🔧 Operaciones disponibles: ${data.operations.join(', ')}`, 'info');
            }
        } else {
            updateServerStatus('disconnected');
            if (response.data && response.data.status === 'warning') {
                logMessage('⚠️ Servidor responde pero hay problemas de autenticación SUNAT (normal con credenciales de prueba)', 'warning', response.data);
                updateServerStatus('connected'); // Cambiar a conectado porque el servidor Django sí responde
            } else {
                logMessage('❌ Servidor responde pero hay problemas de configuración', 'error', response.data);
            }
        }
    } catch (error) {
        hideProgress();
        updateServerStatus('disconnected');
        logMessage('❌ Error de conexión con el servidor Django', 'error', { 
            error: error.message,
            suggestion: 'Verifique que el servidor esté ejecutándose con: python manage.py runserver'
        });
    }
}

async function createTestScenarios() {
    showProgress('Creando escenarios de prueba...', 'Generando boleta con todos los tipos de operaciones');
    
    try {
        const response = await apiCall('/create-test-scenarios/', 'POST');
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ Escenarios de prueba creados exitosamente', 'success', response.data);
            updateInvoiceInfo(response.data);
            
            // Mostrar detalles específicos de los escenarios
            const data = response.data;
            logMessage(`📄 Documento creado: ${data.invoice_reference}`, 'info');
            
            if (data.totals) {
                logMessage('💰 Escenarios incluidos:', 'info', {
                    'Venta Gravada (IGV 18%)': `S/ ${parseFloat(data.totals.total_taxed_amount).toFixed(2)}`,
                    'Venta Exonerada': `S/ ${parseFloat(data.totals.total_exempt_amount).toFixed(2)}`,
                    'IGV Calculado': `S/ ${parseFloat(data.totals.igv_amount).toFixed(2)}`,
                    'Percepción (2%)': `S/ ${parseFloat(data.totals.perception_amount).toFixed(2)}`,
                    'Total Final': `S/ ${parseFloat(data.totals.total_amount).toFixed(2)}`
                });
            }
        } else {
            logMessage('❌ Error creando escenarios de prueba', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión al crear escenarios', 'error', { error: error.message });
    }
}

async function convertToUBL() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    showProgress('Convirtiendo a UBL XML...', 'Generando documento XML según estándar UBL 2.1');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/convert-ubl/`, 'POST');
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ Conversión a UBL XML exitosa', 'success', response.data);
            
            const data = response.data;
            if (data.xml_filename) {
                logMessage(`📄 Archivo XML generado: ${data.xml_filename}`, 'info');
            }
            if (data.xml_path) {
                logMessage(`📁 Ubicación: ${data.xml_path}`, 'info');
            }
        } else {
            logMessage('❌ Error en conversión UBL', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión en conversión UBL', 'error', { error: error.message });
    }
}

async function signXML() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    showProgress('Firmando documento XML...', 'Aplicando firma digital con certificado X.509');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/sign/`, 'POST');
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ Firma digital aplicada exitosamente', 'success', response.data);
            
            const data = response.data;
            if (data.signed_xml_path) {
                logMessage(`🔐 XML firmado: ${data.signed_xml_path.split('/').pop()}`, 'info');
            }
            if (data.zip_path) {
                logMessage(`📦 ZIP creado: ${data.zip_path.split('/').pop()}`, 'info');
            }
            if (data.certificate_info) {
                logMessage('📜 Certificado utilizado:', 'info', {
                    'RUC': data.certificate_info.ruc || 'N/A',
                    'Válido hasta': data.certificate_info.not_valid_after || 'N/A',
                    'Estado': data.certificate_info.is_valid ? 'Válido' : 'Expirado'
                });
            }
        } else {
            logMessage('❌ Error en firma digital', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión en firma digital', 'error', { error: error.message });
    }
}

async function sendToSUNAT() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    showProgress('Enviando a SUNAT...', 'Transmitiendo documento firmado via WebServices');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/send-sunat/`, 'POST');
        hideProgress();
        
        if (response.ok) {
            const data = response.data;
            const sunatResponse = data.sunat_response;
            
            if (sunatResponse && sunatResponse.status === 'success') {
                logMessage('✅ Documento enviado a SUNAT exitosamente', 'success', data);
                
                if (sunatResponse.response_type === 'cdr') {
                    logMessage('📄 Respuesta síncrona recibida (CDR)', 'info');
                    if (sunatResponse.cdr_info) {
                        const cdrInfo = sunatResponse.cdr_info;
                        logMessage('📋 CDR procesado:', 'info', {
                            'Código de respuesta': cdrInfo.response_code || 'N/A',
                            'Descripción': cdrInfo.response_description || 'N/A',
                            'Documento': cdrInfo.document_reference || 'N/A'
                        });
                    }
                } else if (sunatResponse.response_type === 'ticket') {
                    logMessage(`🎫 Ticket asíncrono recibido: ${sunatResponse.ticket}`, 'info');
                    logMessage('ℹ️ Use "Consultar Estado" para verificar el procesamiento', 'info');
                }
            } else {
                logMessage('⚠️ Documento enviado pero con advertencias de SUNAT', 'warning', data);
                if (sunatResponse && sunatResponse.error_message) {
                    logMessage(`⚠️ SUNAT: ${sunatResponse.error_message}`, 'warning');
                }
            }
        } else {
            logMessage('❌ Error enviando a SUNAT', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión al enviar a SUNAT', 'error', { error: error.message });
    }
}

async function checkStatus() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    showProgress('Consultando estado...', 'Verificando estado actual del documento');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/status/`);
        hideProgress();
        
        if (response.ok) {
            logMessage('✅ Estado consultado exitosamente', 'success', response.data);
            updateInvoiceInfo(response.data);
            
            const data = response.data;
            logMessage(`📊 Estado actual: ${data.status}`, 'info');
            
            // Mostrar progreso de archivos
            if (data.files) {
                const files = data.files;
                const fileStatus = {
                    'XML generado': files.xml_file ? '✅' : '❌',
                    'ZIP firmado': files.zip_file ? '✅' : '❌',
                    'CDR de SUNAT': files.cdr_file ? '✅' : '❌'
                };
                logMessage('📁 Estado de archivos:', 'info', fileStatus);
            }
        } else {
            logMessage('❌ Error consultando estado', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión al consultar estado', 'error', { error: error.message });
    }
}

async function processCompleteFlow() {
    const invoiceId = getInvoiceId();
    if (!invoiceId) return;

    showProgress('Procesando flujo completo...', 'Ejecutando: UBL → Firma → Envío SUNAT');
    
    try {
        const response = await apiCall(`/invoice/${invoiceId}/process-complete/`, 'POST');
        hideProgress();
        
        if (response.ok) {
            const data = response.data;
            const overallStatus = data.overall_status;
            
            if (overallStatus === 'success') {
                logMessage('✅ Flujo completo procesado exitosamente', 'success');
            } else {
                logMessage('⚠️ Flujo completado con advertencias', 'warning');
            }
            
            // Mostrar resumen de pasos
            if (data.steps) {
                logMessage('📋 Resumen de pasos ejecutados:', 'info');
                data.steps.forEach((step, index) => {
                    const stepType = step.status === 'success' ? 'success' : 'error';
                    const stepIcon = step.status === 'success' ? '✅' : '❌';
                    logMessage(`${stepIcon} Paso ${index + 1} - ${step.step}: ${step.message}`, stepType);
                });
                
                // Mostrar estadísticas
                const successSteps = data.steps.filter(s => s.status === 'success').length;
                const totalSteps = data.steps.length;
                logMessage(`📊 Resultado: ${successSteps}/${totalSteps} pasos exitosos`, 'info');
            }
            
            // Consultar estado final
            setTimeout(() => checkStatus(), 1000);
        } else {
            logMessage('❌ Error en flujo completo', 'error', response.data);
        }
    } catch (error) {
        hideProgress();
        logMessage('❌ Error de conexión en flujo completo', 'error', { error: error.message });
    }
}

// ==================== KEYBOARD SHORTCUTS ====================
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey) {
        switch(e.key) {
            case '1':
                e.preventDefault();
                createTestScenarios();
                break;
            case '2':
                e.preventDefault();
                processCompleteFlow();
                break;
            case '3':
                e.preventDefault();
                checkStatus();
                break;
            case 'l':
                e.preventDefault();
                clearLogs();
                break;
        }
    }
});

// Auto-test opcional al cargar
// setTimeout(() => testConnection(), 1000);