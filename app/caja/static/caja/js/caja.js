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

  function sanitizarMonto(v) {
    var limpio = String(v || '').replace(/[^\d.,]/g, '');
    var prim = limpio.search(/[.,]/);
    if (prim === -1) return limpio.slice(0, 10);
    var ints = limpio.slice(0, prim).replace(/[.,]/g, '').slice(0, 10);
    var decs = limpio.slice(prim + 1).replace(/[.,]/g, '').slice(0, 2);
    return ints + ',' + decs;
  }

  if (metodo) metodo.addEventListener('change', actualizarPago);
  if (recibido) {
    recibido.addEventListener('keydown', function (e) {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      var tecla = e.key;
      if (tecla.length !== 1) return;
      if (!/[0-9.,]/.test(tecla)) {
        e.preventDefault();
        return;
      }
      var actual = sanitizarMonto(recibido.value);
      var inicio = recibido.selectionStart;
      var fin = recibido.selectionEnd;
      var hipotetico = actual.slice(0, inicio) + tecla + actual.slice(fin);
      if (sanitizarMonto(hipotetico) !== hipotetico) e.preventDefault();
    });

    recibido.addEventListener('paste', function (e) {
      var texto = (e.clipboardData || window.clipboardData).getData('text') || '';
      var solo = texto.replace(/[^\d.,]/g, '');
      var limpio = sanitizarMonto(texto);
      if (limpio.replace(',', '.') !== solo.replace(',', '.')) e.preventDefault();
    });

    recibido.addEventListener('input', function () {
      var s = sanitizarMonto(recibido.value);
      if (recibido.value !== s) recibido.value = s;
      actualizarPago();
    });
  }

  actualizarPago();
})();
