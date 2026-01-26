document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');

    statusDiv.innerHTML = 'Uploading files...';

    const mainFile = document.getElementById('mainFile').files[0];
    const csfFile = document.getElementById('csfFile').files[0];
    const languageCode = document.getElementById('languageCode').value;
    const countryCode = document.getElementById('countryCode').value;

    try {
        const mainFormData = new FormData();
        mainFormData.append('file', mainFile);

        const mainResponse = await fetch('/api/v1/upload/', {
            method: 'POST',
            body: mainFormData
        });

        const mainResult = await mainResponse.json();

        if (!mainResult.success) {
            throw new Error('Main file upload failed');
        }

        let csfFileId = null;
        if (csfFile) {
            const csfFormData = new FormData();
            csfFormData.append('file', csfFile);

            const csfResponse = await fetch('/api/v1/upload/', {
                method: 'POST',
                body: csfFormData
            });

            const csfResult = await csfResponse.json();
            csfFileId = csfResult.file_id;
        }

        statusDiv.innerHTML = 'Processing...';

        const processResponse = await fetch('/api/v1/process/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                main_file_id: mainResult.file_id,
                csf_file_id: csfFileId,
                language_code: languageCode,
                country_code: countryCode || null
            })
        });

        const processResult = await processResponse.json();

        if (processResult.success) {
            statusDiv.innerHTML = 'Success!';
            resultDiv.innerHTML = `
                <h3>Results:</h3>
                <p>Fields: ${processResult.field_count}</p>
                <p>Time: ${processResult.processing_time.toFixed(2)}s</p>
                <a href="/api/v1/process/download/${processResult.output_file}" download>
                    Download CSV
                </a>
            `;
        } else {
            throw new Error(processResult.message);
        }

    } catch (error) {
        statusDiv.innerHTML = `Error: ${error.message}`;
    }
});