(function () {
    'use strict';

    const instanceIdInput = document.getElementById('instanceId');
    const lastVersionCheck = document.getElementById('lastVersionCheck');
    const versionSelect = document.getElementById('versionSelect');
    const versionGroup = document.getElementById('versionGroup');
    const previewSection = document.getElementById('previewSection');
    const searchBtnHeader = document.getElementById('searchBtnHeader');
    const loadBtn = document.getElementById('loadBtn');
    const goldenRecordFile = document.getElementById('goldenRecordFile');
    
    // Preview elements
    const previewId = document.getElementById('previewId');
    const previewCliente = document.getElementById('previewCliente');
    const previewConsultor = document.getElementById('previewConsultor');
    const previewFecha = document.getElementById('previewFecha');
    const previewVersion = document.getElementById('previewVersion');
    const previewPath = document.getElementById('previewPath');
    const versionBadge = document.getElementById('versionBadge');

    // State
    let currentMetadata = null;
    let validationResults = null;
    let currentInstanceId = null;

    // Event Listeners
    lastVersionCheck.addEventListener('change', function() {
        if (this.checked) {
            versionGroup.style.display = 'none';
            versionSelect.disabled = true;
            
            // Si ya hay un ID de instancia cargado, recargar con última versión
            if (currentInstanceId) {
                loadMetadata(currentInstanceId, 'latest');
            }
        } else {
            versionGroup.style.display = 'block';
            versionSelect.disabled = false;
            
            // Si ya hay un ID de instancia cargado, cargar lista de versiones
            if (currentInstanceId) {
                loadVersions(currentInstanceId, true); // No cargar automáticamente
            }
        }
    });

    versionSelect.addEventListener('change', function() {
        if (this.value && currentInstanceId) {
            loadMetadata(currentInstanceId, this.value);
        }
    });

    goldenRecordFile.addEventListener('change', function(e) {
        const fileName = e.target.files[0]?.name || 'Ningún archivo seleccionado';
        document.getElementById('goldenRecordFileName').textContent = fileName;
    });

    searchBtnHeader.addEventListener('click', handleSearch);
    loadBtn.addEventListener('click', handleValidation);

    // Main Functions
    async function handleSearch() {
        const instanceId = instanceIdInput.value.trim();
        
        if (!instanceId) {
            showToast('Por favor ingresa un ID de instancia', 'error');
            return;
        }

        searchBtnHeader.disabled = true;
        searchBtnHeader.textContent = 'Buscando...';
        clearResults();
        previewSection.style.display = 'none';
        loadBtn.style.display = 'none';
        currentMetadata = null;
        currentInstanceId = instanceId;

        try {
            const useLastVersion = lastVersionCheck.checked;
            
            if (useLastVersion) {
                await loadMetadata(instanceId, 'latest');
            } else {
                await loadVersions(instanceId, false); // Cargar y seleccionar primera
                versionGroup.style.display = 'block';
            }

        } catch (error) {
            console.error('Error:', error);
            showToast(`Error: ${error.message}`, 'error');
            currentInstanceId = null;
        } finally {
            searchBtnHeader.disabled = false;
            searchBtnHeader.textContent = 'Buscar';
        }
    }

    async function loadVersions(instanceId, skipAutoLoad = false) {
        try {
            versionSelect.innerHTML = '<option value="">Cargando versiones...</option>';
            
            const response = await fetch(`/api/v1/structure/versions/${instanceId}`, {
                method: 'GET',
                credentials: 'include'
            });

            if (!response.ok) return;
            
            const versions = await response.json();
            
            if (versions.length === 0) {
                versionSelect.innerHTML = '<option value="">No hay versiones disponibles</option>';
                return;
            }
            
            versionSelect.innerHTML = '';
            versions.forEach(version => {
                const option = document.createElement('option');
                option.value = version;
                option.textContent = version;
                versionSelect.appendChild(option);
            });
            
            // Cargar automáticamente la primera versión solo si no se indica saltar
            if (!skipAutoLoad && versions.length > 0) {
                versionSelect.value = versions[0];
                await loadMetadata(instanceId, versions[0]);
            }
            
        } catch (error) {
            console.error('Error loading versions:', error);
            versionSelect.innerHTML = '<option value="">Error cargando versiones</option>';
        }
    }

    async function loadMetadata(instanceId, version) {
        try {
            const response = await fetch(`/api/v1/structure/metadata/${instanceId}?version=${version}`, {
                method: 'GET',
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error al cargar metadata');
            }

            currentMetadata = await response.json();
            updatePreview(currentMetadata);
            previewSection.style.display = 'block';
            loadBtn.style.display = 'block';
            
            showToast(`Versión ${version} cargada`, 'success');

        } catch (error) {
            console.error('Error:', error);
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    async function handleValidation() {
        const instanceId = instanceIdInput.value.trim();
        const file = goldenRecordFile.files[0];
        
        if (!file) {
            showToast('Por favor selecciona un archivo CSV', 'error');
            return;
        }

        if (!file.name.endsWith('.csv')) {
            showToast('El archivo debe ser CSV', 'error');
            return;
        }

        if (!currentMetadata) {
            showToast('Primero busca la metadata', 'error');
            return;
        }

        loadBtn.disabled = true;
        loadBtn.textContent = 'Validando...';
        showLoader(true, 'Validando estructura...');

        const formData = new FormData();
        formData.append('golden_file', file);
        
        const useLastVersion = lastVersionCheck.checked;
        const version = useLastVersion ? 'latest' : (versionSelect.value || 'latest');
        formData.append('metadata_id', instanceId);
        formData.append('version', version);

        try {
            const response = await fetch('/api/v1/structure/validate', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (!response.ok) {
                let errorDetail = 'Error en validación';
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || JSON.stringify(errorData);
                } catch (e) {
                    errorDetail = `HTTP ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorDetail);
            }

            validationResults = await response.json();
            displayValidationResults(validationResults);
            showToast('Validación completada exitosamente', 'success');

        } catch (error) {
            console.error('Error:', error);
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            showLoader(false);
            loadBtn.disabled = false;
            loadBtn.textContent = 'Validar Estructura';
        }
    }

    // Helper Functions
    function updatePreview(metadata) {
        previewId.textContent = metadata.id || '-';
        previewCliente.textContent = metadata.cliente || '-';
        previewConsultor.textContent = metadata.consultor || '-';
        previewFecha.textContent = metadata.fecha ? new Date(metadata.fecha).toLocaleString() : '-';
        previewVersion.textContent = metadata.version || '-';
        previewPath.textContent = metadata.path || '-';
        
        if (versionBadge) {
            versionBadge.textContent = metadata.version || 'v1.0';
        }
    }

    function displayValidationResults(results) {
        const totalErrors = results.total_errors || 0;
        const executionTime = results.execution_time || 0;
        const summary = results.summary || {};
        
        // Eliminar resultado anterior si existe
        const existingResults = document.querySelector('.validation-results-container');
        if (existingResults) {
            existingResults.remove();
        }
        
        const container = document.createElement('div');
        container.className = 'validation-results-container';
        container.style.cssText = `
            margin-top: 30px;
            background: var(--color-white);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-form);
            overflow: hidden;
        `;
        
        let resultHTML = `
            <div class="validation-results">
                <div class="form-header">
                    <h3>Resultados de Validación</h3>
                </div>
                
                <div class="form-content" style="padding: var(--spacing-md);">
                    <div class="stats-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;">
                        <div class="stat-card" style="background: ${totalErrors === 0 ? '#e8f5e9' : '#ffebee'}; padding: 15px; border-radius: 5px; text-align: center; border-left: 4px solid ${totalErrors === 0 ? '#4CAF50' : '#f44336'};">
                            <div style="font-size: 24px; font-weight: bold; color: ${totalErrors === 0 ? '#2e7d32' : '#c62828'};">${totalErrors}</div>
                            <div style="font-size: 13px; color: #666;">Errores encontrados</div>
                        </div>
                        
                        <div class="stat-card" style="background: #e3f2fd; padding: 15px; border-radius: 5px; text-align: center; border-left: 4px solid #2196F3;">
                            <div style="font-size: 24px; font-weight: bold; color: #1565c0;">${executionTime.toFixed(2)}s</div>
                            <div style="font-size: 13px; color: #666;">Tiempo de ejecución</div>
                        </div>
                        
                        <div class="stat-card" style="background: #f3e5f5; padding: 15px; border-radius: 5px; text-align: center; border-left: 4px solid #9C27B0;">
                            <div style="font-size: 24px; font-weight: bold; color: #6a1b9a;">${summary.total_rows || 0}</div>
                            <div style="font-size: 13px; color: #666;">Filas procesadas</div>
                        </div>
                    </div>
        `;
        
        if (totalErrors > 0) {
            const errors = results.report?.validation_results?.errors || [];
            resultHTML += `
                <div style="margin-top: 20px;">
                    <h4 style="margin-bottom: 10px; color: #c62828;">Errores detectados:</h4>
                    <div style="max-height: 200px; overflow-y: auto; background: #f5f5f5; border-radius: 4px; padding: 10px;">
            `;
            
            errors.slice(0, 10).forEach(error => {
                resultHTML += `
                    <div style="padding: 8px; border-bottom: 1px solid #ddd; font-size: 13px;">
                        <span style="font-weight: bold; color: #666;">Fila ${error.row || 'N/A'}</span>
                        <span style="color: #2196F3; margin: 0 10px;">${error.field || 'N/A'}</span>
                        <span style="color: #c62828;">${error.error_message || error.error_type}</span>
                    </div>
                `;
            });
            
            if (errors.length > 10) {
                resultHTML += `<div style="padding: 8px; text-align: center; color: #666; font-style: italic;">... y ${errors.length - 10} errores más</div>`;
            }
            
            resultHTML += `
                    </div>
                </div>
            `;
        } else {
            resultHTML += `
                <div style="text-align: center; padding: 30px; background: #e8f5e9; border-radius: 5px; margin: 20px 0;">
                    <div style="font-size: 48px; color: #4CAF50; margin-bottom: 10px;">✓</div>
                    <h4 style="color: #2e7d32; margin-bottom: 10px;">¡Validación exitosa!</h4>
                    <p style="color: #666;">No se encontraron errores estructurales en el Golden Record.</p>
                </div>
            `;
        }
        
        resultHTML += `
                    <div style="margin-top: 20px; text-align: right;">
                        <button id="downloadReportBtn" class="btn btn-success" style="background: var(--color-primary); color: var(--color-white); border: none; border-radius: 3px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer;">
                            Descargar Reporte CSV
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = resultHTML;
        document.querySelector('.form-container').insertAdjacentElement('afterend', container);
        
        // Event listener para el botón de descarga
        const downloadBtn = document.getElementById('downloadReportBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => downloadReport(results));
        }
    }

    async function downloadReport(results) {
        try {
            const validationId = results.validation_id;
            
            if (!validationId) {
                throw new Error('No se encontró ID de validación para descargar');
            }
            
            const response = await fetch(`/api/v1/structure/download-csv/${validationId}`, {
                method: 'GET',
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error descargando reporte');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `validation_report_${results.instance_id}_${results.version}_${results.validation_id}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('Reporte descargado exitosamente', 'success');
            
        } catch (error) {
            console.error('Error downloading report:', error);
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    // UI Utilities
    function showToast(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.cssText = `
            background: ${type === 'success' ? '#4CAF50' : '#f44336'};
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 14px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        `;
        // Agregar estilos de animación
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(container);
        return container;
    }

    function showLoader(show = true, message = 'Procesando...') {
        let loader = document.querySelector('.loader');
        
        if (show) {
            if (!loader) {
                loader = document.createElement('div');
                loader.className = 'loader';
                loader.innerHTML = `
                    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; display: flex; align-items: center; justify-content: center;">
                        <div style="background: white; padding: 30px; border-radius: 5px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                            <div style="width: 40px; height: 40px; border: 3px solid #f3f3f3; border-top: 3px solid var(--color-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px;"></div>
                            <p style="margin: 0; color: #333; font-size: 14px;">${message}</p>
                        </div>
                    </div>
                `;
                // Agregar animación de spin si no existe
                if (!document.querySelector('#spin-animation')) {
                    const spinStyle = document.createElement('style');
                    spinStyle.id = 'spin-animation';
                    spinStyle.textContent = `
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    `;
                    document.head.appendChild(spinStyle);
                }
                document.body.appendChild(loader);
            }
        } else {
            if (loader) {
                loader.remove();
            }
        }
    }

    function clearResults() {
        const existingResults = document.querySelector('.validation-results-container');
        if (existingResults) {
            existingResults.remove();
        }
    }

    // Asegurar que el botón de validar tenga color verde
    if (loadBtn) {
        loadBtn.style.cssText = `
            background: var(--color-primary);
            color: var(--color-white);
            border: none;
            border-radius: 3px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        `;
        
        loadBtn.addEventListener('mouseenter', function() {
            this.style.background = 'var(--color-primary-dark)';
        });
        
        loadBtn.addEventListener('mouseleave', function() {
            this.style.background = 'var(--color-primary)';
        });
    }
})();