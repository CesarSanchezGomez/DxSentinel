// frontend/static/js/upload.js
(function() {
    'use strict';

    const uploadForm = document.getElementById('uploadForm');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');

    function handleAuthError(response) {
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/auth/login';
            return true;
        }
        return false;
    }

    function setStatus(message, type = 'info') {
        const colors = {
            info: '#0066cc',
            success: 'green',
            error: 'red'
        };
        statusDiv.innerHTML = `<span style="color: ${colors[type]};">${message}</span>`;
    }

// frontend/static/js/upload.js
async function uploadFile(file, description) {
    console.log(`Uploading ${description}:`, file.name);

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/v1/upload/', {  // CAMBIO: Agregado trailing slash
        method: 'POST',
        body: formData,
        credentials: 'include'
    });

    if (handleAuthError(response)) {
        throw new Error('Session expired');
    }

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `${description} upload failed`);
    }

    const result = await response.json();

    if (!result.success) {
        throw new Error(result.message || `${description} upload failed`);
    }

    console.log(`${description} uploaded:`, result);
    return result.file_id;
}

async function processFiles(mainFileId, csfFileId, languageCode, countryCode) {
    console.log('Starting processing with:', {
        main_file_id: mainFileId,
        csf_file_id: csfFileId,
        language_code: languageCode,
        country_code: countryCode || null
    });

    const response = await fetch('/api/v1/process/', {  // CAMBIO: Agregado trailing slash
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            main_file_id: mainFileId,
            csf_file_id: csfFileId,
            language_code: languageCode,
            country_code: countryCode || null
        }),
        credentials: 'include'
    });

    if (handleAuthError(response)) {
        throw new Error('Session expired');
    }

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Processing failed');
    }

    const result = await response.json();

    if (!result.success) {
        throw new Error(result.message || 'Processing failed');
    }

    console.log('Process result:', result);
    return result;
}

    function displayResults(processResult) {
        setStatus('Success!', 'success');
        resultDiv.innerHTML = `
            <h3>Results:</h3>
            <p><strong>Fields:</strong> ${processResult.field_count}</p>
            <p><strong>Time:</strong> ${processResult.processing_time.toFixed(2)}s</p>
            <a href="/api/v1/process/download/${processResult.output_file}" download>
                Download Golden Record CSV
            </a>
            <br>
            <a href="/api/v1/process/download/${processResult.metadata_file}" download>
                Download Metadata JSON
            </a>
        `;
    }

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        resultDiv.innerHTML = '';

        const mainFile = document.getElementById('mainFile').files[0];
        const csfFile = document.getElementById('csfFile').files[0];
        const languageCode = document.getElementById('languageCode').value;
        const countryCode = document.getElementById('countryCode').value;

        try {
            setStatus('Uploading main file...');
            const mainFileId = await uploadFile(mainFile, 'Main file');

            let csfFileId = null;
            if (csfFile) {
                setStatus('Uploading CSF file...');
                csfFileId = await uploadFile(csfFile, 'CSF file');
            }

            setStatus('Processing files...');
            const processResult = await processFiles(
                mainFileId,
                csfFileId,
                languageCode,
                countryCode
            );

            displayResults(processResult);

        } catch (error) {
            console.error('Error:', error);

            if (error.message !== 'Session expired') {
                setStatus(`Error: ${error.message}`, 'error');
                resultDiv.innerHTML = '';
            }
        }
    });
})();