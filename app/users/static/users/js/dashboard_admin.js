/* =====================================================
   dashboard_admin.js
   Renderiza los gráficos del dashboard con Chart.js:
   1. Ventas por período (interactivo con selector 7d, 30d, 12m)
   2. Ingresos por categoría (Gráfico de barras horizontales interactivo)
===================================================== */
(function () {
  'use strict';

  if (typeof Chart === 'undefined') {
    console.warn('Chart.js no está cargado.');
    return;
  }

  // -------- Leer datos del HTML --------
  let data;
  try {
    data = JSON.parse(document.getElementById('dashboard-chart-data').textContent);
  } catch (e) {
    console.error('No se pudieron parsear los datos de los gráficos', e);
    return;
  }

  const BRAND = getComputedStyle(document.documentElement).getPropertyValue('--brand').trim() || '#2563EB';
  const BRAND_DEEP = getComputedStyle(document.documentElement).getPropertyValue('--brand-deep').trim() || '#1E3A8A';

  // -------- Gráfico 1: Ventas por período (línea suave interactiva) --------
  const $linea = document.getElementById('chart-ventas-dias');
  const $selectPeriodo = document.getElementById('chart-periodo-select');
  const $tituloLinea = document.getElementById('chart-linea-titulo');

  let lineaChart = null;

  if ($linea && data.periodos) {
    const defaultKey = ($selectPeriodo ? $selectPeriodo.value : '7d') || '7d';
    const periodInfo = data.periodos[defaultKey] || data.periodos['7d'];

    if ($tituloLinea) $tituloLinea.textContent = periodInfo.titulo;

    lineaChart = new Chart($linea, {
      type: 'line',
      data: {
        labels: periodInfo.labels,
        datasets: [{
          label: 'Ventas ($)',
          data: periodInfo.data,
          fill: true,
          backgroundColor: 'rgba(37, 99, 235, 0.15)',
          borderColor: BRAND,
          borderWidth: 3,
          pointBackgroundColor: BRAND,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 7,
          lineTension: 0.35,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: { display: false },
        scales: {
          yAxes: [{
            ticks: {
              beginAtZero: true,
              callback: (value) => '$' + Number(value).toLocaleString('es-AR'),
            },
            gridLines: { color: '#f1f5f9', zeroLineColor: '#e2e8f0', drawBorder: false },
          }],
          xAxes: [{
            gridLines: { display: false, drawBorder: false },
          }],
        },
        tooltips: {
          backgroundColor: BRAND_DEEP,
          titleFontColor: '#fff',
          bodyFontColor: '#fff',
          callbacks: {
            label: (item) => ' Ventas: $' + Number(item.yLabel).toLocaleString('es-AR', { minimumFractionDigits: 2 }),
          },
        },
      },
    });

    // Cambio interactivo de período de ventas sin recargar
    if ($selectPeriodo) {
      $selectPeriodo.addEventListener('change', () => {
        const key = $selectPeriodo.value;
        const target = data.periodos[key];
        if (!target || !lineaChart) return;

        if ($tituloLinea) $tituloLinea.textContent = target.titulo;

        lineaChart.data.labels = target.labels;
        lineaChart.data.datasets[0].data = target.data;
        lineaChart.update();
      });
    }
  }

  // -------- Gráfico 2: Ingresos por Categoría (Barras Horizontales con Filtros) --------
  const $cat = document.getElementById('chart-ventas-categorias');
  const $selectCatPeriodo = document.getElementById('chart-cat-periodo-select');
  let catChart = null;

  if ($cat && (data.categorias || data.categorias_periodos)) {
    const catDataObj = data.categorias_periodos
      ? (data.categorias_periodos[$selectCatPeriodo ? $selectCatPeriodo.value : 'mes'] || data.categorias)
      : data.categorias;

    catChart = new Chart($cat, {
      type: 'horizontalBar',
      data: {
        labels: catDataObj.labels || [],
        datasets: [{
          label: 'Ingresos ($)',
          data: catDataObj.data || [],
          backgroundColor: catDataObj.colors || '#2563eb',
          borderColor: catDataObj.colors || '#2563eb',
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: { display: false },
        scales: {
          xAxes: [{
            ticks: {
              beginAtZero: true,
              callback: (value) => '$' + Number(value).toLocaleString('es-AR'),
            },
            gridLines: { color: '#f1f5f9', zeroLineColor: '#e2e8f0', drawBorder: false },
          }],
          yAxes: [{
            gridLines: { display: false, drawBorder: false },
          }],
        },
        tooltips: {
          backgroundColor: BRAND_DEEP,
          titleFontColor: '#fff',
          bodyFontColor: '#fff',
          callbacks: {
            label: (item) => ' Ingresos: $' + Number(item.xLabel).toLocaleString('es-AR', { minimumFractionDigits: 2 }),
          },
        },
      },
    });

    // Cambio interactivo de período para categorías sin recargar la página
    if ($selectCatPeriodo && data.categorias_periodos) {
      $selectCatPeriodo.addEventListener('change', () => {
        const key = $selectCatPeriodo.value;
        const target = data.categorias_periodos[key];
        if (!target || !catChart) return;

        catChart.data.labels = target.labels;
        catChart.data.datasets[0].data = target.data;
        catChart.data.datasets[0].backgroundColor = target.colors;
        catChart.data.datasets[0].borderColor = target.colors;
        catChart.update();
      });
    }
  }
})();
