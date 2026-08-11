/* =====================================================
   caja_index.js — modal de detalle de pedido en Caja.
===================================================== */
(function () {
  'use strict';

  const $modalEl = document.getElementById('cajaIndexModal');
  if (!$modalEl) return;

  const $numero = document.getElementById('caja-modal-numero');
  const $estado = document.getElementById('caja-modal-estado');
  const $total = document.getElementById('caja-modal-total');
  const $vendedor = document.getElementById('caja-modal-vendedor');
  const $fecha = document.getElementById('caja-modal-fecha');
  const $metodo = document.getElementById('caja-modal-metodo');
  const $itemsCount = document.getElementById('caja-modal-items-count');
  const $btnCobrar = document.getElementById('caja-modal-btn-cobrar');
  const $btnTicket = document.getElementById('caja-modal-btn-ticket');

  document.querySelectorAll('.caja-card').forEach(card => {
    card.addEventListener('click', (e) => {
      if (e.target.closest('a, button, form')) return;
      abrirModal(card);
    });
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        abrirModal(card);
      }
    });
  });

  function abrirModal(card) {
    const d = card.dataset;
    $numero.textContent = d.numero;
    $total.textContent = '$' + Number(d.total).toLocaleString('es-AR', { minimumFractionDigits: 2 });
    $vendedor.textContent = d.vendedor || 'Sistema';
    $fecha.textContent = d.fecha || '-';
    $metodo.textContent = d.metodoDisplay || 'Pendiente de cobro';
    $itemsCount.textContent = d.itemsCount + (d.itemsCount === '1' ? ' ítem' : ' ítems');

    if (d.estado === 'completado') {
      $estado.className = 'badge badge-success badge-pill';
      $estado.textContent = 'Cobrado';
      $btnCobrar.classList.add('d-none');
      $btnTicket.classList.remove('d-none');
      $btnTicket.href = d.ticketUrl;
    } else if (d.estado === 'pendiente') {
      $estado.className = 'badge badge-warning badge-pill';
      $estado.textContent = 'Pendiente';
      $btnCobrar.classList.remove('d-none');
      $btnCobrar.href = d.detalleUrl;
      $btnTicket.classList.add('d-none');
    } else {
      $estado.className = 'badge badge-danger badge-pill';
      $estado.textContent = 'Cancelado';
      $btnCobrar.classList.add('d-none');
      $btnTicket.classList.add('d-none');
    }

    if (typeof jQuery !== 'undefined') {
      jQuery('#cajaIndexModal').modal('show');
    } else {
      console.error('jQuery no está disponible — el modal no puede abrirse.');
    }
  }

  /* =====================================================
     Aviso por parámetro ?aviso= (pedido ya cobrado/cancelado).
     Muestra el popup y limpia la URL para que no reaparezca.
  ===================================================== */
  (function mostrarAviso() {
    const params = new URLSearchParams(window.location.search);
    const aviso = params.get('aviso');
    if (!aviso) return;

    const opciones = {
      cobrado: {
        titulo: 'Pedido ya cobrado',
        mensaje: 'Este pedido ya fue cobrado, la lista ya está actualizada.',
        boton: 'Entendido',
        clase: 'btn-primary',
      },
      cancelado: {
        titulo: 'Pedido cancelado',
        mensaje: 'Este pedido ya fue cancelado, la lista ya está actualizada.',
        boton: 'Entendido',
        clase: 'btn-warning',
      },
    }[aviso];
    if (opciones) window.mostrarConfirmacion(opciones);

    params.delete('aviso');
    const resto = params.toString();
    const nuevaUrl = window.location.pathname +
      (resto ? '?' + resto : '') + window.location.hash;
    window.history.replaceState({}, '', nuevaUrl);
  })();
})();
