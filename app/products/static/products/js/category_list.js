/* =====================================================
   category_list.js
   - Modal de detalle de la categoría al hacer clic en una tarjeta
===================================================== */
(function () {
  'use strict';

  const $modalEl = document.getElementById('categoryModal');
  if (!$modalEl) return;

  const $img = document.getElementById('cat-modal-image-wrap');
  const $nombre = document.getElementById('cat-modal-nombre');
  const $desc = document.getElementById('cat-modal-descripcion');
  const $count = document.getElementById('cat-modal-count');
  const $estado = document.getElementById('cat-modal-estado');
  const $btnEdit = document.getElementById('cat-modal-btn-editar');
  const $btnDes = document.getElementById('cat-modal-btn-desactivar');
  const $formAct = document.getElementById('cat-modal-form-activar');

  document.querySelectorAll('.category-card').forEach(card => {
    card.style.cursor = 'pointer';
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
    $nombre.textContent = d.nombre;
    $desc.textContent = d.descripcion || 'Sin descripción.';
    $count.textContent = d.count + (d.count === '1' ? ' producto' : ' productos');

    if (d.imagen) {
      $img.innerHTML = '<img src="' + d.imagen + '" alt="' + escapeHtml(d.nombre) + '" class="img-fluid rounded shadow-sm" style="max-height:220px; width:100%; object-fit:cover;">';
    } else {
      $img.innerHTML = '<div class="d-flex align-items-center justify-content-center rounded shadow-sm" ' +
        'style="height:160px; background: linear-gradient(135deg, ' + (d.color || '#3b82f6') + ' 0%, #1e293b 120%); color:#fff;">' +
        '<i class="' + (d.icono || 'fas fa-tag') + ' fa-4x"></i></div>';
    }

    const activa = d.activa === '1';
    if (activa) {
      $estado.innerHTML = '<span class="badge badge-success badge-pill">Activa</span>';
      $btnDes.classList.remove('d-none');
      $btnDes.dataset.confirmUrl = d.deleteUrl;
      $btnDes.dataset.confirm = '¿Desactivar la categoría ' + d.nombre + '? No aparecerá en el menú y sus productos se desactivan.';
      $btnDes.dataset.confirmTitulo = '¿Desactivar categoría?';
      $btnDes.dataset.confirmBoton = 'Sí, desactivar';
      $btnDes.dataset.confirmClase = 'btn-danger';
      $btnDes.dataset.confirmIcono = 'fas fa-toggle-off';
      $formAct.classList.add('d-none');
    } else {
      $estado.innerHTML = '<span class="badge badge-secondary badge-pill">Inactiva</span>';
      $btnDes.classList.add('d-none');
      $formAct.classList.remove('d-none');
      $formAct.action = d.activateUrl;
    }
    $btnEdit.href = d.editUrl;

    if (typeof jQuery !== 'undefined') {
      jQuery('#categoryModal').modal('show');
    } else {
      console.error('jQuery no está disponible — el modal no puede abrirse.');
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
})();
