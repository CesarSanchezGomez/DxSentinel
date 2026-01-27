document.getElementById('splitForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');

    const goldenFile = document.getElementById('goldenFile').files[0];
    const metadataFile = document.getElementById('metadataFile').files[0];

    if (!goldenFile || !metadataFile) {
        statusDiv.style.display = 'block';
        statusDiv.style.color = 'red';
        statusDiv.textContent = 'Please select both files';
        return;
    }

    submitBtn.disabled = true;
    statusDiv.style.display = 'block';
    statusDiv.style.color = 'blue';
    statusDiv.textContent = 'Processing files...';
    resultDiv.style.display = 'none';

    const formData = new FormData();
    formData.append('golden_file', goldenFile);
    formData.append('metadata_file', metadataFile);

    try {
        // URL CORREGIDA
        const response = await fetch('/api/v1/split/golden-record', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error processing files');
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

        statusDiv.textContent = 'Success!';
        statusDiv.style.color = 'green';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<p>✓ Layouts ZIP downloaded successfully!</p>';

    } catch (error) {
        console.error('Error:', error);
        statusDiv.textContent = `Error: ${error.message}`;
        statusDiv.style.color = 'red';
    } finally {
        submitBtn.disabled = false;
    }
});