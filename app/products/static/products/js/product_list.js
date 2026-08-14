/* =====================================================
   product_list.js
   - Filtros en tiempo real (búsqueda + selects)
   - Modal de detalle al hacer click en una tarjeta de producto
===================================================== */
(function () {
  'use strict';

  // -------- Pintar colores de categoría desde data-color --------
  document.querySelectorAll('.product-cat-badge[data-color], .category-badge[data-color]').forEach(el => {
    el.style.backgroundColor = el.dataset.color;
    el.style.color = '#fff';
  });
  document.querySelectorAll('.product-thumb-empty[data-color], .product-card-placeholder[data-color]').forEach(el => {
    const c = el.dataset.color;
    el.style.backgroundColor = c + '22';
    el.style.color = c;
  });

  // -------- Filtros en tiempo real --------
  const form = document.getElementById('productFilterForm');
  if (form) {
    const qInput = document.getElementById('q-input');
    let timer;
    if (qInput) {
      qInput.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => form.submit(), 350);
      });
    }
    form.querySelectorAll('select.filter-auto').forEach(sel => {
      sel.addEventListener('change', () => form.submit());
    });
  }

  // -------- Modal de detalle del producto --------
  const $modalEl = document.getElementById('productModal');
  if (!$modalEl) return;

  const $img = document.getElementById('modal-image-wrap');
  const $nombre = document.getElementById('modal-nombre');
  const $cat = document.getElementById('modal-categoria');
  const $desc = document.getElementById('modal-descripcion');
  const $precio = document.getElementById('modal-precio');
  const $estado = document.getElementById('modal-estado');
  const $btnEdit = document.getElementById('modal-btn-editar');
  const $btnDes = document.getElementById('modal-btn-desactivar');
  const $formAct = document.getElementById('modal-form-activar');

  document.querySelectorAll('.product-card, .product-row').forEach(row => {
    row.addEventListener('click', (e) => {
      if (e.target.closest('a, button, form')) return;
      abrirModal(row);
    });
    row.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        abrirModal(row);
      }
    });
  });

  function abrirModal(row) {
    const d = row.dataset;
    // Card bloqueada por el dueño: solo el modal del superowner, sin detalle normal
    if (d.bloqueoDueno === '1') {
      if (typeof window.abrirModalBloqueoDueno === 'function') {
        window.abrirModalBloqueoDueno(row);
      }
      return;
    }
    $nombre.textContent = d.nombre;
    $cat.textContent = d.categoria;
    $cat.style.background = d.categoriaColor;
    $cat.style.color = '#fff';
    $desc.textContent = d.descripcion || 'Sin descripción.';
    $precio.textContent = '$' + Number(d.precio).toLocaleString('es-AR', { minimumFractionDigits: 2 });

    if (d.imagen) {
      $img.innerHTML = '<img src="' + d.imagen + '" alt="' + escapeHtml(d.nombre) + '" class="img-fluid rounded shadow-sm" style="max-height:240px; object-fit:cover;">';
    } else {
      $img.innerHTML = '<div class="d-inline-flex align-items-center justify-content-center rounded shadow-sm" ' +
        'style="width:120px; height:120px; background:' + d.categoriaColor + '22; color:' + d.categoriaColor + ';">' +
        '<i class="fas fa-utensils fa-3x"></i></div>';
    }

    const activo = d.activo === '1';
    if (activo) {
      $estado.innerHTML = '<span class="badge badge-success badge-pill">Activo</span>';
      $btnDes.classList.remove('d-none');
      $btnDes.dataset.confirmUrl = d.deleteUrl;
      $btnDes.dataset.confirm = '¿Desactivar ' + d.nombre + '? No aparecerá en el POS pero se conservan sus ventas históricas.';
      $btnDes.dataset.confirmTitulo = '¿Desactivar producto?';
      $btnDes.dataset.confirmBoton = 'Sí, desactivar';
      $btnDes.dataset.confirmClase = 'btn-danger';
      $btnDes.dataset.confirmIcono = 'fas fa-toggle-off';
      $formAct.classList.add('d-none');
    } else {
      $estado.innerHTML = '<span class="badge badge-secondary badge-pill">Inactivo</span>';
      $btnDes.classList.add('d-none');
      $formAct.classList.remove('d-none');
      $formAct.action = d.activateUrl;
    }
    $btnEdit.href = d.editUrl;

    if (typeof jQuery !== 'undefined') {
      jQuery('#productModal').modal('show');
    } else {
      console.error('jQuery no está disponible — el modal no puede abrirse.');
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // -------- Apertura automática del detalle desde otros módulos --------
  // Ej: "Ver producto" del detalle de mensajes navega a /menu/?detalle=ID.
  const detalleId = new URLSearchParams(window.location.search).get('detalle');
  if (detalleId && /^\d+$/.test(detalleId)) {
    const card = document.querySelector('.product-card[data-id="' + detalleId + '"]');
    if (card) {
      setTimeout(() => {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        abrirModal(card);
      }, 250);
    }
  }
})();
