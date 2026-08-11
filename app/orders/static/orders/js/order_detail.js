/* =====================================================
   order_detail.js — aviso por parámetro ?aviso=
   (intento de editar/cancelar un pedido ya cobrado/cancelado).
   Muestra el popup y limpia la URL para que no reaparezca.
===================================================== */
(function () {
  'use strict';

  const params = new URLSearchParams(window.location.search);
  const aviso = params.get('aviso');
  if (!aviso) return;

  const estado = window.ORDER_DETAIL_ESTADO || '';
  const estadoTexto = estado === 'completado'
    ? 'cobrado'
    : (estado === 'cancelado' ? 'cancelado' : '');

  let opciones = null;
  if (aviso.startsWith('editar_')) {
    opciones = {
      titulo: 'No se puede editar',
      mensaje: estadoTexto
        ? 'Este pedido ya fue ' + estadoTexto + ' y no se puede editar.'
        : 'Este pedido ya no está pendiente y no se puede editar.',
      boton: 'Entendido',
      clase: 'btn-primary',
    };
  } else if (aviso.startsWith('cancelar_')) {
    opciones = {
      titulo: 'No se puede cancelar',
      mensaje: estadoTexto
        ? 'Este pedido ya fue ' + estadoTexto + ' y no se puede cancelar.'
        : 'Este pedido ya no está pendiente y no se puede cancelar.',
      boton: 'Entendido',
      clase: 'btn-warning',
    };
  }
  if (opciones && typeof window.mostrarConfirmacion === 'function') {
    window.mostrarConfirmacion(opciones);
  }

  params.delete('aviso');
  const resto = params.toString();
  const nuevaUrl = window.location.pathname +
    (resto ? '?' + resto : '') + window.location.hash;
  window.history.replaceState({}, '', nuevaUrl);
})();
