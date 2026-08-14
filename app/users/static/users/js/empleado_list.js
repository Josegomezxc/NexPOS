/* =====================================================
   empleado_list.js — filtros en tiempo real y modal
   de detalle del usuario/empleado al hacer clic en una tarjeta.
===================================================== */
(function () {
  'use strict';

  // -------- Filtros en tiempo real --------
  const form = document.getElementById('empleadoFilterForm');
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

  // -------- Modal de detalle del empleado --------
  const $modalEl = document.getElementById('empleadoModal');
  if (!$modalEl) return;

  const $avatarWrap = document.getElementById('emp-modal-avatar');
  const $name = document.getElementById('emp-modal-nombre');
  const $username = document.getElementById('emp-modal-username');
  const $rol = document.getElementById('emp-modal-rol');
  const $email = document.getElementById('emp-modal-email');
  const $joined = document.getElementById('emp-modal-joined');
  const $estado = document.getElementById('emp-modal-estado');
  const $btnEdit = document.getElementById('emp-modal-btn-editar');
  const $btnDes = document.getElementById('emp-modal-btn-desactivar');
  const $formAct = document.getElementById('emp-modal-form-activar');

  document.querySelectorAll('.empleado-card').forEach(card => {
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
    // Card bloqueada por el dueño: solo el modal del superowner, sin detalle normal
    if (d.bloqueoDueno === '1') {
      if (typeof window.abrirModalBloqueoDueno === 'function') {
        window.abrirModalBloqueoDueno(card);
      }
      return;
    }
    $name.textContent = d.nombre;
    $username.textContent = '@' + d.username;
    $email.textContent = d.email || 'Sin correo asignado';
    $joined.textContent = d.joined || '-';

    const esAdmin = d.esAdmin === '1';
    if (esAdmin) {
      $rol.className = 'badge badge-primary empleado-role-badge';
      $rol.innerHTML = '<i class="fas fa-crown mr-1"></i> Administrador';
      $avatarWrap.className = 'empleado-avatar avatar-admin shadow-sm';
      $avatarWrap.innerHTML = '<i class="fas fa-user-shield"></i>';
    } else {
      $rol.className = 'badge badge-secondary empleado-role-badge';
      $rol.innerHTML = '<i class="fas fa-user mr-1"></i> Empleado';
      $avatarWrap.className = 'empleado-avatar avatar-empleado shadow-sm';
      $avatarWrap.innerHTML = '<i class="fas fa-user-tie"></i>';
    }

    const activo = d.activo === '1';
    const isSelf = d.isSelf === '1';

    if (activo) {
      $estado.innerHTML = '<span class="badge badge-success badge-pill">Activo</span>';
    } else {
      $estado.innerHTML = '<span class="badge badge-danger badge-pill">Inactivo</span>';
    }

    $btnEdit.href = d.editUrl;

    if (isSelf) {
      $btnDes.classList.add('d-none');
      $formAct.classList.add('d-none');
    } else if (activo) {
      $btnDes.classList.remove('d-none');
      $btnDes.dataset.confirmUrl = d.deleteUrl;
      $btnDes.dataset.confirm = '¿Desactivar a ' + d.nombre + '? Perderá el acceso al sistema.';
      $btnDes.dataset.confirmTitulo = '¿Desactivar empleado?';
      $btnDes.dataset.confirmBoton = 'Sí, desactivar';
      $btnDes.dataset.confirmClase = 'btn-danger';
      $btnDes.dataset.confirmIcono = 'fas fa-user-slash';
      $formAct.classList.add('d-none');
    } else {
      $btnDes.classList.add('d-none');
      $formAct.classList.remove('d-none');
      $formAct.action = d.activateUrl;
    }

    if (typeof jQuery !== 'undefined') {
      jQuery('#empleadoModal').modal('show');
    } else {
      console.error('jQuery no está disponible — el modal no puede abrirse.');
    }
  }
})();
