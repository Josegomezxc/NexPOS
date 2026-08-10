(function () {
    'use strict';

    function hidePreloader() {
        var preloader = document.getElementById('nexpos-preloader');
        if (preloader) {
            preloader.classList.add('preloader-hidden');
        }
    }

    function showPreloader() {
        var preloader = document.getElementById('nexpos-preloader');
        if (preloader) {
            preloader.classList.remove('preloader-hidden');
        }
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

    // Muestra la pantalla de carga al navegar o enviar formularios
    document.addEventListener('click', function (e) {
        var link = e.target.closest('a');
        if (!link) return;
        var href = link.getAttribute('href');
        var target = link.getAttribute('target');
        
        if (href && !href.startsWith('#') && !href.startsWith('javascript:') && target !== '_blank' && !e.ctrlKey && !e.metaKey) {
            showPreloader();
        }
    });

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (form && !form.getAttribute('target')) {
            showPreloader();
        }
    });

    // Restaurar si el navegador usa bfcache
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            hidePreloader();
        }
    });
})();
