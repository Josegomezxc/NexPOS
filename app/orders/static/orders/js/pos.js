/* =====================================================
   pos.js — Punto de Venta (POS) Táctil e Interactivo
===================================================== */
(function () {
  'use strict';

  // ---------- Configuración ----------
  const $config = document.getElementById('pos-config');
  const POS_CSRF = $config ? $config.dataset.csrf : '';
  const POS_CREATE_URL = $config ? $config.dataset.createUrl : '';

  // ---------- Datos de productos ----------
  let PRODUCTS = [];
  try {
    PRODUCTS = JSON.parse(document.getElementById('pos-productos-data').textContent || '[]');
  } catch (e) {
    PRODUCTS = [];
  }

  const productById = new Map();
  PRODUCTS.forEach(p => productById.set(String(p.id_prod), {
    id: String(p.id_prod),
    nombre: p.prod_nombre,
    precio: parseFloat(p.prod_precio) || 0,
    categoria_id: String(p.prod_categoria_id),
    descripcion: p.prod_descripcion || '',
    imagen_url: p.prod_imagen_url || '',
  }));

  // Carrito en memoria
  const cart = new Map();
  const MAX_QTY = 999;

  let state = 'editando';
  let savedTicketUrl = null;
  let savedNumero = null;
  let currentCategory = 'all';

  // ---------- Elementos DOM ----------
  const $searchInput = document.getElementById('pos-search-input');
  const $pillsContainer = document.getElementById('pos-cat-pills');
  const $touchGrid = document.getElementById('pos-touch-grid');

  const $tbody = document.getElementById('pos-cart-tbody');
  const $empty = document.getElementById('pos-cart-empty');
  const $count = document.getElementById('pos-cart-count');
  const $btnClear = document.getElementById('pos-btn-vaciar');

  const $total = document.getElementById('pos-total');
  const $btnGuardar = document.getElementById('pos-btn-guardar');
  const $btnImprimir = document.getElementById('pos-btn-imprimir');
  const $btnNuevo = document.getElementById('pos-btn-nuevo');
  const $helpText = document.getElementById('pos-help-text');

  // ---------- Utils ----------
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatMoney(n) {
    const v = Number(n) || 0;
    return '$' + v.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function sanitizeQty(value) {
    let v = parseInt(value, 10);
    if (!Number.isFinite(v) || v < 1) v = 1;
    if (v > MAX_QTY) v = MAX_QTY;
    return v;
  }

  // ---------- Filtrado de Productos en la Grilla ----------
  function filterProducts() {
    if (!$touchGrid) return;
    const query = ($searchInput ? $searchInput.value : '').toLowerCase().trim();
    const cards = $touchGrid.querySelectorAll('.pos-touch-card');

    cards.forEach(card => {
      const catId = card.dataset.categoriaId;
      const nombre = (card.dataset.nombre || '').toLowerCase();
      const desc = (card.dataset.descripcion || '').toLowerCase();

      const matchesCat = (currentCategory === 'all' || String(catId) === String(currentCategory));
      const matchesSearch = !query || nombre.includes(query) || desc.includes(query);

      if (matchesCat && matchesSearch) {
        card.style.display = 'flex';
      } else {
        card.style.display = 'none';
      }
    });
  }

  // Píldoras de categoría
  if ($pillsContainer) {
    $pillsContainer.addEventListener('click', (e) => {
      const pill = e.target.closest('.pos-cat-pill');
      if (!pill) return;

      $pillsContainer.querySelectorAll('.pos-cat-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentCategory = pill.dataset.catId;
      filterProducts();
    });
  }

  // Búsqueda en tiempo real
  if ($searchInput) {
    $searchInput.addEventListener('input', filterProducts);
  }

  // Clic en Tarjeta de Producto
  if ($touchGrid) {
    $touchGrid.addEventListener('click', (e) => {
      const card = e.target.closest('.pos-touch-card');
      if (!card) return;

      if (state === 'guardado') reiniciar();

      const id = card.dataset.id;
      const p = productById.get(id);
      if (!p) return;

      if (cart.has(id)) {
        cart.get(id).cantidad = sanitizeQty(cart.get(id).cantidad + 1);
      } else {
        cart.set(id, {
          id: p.id,
          nombre: p.nombre,
          precio: p.precio,
          descripcion: p.descripcion,
          cantidad: 1,
        });
      }
      render();
      flash(`+1 ${p.nombre} agregado al pedido`);
    });
  }

  // ---------- Render del Carrito / Ticket ----------
  function render() {
    if (!$tbody) return;

    $tbody.querySelectorAll('tr.cart-row').forEach(tr => tr.remove());

    const empty = cart.size === 0;
    if ($empty) $empty.style.display = empty ? '' : 'none';

    const guardado = state === 'guardado';
    let total = 0;

    for (const item of cart.values()) {
      const subtotal = item.precio * item.cantidad;
      total += subtotal;
      const tr = document.createElement('tr');
      tr.className = 'cart-row';

      const qtyCell = guardado
        ? `<span class="font-weight-bold">${item.cantidad}</span>`
        : `<div class="pos-stepper-wrap">
            <button type="button" class="pos-stepper-btn" data-act="dec" data-id="${item.id}">-</button>
            <span class="pos-stepper-val">${item.cantidad}</span>
            <button type="button" class="pos-stepper-btn" data-act="inc" data-id="${item.id}">+</button>
           </div>`;

      const delCell = guardado
        ? ''
        : `<button type="button" class="btn btn-sm btn-link text-danger p-0" data-act="del" data-id="${item.id}" title="Quitar">
             <i class="fas fa-trash-alt"></i>
           </button>`;

      tr.innerHTML = `
        <td class="align-middle">
          <strong class="d-block text-dark">${escapeHtml(item.nombre)}</strong>
          <small class="text-muted">${formatMoney(item.precio)} c/u</small>
        </td>
        <td class="text-center align-middle">${qtyCell}</td>
        <td class="text-right align-middle font-weight-bold text-dark">${formatMoney(subtotal)}</td>
        <td class="text-center align-middle">${delCell}</td>`;

      $tbody.appendChild(tr);
    }

    const count = Array.from(cart.values()).reduce((s, i) => s + i.cantidad, 0);
    if ($total) $total.textContent = formatMoney(total);
    if ($count) $count.textContent = count;

    actualizarBotones(empty);
  }

  function actualizarBotones(empty) {
    if (state === 'editando') {
      $btnGuardar.classList.remove('d-none');
      $btnImprimir.classList.add('d-none');
      $btnNuevo.classList.add('d-none');
      $btnGuardar.disabled = empty;
      if ($btnClear) $btnClear.disabled = false;
      if ($helpText) {
        $helpText.textContent = empty
          ? 'El botón se activa cuando agregás al menos un producto al pedido.'
          : 'Revisá el pedido y presioná "Guardar pedido" para generar el ticket.';
      }
    } else if (state === 'guardado') {
      $btnGuardar.classList.add('d-none');
      $btnImprimir.classList.remove('d-none');
      $btnNuevo.classList.remove('d-none');
      $btnImprimir.disabled = false;
      if ($btnClear) $btnClear.disabled = true;
      if ($helpText) {
        $helpText.textContent = savedNumero
          ? `Pedido ${savedNumero} guardado. Imprimí el ticket: el cliente paga en Caja.`
          : 'Pedido guardado. Imprimí el ticket: el cliente paga en Caja.';
      }
    }
  }

  // ---------- Eventos Stepper e Ítems en el Carrito ----------
  if ($tbody) {
    $tbody.addEventListener('click', (ev) => {
      if (state === 'guardado') return;

      const btnInc = ev.target.closest('button[data-act="inc"]');
      const btnDec = ev.target.closest('button[data-act="dec"]');
      const btnDel = ev.target.closest('button[data-act="del"]');

      if (btnInc) {
        const item = cart.get(btnInc.dataset.id);
        if (item) {
          item.cantidad = sanitizeQty(item.cantidad + 1);
          render();
        }
      } else if (btnDec) {
        const item = cart.get(btnDec.dataset.id);
        if (item) {
          if (item.cantidad > 1) {
            item.cantidad = sanitizeQty(item.cantidad - 1);
          } else {
            cart.delete(btnDec.dataset.id);
          }
          render();
        }
      } else if (btnDel) {
        cart.delete(btnDel.dataset.id);
        render();
      }
    });
  }

  // Vaciar Carrito
  if ($btnClear) {
    $btnClear.addEventListener('click', () => {
      if (state === 'guardado' || cart.size === 0) return;
      if (window.mostrarConfirmacion) {
        window.mostrarConfirmacion({
          titulo: '¿Vaciar el pedido?',
          mensaje: 'Se quitan todos los ítems del carrito.',
          boton: 'Sí, vaciar',
          clase: 'btn-warning',
          icono: 'fas fa-trash',
          alAceptar: () => {
            cart.clear();
            render();
          },
        });
      } else {
        cart.clear();
        render();
      }
    });
  }

  // ---------- Guardar pedido ----------
  async function guardarPedido() {
    if (cart.size === 0 || state !== 'editando') return;

    for (const item of cart.values()) {
      item.cantidad = sanitizeQty(item.cantidad);
    }

    const payload = {
      items: Array.from(cart.values()).map(i => ({
        producto_id: i.id, cantidad: i.cantidad,
      })),
    };

    $btnGuardar.disabled = true;
    const originalLabel = $btnGuardar.innerHTML;
    $btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

    try {
      const resp = await fetch(POS_CREATE_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': POS_CSRF,
        },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || 'Error al guardar.');

      savedTicketUrl = data.ticket_url;
      savedNumero = data.numero;
      state = 'guardado';
      render();
      flash(`Pedido ${data.numero} guardado (${formatMoney(data.total)}). El cliente paga en Caja.`);
    } catch (err) {
      flash('Error al guardar el pedido: ' + err.message, 'error');
      $btnGuardar.innerHTML = originalLabel;
      $btnGuardar.disabled = cart.size === 0;
    }
  }

  function imprimirTicket() {
    if (state !== 'guardado' || !savedTicketUrl) return;
    window.open(savedTicketUrl, '_blank');
  }

  function reiniciar() {
    cart.clear();
    state = 'editando';
    savedTicketUrl = null;
    savedNumero = null;
    $btnGuardar.innerHTML = '<i class="fas fa-save"></i> Guardar pedido';
    render();
  }

  if ($btnGuardar) $btnGuardar.addEventListener('click', guardarPedido);
  if ($btnImprimir) $btnImprimir.addEventListener('click', imprimirTicket);
  if ($btnNuevo) $btnNuevo.addEventListener('click', reiniciar);

  function flash(msg, tipo) {
    const esError = tipo === 'error';
    const toast = document.createElement('div');
    toast.className = esError ? 'pos-toast pos-toast-danger' : 'pos-toast';
    toast.setAttribute('role', esError ? 'alert' : 'status');
    toast.innerHTML = `<i class="${esError ? 'fas fa-check-circle' : 'fas fa-plus-circle'}"></i><span>${escapeHtml(msg)}</span>`;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  render();
})();
