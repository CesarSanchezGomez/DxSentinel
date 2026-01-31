(function () {
    'use strict';

    const splitForm = document.getElementById('splitForm');
    const submitBtn = document.getElementById('submitBtn');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');

    function showToast(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
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
                    <div class="spinner"></div>
                    <p>${message}</p>
                `;
                document.body.appendChild(loader);
            }
        } else {
            if (loader) {
                loader.remove();
            }
        }
    }

    function setStatus(message, type = 'info') {
        statusDiv.style.display = 'block';
        statusDiv.className = `log-section ${type}`;
        statusDiv.innerHTML = `
            <h4>Estado</h4>
            <div class="log-output">${message}</div>
        `;
    }

    function setResult(html) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'log-section';
        resultDiv.innerHTML = `
            <h4>Resultado</h4>
            <div class="log-output">${html}</div>
        `;
    }

    splitForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const goldenFile = document.getElementById('goldenFile').files[0];
        const metadataFile = document.getElementById('metadataFile').files[0];

        if (!goldenFile || !metadataFile) {
            showToast('Por favor selecciona ambos archivos', 'error');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Procesando...';
        showLoader(true, 'Generando layouts...');

        setStatus('Subiendo archivos y procesando...', 'info');
        resultDiv.style.display = 'none';

        const formData = new FormData();
        formData.append('golden_file', goldenFile);
        formData.append('metadata_file', metadataFile);

        try {
            const response = await fetch('/api/v1/split/golden-record', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error procesando archivos');
            }

            // Descargar el ZIP
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'layouts.zip';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            setStatus('✓ Proceso completado exitosamente', 'success');
            setResult(`
                <p style="color: var(--color-success); font-weight: 600;">
                    ✓ Layouts ZIP descargado correctamente
                </p>
                <p style="margin-top: 10px;">
                    <strong>Archivos procesados:</strong><br>
                    • ${goldenFile.name}<br>
                    • ${metadataFile.name}
                </p>
            `);

            showToast('Layouts generados exitosamente', 'success');

        } catch (error) {
            console.error('Error:', error);
            setStatus(`✗ Error: ${error.message}`, 'error');
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            showLoader(false);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Generate Layouts';
        }
    });

    // Mostrar nombre de archivos seleccionados
    document.getElementById('goldenFile').addEventListener('change', function(e) {
        const fileName = e.target.files[0]?.name || 'Ningún archivo seleccionado';
        document.getElementById('goldenFileName').textContent = fileName;

        if (e.target.files[0]) {
            showToast(`Golden Record seleccionado: ${fileName}`, 'success');
        }
    });

    document.getElementById('metadataFile').addEventListener('change', function(e) {
        const fileName = e.target.files[0]?.name || 'Ningún archivo seleccionado';
        document.getElementById('metadataFileName').textContent = fileName;

        if (e.target.files[0]) {
            showToast(`Metadata seleccionado: ${fileName}`, 'success');
        }
    });
})();