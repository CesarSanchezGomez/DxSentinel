document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // Elementos del DOM
    const uploadForm = document.getElementById('uploadForm');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');
    const countryModal = document.getElementById('countryModal');
    const openModalBtn = document.getElementById('openCountryModal');
    const closeModalBtn = document.getElementById('closeCountryModal');
    const cancelModalBtn = document.getElementById('cancelCountrySelection');
    const confirmModalBtn = document.getElementById('confirmCountrySelection');
    const countryCheckboxesDiv = document.getElementById('countryCheckboxes');
    const selectAllBtn = document.getElementById('selectAllCountries');
    const deselectAllBtn = document.getElementById('deselectAllCountries');
    const selectedCountLabel = document.getElementById('selectedCountriesCount');
    const selectedPreview = document.getElementById('selectedCountriesPreview');
    const countrySearch = document.getElementById('countrySearch');

    // Variables de estado
    let csfFileId = null;
    let availableCountries = [];
    let selectedCountries = ['USA'];
    let filteredCountries = [];

    // Validación inicial
    if (!uploadForm) {
        console.error('No se encontró el formulario uploadForm');
        return;
    }

    // Validadores de XML
    const XML_VALIDATORS = {
        sdm: (content) => content.includes('<succession-data-model'),
        csf_sdm: (content) => 
            content.includes('<country-specific-fields') &&
            content.includes('<format-group')
    };

    // ========== FUNCIONES DE UTILIDAD ==========
    function handleAuthError(response) {
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/auth/login';
            return true;
        }
        return false;
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
        } else if (loader) {
            loader.remove();
        }
    }

    function setStatus(message, type = 'info') {
        statusDiv.style.display = 'block';
        statusDiv.className = `toast ${type}`;
        statusDiv.style.marginBottom = 'var(--spacing-md)';
        statusDiv.innerHTML = message;
    }

    // ========== FUNCIONES DEL MODAL ==========
    function openModal() {
        countryModal.classList.add('active');
        document.body.style.overflow = 'hidden';
        setTimeout(() => countrySearch.focus(), 100);
    }

    function closeModal() {
        countryModal.classList.remove('active');
        document.body.style.overflow = '';
        countrySearch.value = '';
        filterCountries('');
    }

    function updateSelectedCount() {
        const checkboxes = countryCheckboxesDiv.querySelectorAll('input[type="checkbox"]:not([style*="display: none"])');
        const allCheckboxes = countryCheckboxesDiv.querySelectorAll('input[type="checkbox"]');
        const selectedCount = Array.from(allCheckboxes).filter(cb => cb.checked).length;
        selectedCountLabel.textContent = `${selectedCount} seleccionados`;
    }

    function updatePreview() {
        if (selectedCountries.length === 0) {
            selectedPreview.textContent = 'Ningún país seleccionado';
            selectedPreview.style.color = 'var(--color-gray-dark)';
        } else {
            const preview = selectedCountries.length <= 3
                ? selectedCountries.join(', ')
                : `${selectedCountries.slice(0, 3).join(', ')} +${selectedCountries.length - 3} más`;

            selectedPreview.textContent = `${selectedCountries.length} seleccionados: ${preview}`;
            selectedPreview.style.color = 'var(--color-success)';
        }
    }

    function getSelectedCountriesFromModal() {
        const checkboxes = countryCheckboxesDiv.querySelectorAll('input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }

    function filterCountries(searchTerm) {
        const term = searchTerm.toLowerCase().trim();
        const items = countryCheckboxesDiv.querySelectorAll('.checkbox-item');

        items.forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            const countryCode = checkbox.value.toLowerCase();
            item.style.display = countryCode.includes(term) ? 'flex' : 'none';
        });

        updateSelectedCount();
    }

    function populateCountryCheckboxes(countries) {
        countryCheckboxesDiv.innerHTML = '';
        availableCountries = countries;
        filteredCountries = countries;

        countries.forEach((country) => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'checkbox-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `country_${country}`;
            checkbox.value = country;
            checkbox.checked = selectedCountries.includes(country);
            checkbox.addEventListener('change', updateSelectedCount);

            const label = document.createElement('label');
            label.htmlFor = `country_${country}`;
            label.textContent = country;

            itemDiv.addEventListener('click', function(e) {
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                    updateSelectedCount();
                }
            });

            itemDiv.appendChild(checkbox);
            itemDiv.appendChild(label);
            countryCheckboxesDiv.appendChild(itemDiv);
        });

        updateSelectedCount();
    }

    function resetCountrySelection() {
        availableCountries = [];
        selectedCountries = ['USA'];
        csfFileId = null;
        countryCheckboxesDiv.innerHTML = '';
        openModalBtn.disabled = true;
        selectedPreview.textContent = 'USA (default)';
        selectedPreview.style.color = 'var(--color-gray-darker)';

        const helper = document.getElementById('countryCodeHelper');
        if (helper) {
            helper.textContent = 'Se activará al subir CSF';
            helper.style.color = 'var(--color-gray-dark)';
        }
    }

    // ========== FUNCIONES DE VALIDACIÓN ==========
    async function validateXMLFile(file, expectedType) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = function(e) {
                const content = e.target.result;
                const validator = XML_VALIDATORS[expectedType];

                if (!validator) {
                    reject(new Error('Tipo de validación desconocido'));
                    return;
                }

                if (!validator(content)) {
                    const errorMessages = {
                        sdm: 'El archivo principal debe ser un Succession Data Model válido',
                        csf_sdm: 'El archivo CSF debe ser un CSF Succession Data Model válido'
                    };
                    reject(new Error(errorMessages[expectedType]));
                    return;
                }

                resolve(true);
            };

            reader.onerror = () => reject(new Error('Error al leer el archivo'));
            reader.readAsText(file);
        });
    }

    // ========== FUNCIONES DE API ==========
    async function uploadFile(file, fileType) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', fileType);

        const response = await fetch('/api/v1/upload/', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        if (handleAuthError(response)) throw new Error('Session expired');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }

        const result = await response.json();
        if (!result.success) throw new Error(result.message || 'Upload failed');

        return result.file_id;
    }

    async function extractCountriesFromCSF(fileId) {
        const response = await fetch(`/api/v1/upload/countries/${fileId}`, {
            method: 'GET',
            credentials: 'include'
        });

        if (handleAuthError(response)) throw new Error('Session expired');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al extraer países');
        }

        const result = await response.json();
        if (!result.success) throw new Error(result.message || 'Error al extraer países');

        return result.countries;
    }

    async function processFiles(mainFileId, csfFileId, languageCode, countryCodes) {
        // Obtener todos los valores del formulario
        const processId = document.getElementById('id').value;
        const cliente = document.getElementById('cliente').value;
        const consultor = document.getElementById('consultor').value;
        
        // Validar campos obligatorios
        if (!processId || !cliente || !consultor) {
            throw new Error('Por favor completa todos los campos obligatorios');
        }

        // Crear payload completo
        const payload = {
            id: processId,
            cliente: cliente,
            consultor: consultor,
            main_file_id: mainFileId,
            csf_file_id: csfFileId || null,
            language_code: languageCode,
            country_codes: countryCodes
        };

        console.log('Enviando payload:', payload);

        const response = await fetch('/api/v1/process/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            credentials: 'include'
        });

        if (handleAuthError(response)) throw new Error('Session expired');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Processing failed');
        }

        const result = await response.json();
        if (!result.success) throw new Error(result.message || 'Processing failed');

        return result;
    }

    // ========== FUNCIONES DE UI ==========
    function displayResults(processResult) {
        resultDiv.style.display = 'block';

        resultDiv.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3>Resultados</h3>
                </div>
                <div class="card-body">
                    <div class="selection-summary" style="margin-bottom: var(--spacing-md); align-items: center;">
                        <div class="summary-item">
                            <span style="color: var(--color-gray-dark); font-size: 13px;">Campos procesados:</span>
                            <span class="badge">${processResult.field_count}</span>
                        </div>
                        <div class="summary-item">
                            <span style="color: var(--color-gray-dark); font-size: 13px;">Tiempo:</span>
                            <span class="badge">${processResult.processing_time.toFixed(2)}s</span>
                        </div>
                    </div>
                    <div class="card-actions" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-sm);">
                        <a href="/api/v1/process/download/${processResult.output_file}" 
                           class="btn btn-primary" 
                           download="${processResult.output_file}">
                            CSV
                        </a>
                        <a href="/api/v1/process/download/${processResult.metadata_file}" 
                           class="btn btn-secondary" 
                           download="${processResult.metadata_file}">
                            Metadata
                        </a>
                    </div>
                </div>
            </div>
        `;

        showToast('Archivos procesados exitosamente');
    }

    // ========== EVENT LISTENERS ==========
    countrySearch.addEventListener('input', function(e) {
        filterCountries(e.target.value);
    });

    openModalBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    cancelModalBtn.addEventListener('click', closeModal);

    confirmModalBtn.addEventListener('click', function() {
        selectedCountries = getSelectedCountriesFromModal();
        updatePreview();
        closeModal();

        if (selectedCountries.length > 0) {
            showToast(`${selectedCountries.length} ${selectedCountries.length === 1 ? 'país seleccionado' : 'países seleccionados'}`, 'success');
        }
    });

    selectAllBtn.addEventListener('click', function() {
        const visibleCheckboxes = countryCheckboxesDiv.querySelectorAll('input[type="checkbox"]:not([style*="display: none"])');
        visibleCheckboxes.forEach(cb => cb.checked = true);
        updateSelectedCount();
    });

    deselectAllBtn.addEventListener('click', function() {
        const visibleCheckboxes = countryCheckboxesDiv.querySelectorAll('input[type="checkbox"]:not([style*="display: none"])');
        visibleCheckboxes.forEach(cb => cb.checked = false);
        updateSelectedCount();
    });

    countryModal.addEventListener('click', function(e) {
        if (e.target === countryModal) {
            closeModal();
        }
    });

    // Eventos de archivos
    document.getElementById('mainFile').addEventListener('change', async function(e) {
        const file = e.target.files[0];
        const fileNameDisplay = document.getElementById('mainFileName');

        if (!file) {
            fileNameDisplay.textContent = 'Ningún archivo seleccionado';
            return;
        }

        fileNameDisplay.textContent = `Validando ${file.name}...`;

        try {
            await validateXMLFile(file, 'sdm');
            fileNameDisplay.textContent = file.name;
            fileNameDisplay.style.color = 'var(--color-success)';
        } catch (error) {
            fileNameDisplay.textContent = error.message;
            fileNameDisplay.style.color = 'var(--color-error)';
            e.target.value = '';
            showToast(error.message, 'error');
        }
    });

    document.getElementById('csfFile').addEventListener('change', async function(e) {
        const file = e.target.files[0];
        const fileNameDisplay = document.getElementById('csfFileName');

        if (!file) {
            fileNameDisplay.textContent = 'Ningún archivo seleccionado';
            resetCountrySelection();
            return;
        }

        fileNameDisplay.textContent = `Validando ${file.name}...`;

        try {
            await validateXMLFile(file, 'csf_sdm');
            fileNameDisplay.textContent = file.name;
            fileNameDisplay.style.color = 'var(--color-success)';

            showLoader(true, 'Extrayendo países del CSF...');
            csfFileId = await uploadFile(file, 'csf_sdm');

            const countries = await extractCountriesFromCSF(csfFileId);
            showLoader(false);

            openModalBtn.disabled = false;

            if (!countries.includes('USA')) {
                selectedCountries = [];
            }

            populateCountryCheckboxes(countries);
            updatePreview();

            const helper = document.getElementById('countryCodeHelper');
            if (helper) {
                helper.textContent = `${countries.length} ${countries.length === 1 ? 'país encontrado' : 'países encontrados'}`;
                helper.style.color = 'var(--color-success)';
            }

            showToast(`${countries.length} ${countries.length === 1 ? 'país encontrado' : 'países encontrados'} en el CSF`, 'success');

        } catch (error) {
            fileNameDisplay.textContent = error.message;
            fileNameDisplay.style.color = 'var(--color-error)';
            e.target.value = '';
            showLoader(false);
            resetCountrySelection();
            showToast(error.message, 'error');
        }
    });

    // Evento principal del formulario
    uploadForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const submitBtn = document.querySelector('button[type="submit"]');
        const mainFile = document.getElementById('mainFile').files[0];
        const csfFile = document.getElementById('csfFile').files[0];
        const languageCode = document.getElementById('languageCode').value;

        // Validaciones iniciales
        if (!mainFile) {
            showToast('Selecciona el archivo principal', 'error');
            return;
        }

        if (csfFile && selectedCountries.length === 0) {
            showToast('Selecciona al menos un país del CSF', 'error');
            return;
        }

        // Deshabilitar botón de submit
        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Procesando...';

        try {
            // Subir archivo principal
            showLoader(true, 'Subiendo archivo principal...');
            const mainFileId = await uploadFile(mainFile, 'sdm');

            // Procesar archivos
            showLoader(true, 'Procesando archivos...');
            const processResult = await processFiles(
                mainFileId,
                csfFileId,
                languageCode,
                selectedCountries
            );

            showLoader(false);
            displayResults(processResult);

        } catch (error) {
            console.error(error);
            showLoader(false);
            setStatus(`Error: ${error.message}`, 'error');
            showToast(error.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });

    // Inicialización
    updatePreview();
    console.log('upload.js cargado correctamente');
});