/* Modal informativo de registros desactivados por el dueño del sistema.
   La card bloqueada lleva data-bloqueo-dueno="1" + data-tipo / data-dueno /
   data-fecha; cada lista JS llama a abrirModalBloqueoDueno(card) en lugar de
   abrir su modal de detalle normal. La imagen y descripción solo se muestran
   para Producto / Categoría (los usuarios se ven igual que antes). */
(function () {
    'use strict';

    function escapeHtml(texto) {
        var d = document.createElement('div');
        d.textContent = texto;
        return d.innerHTML;
    }

    function abrirModalBloqueoDueno(fuente) {
        var modal = document.getElementById('modalBloqueoDueno');
        if (!modal) return;
        var nombre = modal.querySelector('#md-bloqueo-nombre');
        var tipo = modal.querySelector('#md-bloqueo-tipo');
        var dueno = modal.querySelector('#md-bloqueo-dueno');
        var fecha = modal.querySelector('#md-bloqueo-fecha');
        var imagenWrap = modal.querySelector('#md-bloqueo-imagen-wrap');
        var descripcion = modal.querySelector('#md-bloqueo-descripcion');

        var tipoRegistro = fuente.getAttribute('data-tipo') || 'Registro';
        if (nombre) nombre.textContent = fuente.getAttribute('data-nombre') || '—';
        if (tipo) tipo.textContent = tipoRegistro;
        if (dueno) dueno.textContent = fuente.getAttribute('data-dueno') || '—';
        if (fecha) fecha.textContent = fuente.getAttribute('data-fecha') || '—';

        if (imagenWrap && descripcion) {
            if (tipoRegistro === 'Producto' || tipoRegistro === 'Categoría') {
                pintarDetalle(fuente, tipoRegistro, imagenWrap, descripcion);
            } else {
                imagenWrap.style.display = 'none';
                descripcion.style.display = 'none';
            }
        }

        if (window.jQuery && jQuery.fn.modal) {
            jQuery('#modalBloqueoDueno').modal('show');
        }
    }

    function pintarDetalle(fuente, tipoRegistro, imagenWrap, descripcion) {
        var imagen = fuente.getAttribute('data-imagen');
        var color = fuente.getAttribute('data-categoria-color') || fuente.getAttribute('data-color') || '#3b82f6';
        var icono = fuente.getAttribute('data-icono') || (tipoRegistro === 'Producto' ? 'fa-utensils' : 'fa-tag');
        var nombre = fuente.getAttribute('data-nombre') || '';

        if (imagen) {
            imagenWrap.innerHTML = '<img src="' + imagen + '" alt="' + escapeHtml(nombre) +
                '" class="img-fluid rounded shadow-sm" style="max-height:220px; object-fit:cover;">';
        } else {
            imagenWrap.innerHTML = '<div class="d-inline-flex align-items-center justify-content-center rounded shadow-sm" ' +
                'style="width:120px; height:120px; background:' + color + '22; color:' + color + ';">' +
                '<i class="fas ' + icono + ' fa-3x"></i></div>';
        }
        imagenWrap.style.display = 'block';

        descripcion.textContent = fuente.getAttribute('data-descripcion') || 'Sin descripción.';
        descripcion.style.display = 'block';
    }

    window.abrirModalBloqueoDueno = abrirModalBloqueoDueno;
})();
