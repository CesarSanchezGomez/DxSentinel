// frontend/static/js/auth-login.js
(function() {
    'use strict';

    // Configuración de Supabase (inyectada desde el template)
    const SUPABASE_URL = window.SUPABASE_CONFIG?.url;
    const SUPABASE_KEY = window.SUPABASE_CONFIG?.key;

    if (!SUPABASE_URL || !SUPABASE_KEY) {
        console.error('Configuración de Supabase no disponible');
        return;
    }

    const { createClient } = supabase;
    const supabaseClient = createClient(SUPABASE_URL, SUPABASE_KEY);

    // Mostrar errores de la URL
    function showUrlError() {
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');

        if (!error) return;

        const errorContainer = document.getElementById('error-container');
        const errorMessages = {
            'domain_not_allowed': 'Solo se permite acceso a usuarios de @dxgrow.com',
            'access_denied': 'Acceso denegado. Por favor, intente nuevamente.'
        };

        const message = errorMessages[error] || `Error: ${error}`;
        errorContainer.innerHTML = `<div class="error-message">${message}</div>`;
    }

    // Login con Google
    async function loginWithGoogle() {
        try {
            const { error } = await supabaseClient.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: window.location.origin + '/auth/callback',
                    queryParams: {
                        access_type: 'offline',
                        prompt: 'consent',
                        hd: 'dxgrow.com'
                    }
                }
            });

            if (error) {
                document.getElementById('error-container').innerHTML =
                    `<div class="error-message">${error.message}</div>`;
            }
        } catch (err) {
            console.error('Error en login:', err);
            document.getElementById('error-container').innerHTML =
                `<div class="error-message">Error inesperado. Intente nuevamente.</div>`;
        }
    }

    // Exponer función global para el botón
    window.loginWithGoogle = loginWithGoogle;

    // Inicializar
    showUrlError();
})();