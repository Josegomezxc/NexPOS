(function () {
    'use strict';

    var OJO = 'fa-eye';
    var OJO_TACHADO = 'fa-eye-slash';

    function alternar(boton) {
        if (!boton) return false;
        var selector = boton.getAttribute('data-toggle-password');
        var input = null;

        if (selector && selector.length > 0) {
            try {
                input = document.querySelector(selector);
            } catch (err) {
                console.warn('Selector de contraseña no válido:', selector);
            }
        }

        if (!input) {
            var wrap = boton.closest('.campo-wrap, .login-input-wrap, .form-group');
            if (wrap) {
                input = wrap.querySelector('input');
            }
        }

        if (!input) return false;

        var esTexto = (input.type === 'text');
        input.type = esTexto ? 'password' : 'text';
        var ahoraEsVisible = (input.type === 'text');

        var icono = boton.querySelector('i, .fa-eye, .fa-eye-slash');
        if (icono) {
            if (ahoraEsVisible) {
                icono.classList.remove(OJO);
                icono.classList.add(OJO_TACHADO);
            } else {
                icono.classList.remove(OJO_TACHADO);
                icono.classList.add(OJO);
            }
        }

        boton.setAttribute('aria-label', ahoraEsVisible ? 'Ocultar contraseña' : 'Mostrar contraseña');
        boton.title = ahoraEsVisible ? 'Ocultar contraseña' : 'Mostrar contraseña';
        return ahoraEsVisible;
    }

    document.addEventListener('click', function (e) {
        var boton = e.target.closest('[data-toggle-password]');
        if (!boton) return;
        e.preventDefault();
        e.stopPropagation();
        alternar(boton);
    });
})();
