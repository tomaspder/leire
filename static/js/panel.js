(function () {
  "use strict";
  const data = JSON.parse(document.getElementById("chart-data").textContent);
  const fmt = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 });
  const BLUE = "#3366aa";
  const ORANGE = "#d9822b";
  const GREY = "#9aa5b1";

  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.locale = "es-ES";

  function tooltip(axis, suffix) {
    return { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmt.format(ctx.parsed[axis])}${suffix || ""}` } };
  }

  // Ajusta la altura de los gráficos horizontales al número de barrios mostrados.
  function sizeBox(canvasId, n) {
    const box = document.getElementById(canvasId).parentElement;
    box.style.height = Math.max(320, n * 22 + 60) + "px";
  }

  function horizontalBar(id, rows, label, color, suffix) {
    sizeBox(id, rows.length);
    new Chart(document.getElementById(id), {
      type: "bar",
      data: { labels: rows.map((r) => r.label), datasets: [{ label, data: rows.map((r) => r.value), backgroundColor: color }] },
      options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: tooltip("x", suffix) },
        scales: { x: { beginAtZero: true, ticks: { callback: (v) => fmt.format(v) } } },
      },
    });
  }

  horizontalBar("chart-population", data.population, "Habitantes", BLUE);
  horizontalBar("chart-density", data.density, "Densidad", ORANGE, " hab/km²");

  new Chart(document.getElementById("chart-evolution"), {
    type: "line",
    data: {
      labels: data.evolution.map((r) => r.label),
      datasets: [{ label: "Habitantes", data: data.evolution.map((r) => r.value), borderColor: BLUE, backgroundColor: BLUE, tension: 0.2 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: tooltip("y") },
      scales: { y: { ticks: { callback: (v) => fmt.format(v) }, title: { display: true, text: "Habitantes" } },
                x: { title: { display: true, text: "Fecha de referencia" } } },
    },
  });

  const selected = data.selectedDistrict;
  new Chart(document.getElementById("chart-districts"), {
    type: "bar",
    data: {
      labels: data.districts.map((r) => r.label),
      datasets: [
        { label: "Habitantes", data: data.districts.map((r) => r.population), yAxisID: "y",
          backgroundColor: data.districts.map((r) => (!selected || r.id === selected ? BLUE : GREY)) },
        { label: "Densidad (hab/km²)", data: data.districts.map((r) => r.density), yAxisID: "y1", type: "line",
          borderColor: ORANGE, backgroundColor: ORANGE },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { tooltip: tooltip("y") },
      scales: {
        y: { beginAtZero: true, position: "left", title: { display: true, text: "Habitantes" }, ticks: { callback: (v) => fmt.format(v) } },
        y1: { beginAtZero: true, position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "hab/km²" }, ticks: { callback: (v) => fmt.format(v) } },
      },
    },
  });

  new Chart(document.getElementById("chart-ages"), {
    type: "bar",
    data: { labels: data.ages.map((r) => r.label), datasets: [{ label: "Habitantes", data: data.ages.map((r) => r.value), backgroundColor: BLUE }] },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: tooltip("y") },
      scales: { y: { beginAtZero: true, ticks: { callback: (v) => fmt.format(v) } } },
    },
  });
})();
