(function () {
    'use strict';

    const instanceIdInput = document.getElementById('instanceId');
    const lastVersionCheck = document.getElementById('lastVersionCheck');
    const versionSelect = document.getElementById('versionSelect');
    const versionGroup = document.getElementById('versionGroup');
    const previewSection = document.getElementById('previewSection');
    const searchBtn = document.getElementById('searchBtn');
    const loadBtn = document.getElementById('loadBtn');
    const goldenRecordFile = document.getElementById('goldenRecordFile');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');
    
    // Preview elements
    const previewId = document.getElementById('previewId');
    const previewCliente = document.getElementById('previewCliente');
    const previewConsultor = document.getElementById('previewConsultor');
    const previewFecha = document.getElementById('previewFecha');
    const previewVersion = document.getElementById('previewVersion');
    const previewPath = document.getElementById('previewPath');
    const jsonViewer = document.getElementById('jsonViewer');

    // Toggle version selection
    lastVersionCheck.addEventListener('change', function() {
        if (this.checked) {
            versionGroup.style.display = 'none';
            versionSelect.disabled = true;
        } else {
            versionGroup.style.display = 'block';
            versionSelect.disabled = false;
            if (instanceIdInput.value.trim()) {
                loadVersions(instanceIdInput.value.trim());
            }
        }
    });

    // File name display
    goldenRecordFile.addEventListener('change', function(e) {
        const fileName = e.target.files[0]?.name || 'Ningún archivo seleccionado';
        document.getElementById('goldenRecordFileName').textContent = fileName;
    });

    // Search metadata
    searchBtn.addEventListener('click', async function() {
        const instanceId = instanceIdInput.value.trim();
        
        if (!instanceId) {
            showToast('Por favor ingresa un ID de instancia', 'error');
            return;
        }

        searchBtn.disabled = true;
        searchBtn.textContent = 'Buscando...';
        setStatus('Buscando metadata...', 'info');
        previewSection.style.display = 'none';
        loadBtn.style.display = 'none';

        try {
            const useLastVersion = lastVersionCheck.checked;
            const version = useLastVersion ? 'latest' : versionSelect.value;
            
            const response = await fetch(`/api/v1/structure/metadata/${instanceId}?version=${version}`, {
                method: 'GET',
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error al buscar metadata');
            }

            const metadata = await response.json();
            
            // Update preview
            updatePreview(metadata);
            previewSection.style.display = 'block';
            loadBtn.style.display = 'block';
            
            setStatus('✓ Metadata encontrada', 'success');
            showToast('Metadata cargada exitosamente', 'success');

        } catch (error) {
            console.error('Error:', error);
            setStatus(`✗ Error: ${error.message}`, 'error');
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            searchBtn.disabled = false;
            searchBtn.textContent = 'Buscar Metadata';
        }
    });

    // Load golden record
    loadBtn.addEventListener('click', async function() {
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

        loadBtn.disabled = true;
        loadBtn.textContent = 'Cargando...';
        setStatus('Procesando Golden Record...', 'info');

        const formData = new FormData();
        formData.append('golden_file', file);
        
        const useLastVersion = lastVersionCheck.checked;
        const version = useLastVersion ? 'latest' : versionSelect.value;
        formData.append('metadata_id', instanceId);
        formData.append('version', version);

        try {
            const response = await fetch('/api/v1/structure/load-golden-record', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error al procesar Golden Record');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `golden_record_${instanceId}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            setStatus('✓ Golden Record procesado exitosamente', 'success');
            setResult(`
                <p style="color: var(--color-success); font-weight: 600;">
                    ✓ Golden Record procesado y descargado
                </p>
                <p style="margin-top: 10px;">
                    <strong>Archivo:</strong> ${file.name}<br>
                    <strong>Instancia:</strong> ${instanceId}<br>
                    <strong>Versión:</strong> ${version === 'latest' ? 'Última' : version}
                </p>
            `);

            showToast('Golden Record procesado exitosamente', 'success');

        } catch (error) {
            console.error('Error:', error);
            setStatus(`✗ Error: ${error.message}`, 'error');
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            loadBtn.disabled = false;
            loadBtn.textContent = 'Cargar Golden Record';
        }
    });

    // Helper functions
    async function loadVersions(instanceId) {
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
            
        } catch (error) {
            console.error('Error loading versions:', error);
            versionSelect.innerHTML = '<option value="">Error cargando versiones</option>';
        }
    }

    function updatePreview(metadata) {
        // Basic info
        previewId.textContent = metadata.id || '-';
        previewCliente.textContent = metadata.cliente || '-';
        previewConsultor.textContent = metadata.consultor || '-';
        previewFecha.textContent = metadata.fecha ? new Date(metadata.fecha).toLocaleString() : '-';
        previewVersion.textContent = metadata.version || '-';
        previewPath.textContent = metadata.path || '-';
        
        // JSON viewer
        jsonViewer.textContent = JSON.stringify(metadata.raw, null, 2);
    }

    function showToast(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    function setStatus(message, type = 'info') {
        statusDiv.style.display = 'block';
        statusDiv.className = `log-section ${type}`;
        statusDiv.innerHTML = `<h4>Estado</h4><div class="log-output">${message}</div>`;
    }

    function setResult(html) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'log-section';
        resultDiv.innerHTML = `<h4>Resultado</h4><div class="log-output">${html}</div>`;
    }
})();