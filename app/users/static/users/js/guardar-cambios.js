/* =====================================================
   guardar-cambios.js — Deshabilitar "Guardar" sin cambios
   Solo actúa sobre formularios con data-guardar-cambios.

   - Toma un snapshot inicial de los campos (name=value).
   - En cada input/change compara contra el snapshot: si no
     hay diferencias, el/los botón(es) [type="submit"] quedan
     deshabilitados (no se puede guardar algo que no cambió).
   - El submit por tecla Enter también se bloquea si no hay
     cambios (el botón deshabilitado no cubre ese caso).
   - Los campos de archivo (type=file) no son serializables:
     seleccionar un archivo cuenta como cambio.
   - Compatible con validacion.js (form con cambios pero
     inválido sigue bloqueado por la validación) y con el
     preloader (preventDefault es síncrono, el overlay no
     aparece sobre un submit bloqueado).
============================================================= */
(function () {
  'use strict';

  function serializar(form) {
    var datos = new FormData(form);
    var partes = [];
    for (var entrada of datos) {
      partes.push(entrada[0] + '=' + entrada[1]);
    }
    return partes.join('&');
  }

  function hayArchivoNuevo(form) {
    var archivos = form.querySelectorAll('input[type="file"]');
    for (var i = 0; i < archivos.length; i++) {
      if (archivos[i].files && archivos[i].files.length > 0) return true;
    }
    return false;
  }

  function armarForm(form) {
    var inicial = serializar(form);
    var botones = form.querySelectorAll('button[type="submit"]');

    function tienenCambios() {
      return serializar(form) !== inicial || hayArchivoNuevo(form);
    }

    function sincronizar() {
      var activo = tienenCambios();
      botones.forEach(function (btn) {
        btn.disabled = !activo;
        if (!activo) btn.setAttribute('title', 'No hay cambios para guardar');
        else btn.removeAttribute('title');
      });
    }

    form.addEventListener('input', sincronizar);
    form.addEventListener('change', sincronizar);

    form.addEventListener('submit', function (e) {
      if (!tienenCambios()) e.preventDefault();
    });

    sincronizar();
  }

  function iniciar() {
    document.querySelectorAll('form[data-guardar-cambios]').forEach(armarForm);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();