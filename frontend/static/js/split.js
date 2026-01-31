(function () {
    'use strict';

    const splitForm = document.getElementById('splitForm');
    const submitBtn = document.getElementById('submitBtn');

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
            } else {
                loader.querySelector('p').textContent = message;
            }
        } else {
            if (loader) {
                loader.remove();
            }
        }
    }

    splitForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const goldenFile = document.getElementById('goldenFile').files[0];
        const metadataFile = document.getElementById('metadataFile').files[0];

        if (!goldenFile || !metadataFile) {
            showToast('Selecciona ambos archivos', 'error');
            return;
        }

        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Generando...';
        showLoader(true, 'Generando layouts...');

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

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'layouts.zip';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showToast('Layouts generados exitosamente', 'success');

        } catch (error) {
            console.error('Error:', error);
            showToast(error.message, 'error');
        } finally {
            showLoader(false);
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });

    document.getElementById('goldenFile').addEventListener('change', function (e) {
        const fileNameDisplay = document.getElementById('goldenFileName');

        if (!e.target.files[0]) {
            fileNameDisplay.textContent = 'Ningún archivo seleccionado';
            fileNameDisplay.style.color = '';
            return;
        }

        const fileName = e.target.files[0].name;
        fileNameDisplay.textContent = fileName;
        fileNameDisplay.style.color = 'var(--color-success)';
    });

    document.getElementById('metadataFile').addEventListener('change', function (e) {
        const fileNameDisplay = document.getElementById('metadataFileName');

        if (!e.target.files[0]) {
            fileNameDisplay.textContent = 'Ningún archivo seleccionado';
            fileNameDisplay.style.color = '';
            return;
        }

        const fileName = e.target.files[0].name;
        fileNameDisplay.textContent = fileName;
        fileNameDisplay.style.color = 'var(--color-success)';
    });
})();