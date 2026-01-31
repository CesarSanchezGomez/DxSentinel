// frontend/static/js/auth-callback.js
(function() {
    'use strict';

    const ALLOWED_DOMAIN = window.ALLOWED_DOMAIN || 'dxgrow.com';

    function showError(message) {
        const spinner = document.getElementById('spinner');
        const errorMessage = document.getElementById('error-message');
        const errorText = document.getElementById('error-text');

        if (spinner) spinner.style.display = 'none';
        if (errorText) errorText.textContent = message;
        if (errorMessage) errorMessage.style.display = 'block';
    }

    async function processCallback() {
        try {
            // 1. Obtener parámetros del hash
            const hashParams = new URLSearchParams(window.location.hash.substring(1));

            const accessToken = hashParams.get('access_token');
            const refreshToken = hashParams.get('refresh_token');
            const error = hashParams.get('error');
            const errorDescription = hashParams.get('error_description');

            // 2. Verificar errores de OAuth
            if (error) {
                showError(`Error de autenticación: ${errorDescription || error}`);
                return;
            }

            // 3. Verificar token
            if (!accessToken) {
                showError('No se recibió el token de acceso. Por favor, intenta nuevamente.');
                return;
            }

            // 4. Decodificar JWT para obtener email
            const payload = JSON.parse(atob(accessToken.split('.')[1]));
            const email = payload.email;

            // 5. Validación de dominio (frontend - UX feedback rápido)
            if (!email.endsWith(`@${ALLOWED_DOMAIN}`)) {
                showError(`Solo se permite acceso a usuarios de @${ALLOWED_DOMAIN}`);
                return;
            }

            // 6. Enviar tokens al backend para crear sesión
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/auth/session';

            const inputs = {
                access_token: accessToken,
                refresh_token: refreshToken,
                email: email
            };

            Object.entries(inputs).forEach(([name, value]) => {
                if (value) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = name;
                    input.value = value;
                    form.appendChild(input);
                }
            });

            document.body.appendChild(form);
            form.submit();

        } catch (err) {
            showError('Error inesperado al procesar la autenticación: ' + err.message);
            console.error('Error details:', err);
        }
    }

    // Ejecutar al cargar la página
    processCallback();
})();