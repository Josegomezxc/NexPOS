/* =====================================================
   order_list.js — filtros en tiempo real y modal
   de detalle del pedido al hacer clic en una tarjeta.
===================================================== */
(function () {
  'use strict';

  // -------- Filtros en tiempo real --------
  const form = document.getElementById('orderFilterForm');
  if (form) {
    const qInput = document.getElementById('q-input');
    let timer;
    if (qInput) {
      qInput.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => form.submit(), 350);
      });
    }
    form.querySelectorAll('.filter-auto').forEach(el => {
      el.addEventListener('change', () => form.submit());
    });
  }

  // -------- Modal de detalle del pedido --------
  const $modalEl = document.getElementById('orderModal');
  if (!$modalEl) return;

  const $numero = document.getElementById('order-modal-numero');
  const $estado = document.getElementById('order-modal-estado');
  const $total = document.getElementById('order-modal-total');
  const $vendedor = document.getElementById('order-modal-vendedor');
  const $cliente = document.getElementById('order-modal-cliente');
  const $fecha = document.getElementById('order-modal-fecha');
  const $metodo = document.getElementById('order-modal-metodo');
  const $itemsCount = document.getElementById('order-modal-items-count');
  const $btnVer = document.getElementById('order-modal-btn-ver');
  const $btnTicket = document.getElementById('order-modal-btn-ticket');

  document.querySelectorAll('.order-card').forEach(card => {
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
    $cliente.textContent = d.cliente || 'Consumidor Final';
    $fecha.textContent = d.fecha || '-';
    $metodo.textContent = d.metodoDisplay || 'Sin registrar';
    $itemsCount.textContent = d.itemsCount + (d.itemsCount === '1' ? ' ítem' : ' ítems');

    if (d.estado === 'completado') {
      $estado.className = 'badge badge-success badge-pill';
      $estado.textContent = 'Completado';
    } else if (d.estado === 'pendiente') {
      $estado.className = 'badge badge-warning badge-pill';
      $estado.textContent = 'Pendiente';
    } else {
      $estado.className = 'badge badge-secondary badge-pill';
      $estado.textContent = 'Cancelado';
    }

    $btnVer.href = d.detailUrl;
    $btnTicket.href = d.ticketUrl;

    if (typeof jQuery !== 'undefined') {
      jQuery('#orderModal').modal('show');
    } else {
      console.error('jQuery no está disponible — el modal no puede abrirse.');
    }
  }
})();
