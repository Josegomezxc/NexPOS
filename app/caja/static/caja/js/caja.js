/* =====================================================
   Caja - formulario simplificado de cobro POS
   1. Método de pago: efectivo muestra "monto recibido" + vuelto
   Vuelto = recibido - total (solo efectivo).
===================================================== */

(function () {
  'use strict';

  var form = document.querySelector('form[data-total]');
  if (!form) return;

  var TOTAL = parseFloat(form.dataset.total) || 0;

  var metodo = document.getElementById('metodo_pago');
  var recibidoWrap = document.getElementById('recibido-wrap');
  var recibido = document.getElementById('recibido');
  var vueltoBox = document.getElementById('vuelto-box');
  var vueltoAmount = document.getElementById('vuelto-amount');

  function formatMoney(n) {
    var v = Number(n) || 0;
    return '$' + v.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function actualizarPago() {
    if (!metodo) return;
    var esEfectivo = metodo.value === 'efectivo';
    if (recibidoWrap) recibidoWrap.classList.toggle('d-none', !esEfectivo);
    if (!esEfectivo) {
      if (vueltoBox) vueltoBox.classList.add('d-none');
      return;
    }
    if (!recibido) return;
    var rec = parseFloat(String(recibido.value).replace(',', '.'));
    if (Number.isFinite(rec) && rec >= TOTAL) {
      if (vueltoBox) vueltoBox.classList.remove('d-none');
      if (vueltoAmount) vueltoAmount.textContent = formatMoney(rec - TOTAL);
    } else {
      if (vueltoBox) vueltoBox.classList.add('d-none');
    }
  }

  if (metodo) metodo.addEventListener('change', actualizarPago);
  if (recibido) recibido.addEventListener('input', actualizarPago);

  actualizarPago();
})();
