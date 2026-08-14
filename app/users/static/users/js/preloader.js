(function () {
    'use strict';

    function hidePreloader() {
        var preloader = document.getElementById('nexpos-preloader');
        if (preloader) {
            preloader.classList.add('preloader-hidden');
        }
    }

    var safetyTimer = null;

    function showPreloader() {
        var preloader = document.getElementById('nexpos-preloader');
        if (preloader) {
            preloader.classList.remove('preloader-hidden');
        }
        // Red de seguridad: si no hay navegación real, el overlay se oculta solo.
        clearTimeout(safetyTimer);
        safetyTimer = setTimeout(hidePreloader, 5000);
    }

    // Al estar listo el DOM
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(hidePreloader, 100);
    } else {
        window.addEventListener('DOMContentLoaded', function () {
            setTimeout(hidePreloader, 100);
        });
    }

    // Fallback de seguridad por si algún recurso demora
    setTimeout(hidePreloader, 2000);

    // Muestra la pantalla de carga al navegar o enviar formularios.
    // La decisión se posterga (setTimeout 0) para que corran primero los
    // demás listeners del mismo evento (main.js/validacion.js/otros): si
    // alguno hace preventDefault (ej. popup de confirmación, form inválido,
    // rechazo de categoría protegida), el preloader NO debe mostrarse.
    document.addEventListener('click', function (e) {
        var link = e.target.closest('a');
        if (!link) return;
        var href = link.getAttribute('href');
        var target = link.getAttribute('target');

        if (href && !href.startsWith('#') && !href.startsWith('javascript:') && target !== '_blank' && !e.ctrlKey && !e.metaKey) {
            setTimeout(function () {
                if (!e.defaultPrevented) showPreloader();
            }, 0);
        }
    });

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form || form.getAttribute('target')) return;
        setTimeout(function () {
            if (!e.defaultPrevented) showPreloader();
        }, 0);
    });

    // Restaurar si el navegador usa bfcache
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            hidePreloader();
        }
    });
})();
