(function () {
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

    async function uploadFile(file, description) {
        console.log(`Uploading ${description}:`, file.name);

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/v1/upload/', {
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

        const response = await fetch('/api/v1/process/', {
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

        let layoutsHtml = '';
        if (processResult.layout_files && processResult.layout_files.length > 0) {
            layoutsHtml = '<h4>Individual Layouts:</h4><ul>';
            processResult.layout_files.forEach(layoutFile => {
                const fileName = layoutFile.split('/').pop();
                layoutsHtml += `
                    <li>
                        <a href="/api/v1/process/download/${fileName}" download>
                            ${fileName}
                        </a>
                    </li>
                `;
            });
            layoutsHtml += '</ul>';
        }

        resultDiv.innerHTML = `
            <h3>Results:</h3>
            <p><strong>Fields:</strong> ${processResult.field_count}</p>
            <p><strong>Time:</strong> ${processResult.processing_time.toFixed(2)}s</p>
            <h4>Main Files:</h4>
            <a href="/api/v1/process/download/${processResult.output_file}" download>
                Download Golden Record CSV
            </a>
            <br>
            <a href="/api/v1/process/download/${processResult.metadata_file}" download>
                Download Metadata JSON
            </a>
            ${layoutsHtml}
        `;
    }

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        resultDiv.innerHTML = '';

        const mainFile = document.getElementById('mainFile').files[0];
        const csfFile = document.getElementById('csfFile').files[0];
        const languageCode = document.getElementById('languageCode').value;
        const countryCode = document.getElementById('countryCode').value.trim(); // ADD .trim()

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
                countryCode || null  // CHANGE: Ensure empty string becomes null
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