/**
 * SafeSight AI – Dashboard BI Controller
 * Manages Chart.js instances, Plotly heatmap, circular gauge updates,
 * asynchronous filtering, and demo data re-seeding.
 */

let timeseriesChartInstance = null;
let violationsTypeChartInstance = null;
let complianceTrendChartInstance = null;
let cameraZoneChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  initDashboard();

  // Filter Button
  const applyBtn = document.getElementById("applyFiltersBtn");
  if (applyBtn) {
    applyBtn.addEventListener("click", () => fetchAllAnalytics());
  }

  // Load Demo Data Button
  const demoBtn = document.getElementById("loadDemoDataBtn");
  if (demoBtn) {
    demoBtn.addEventListener("click", async () => {
      demoBtn.disabled = true;
      demoBtn.innerHTML = "<span>⏳</span> Loading...";
      try {
        const res = await fetch("/api/seed-demo", { method: "POST" });
        const data = await res.json();
        showToast(data.message || "Demo data loaded successfully!", "success");
        setTimeout(() => location.reload(), 600);
      } catch (err) {
        showToast("Error reloading demo data: " + err, "error");
        demoBtn.disabled = false;
        demoBtn.innerHTML = "<span>🔄</span> Load Demo Data";
      }
    });
  }
});

function getFilterParams() {
  const camera = document.getElementById("cameraFilter")?.value || "all";
  const dateFrom = document.getElementById("dateFrom")?.value || "";
  const dateTo = document.getElementById("dateTo")?.value || "";

  const params = new URLSearchParams();
  if (camera && camera !== "all") params.append("camera", camera);
  if (dateFrom) params.append("date_from", dateFrom);
  if (dateTo) params.append("date_to", dateTo);
  return params.toString();
}

async function initDashboard() {
  await fetchAllAnalytics();
}

async function fetchAllAnalytics() {
  const query = getFilterParams();

  // 1. Fetch KPI & Safety Score
  fetch(`/api/analytics/kpi?${query}`)
    .then(r => r.json())
    .then(data => updateKPIs(data))
    .catch(console.error);

  fetch(`/api/analytics/safety-score?${query}`)
    .then(r => r.json())
    .then(data => updateSafetyScore(data))
    .catch(console.error);

  // 2. Fetch Charts Data
  fetch(`/api/analytics/timeseries?${query}`)
    .then(r => r.json())
    .then(data => renderTimeseriesChart(data))
    .catch(console.error);

  fetch(`/api/analytics/violations-by-type?${query}`)
    .then(r => r.json())
    .then(data => renderViolationsTypeChart(data))
    .catch(console.error);

  fetch(`/api/analytics/heatmap?${query}`)
    .then(r => r.json())
    .then(data => renderPlotlyHeatmap(data))
    .catch(console.error);

  fetch(`/api/analytics/compliance-trend?${query}`)
    .then(r => r.json())
    .then(data => renderComplianceTrend(data))
    .catch(console.error);

  fetch(`/api/analytics/violations-by-camera?${query}`)
    .then(r => r.json())
    .then(data => renderCameraZoneChart(data))
    .catch(console.error);
}

function updateKPIs(kpi) {
  if (!kpi) return;
  document.getElementById("kpiTotalPeople").innerText = kpi.total_people || 0;
  document.getElementById("kpiSafe").innerText = kpi.safe_count || 0;
  document.getElementById("kpiUnsafe").innerText = kpi.unsafe_count || 0;
  document.getElementById("kpiCompliance").innerText = (kpi.compliance_percent || 0) + "%";
  document.getElementById("kpiViolations").innerText = kpi.total_violations || 0;
}

function updateSafetyScore(scoreData) {
  if (!scoreData) return;
  const valEl = document.getElementById("safetyGaugeVal");
  const statEl = document.getElementById("safetyGaugeStatus");
  const gaugeCircle = document.getElementById("safetyGauge");

  const score = scoreData.score || 94.5;
  if (valEl) valEl.innerText = score + "%";
  if (statEl) {
    statEl.innerText = scoreData.status || "Optimal";
    statEl.style.color = scoreData.color || "#22C55E";
  }

  // Update conic gradient
  if (gaugeCircle) {
    const col = scoreData.color || "#22C55E";
    gaugeCircle.style.background = `conic-gradient(${col} 0% ${score}%, var(--border-color) ${score}% 100%)`;
  }
}

function renderTimeseriesChart(ts) {
  const ctx = document.getElementById("timeseriesChart")?.getContext("2d");
  if (!ctx) return;

  if (timeseriesChartInstance) {
    timeseriesChartInstance.destroy();
  }

  timeseriesChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: ts.dates.map(d => d.slice(5)), // MM-DD
      datasets: [
        {
          label: "Helmet",
          data: ts.helmet,
          borderColor: "#EF4444",
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          tension: 0.35,
          borderWidth: 2,
          fill: true
        },
        {
          label: "Vest",
          data: ts.vest,
          borderColor: "#F59E0B",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        },
        {
          label: "Goggles",
          data: ts.goggles,
          borderColor: "#3B82F6",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        },
        {
          label: "Other",
          data: ts.other,
          borderColor: "#8B5CF6",
          backgroundColor: "transparent",
          tension: 0.35,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, font: { family: "Inter", size: 11 } } },
        tooltip: { mode: "index", intersect: false }
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(100, 116, 139, 0.1)" }, ticks: { precision: 0 } },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderViolationsTypeChart(typesData) {
  const ctx = document.getElementById("violationsTypeChart")?.getContext("2d");
  if (!ctx) return;

  if (violationsTypeChartInstance) {
    violationsTypeChartInstance.destroy();
  }

  const vTot = document.getElementById("vTotalCount");
  if (vTot) vTot.innerText = typesData.total || 0;

  violationsTypeChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Helmet", "Safety Vest", "Goggles", "Other"],
      datasets: [
        {
          data: [
            typesData.helmet || 0,
            typesData.vest || 0,
            typesData.goggles || 0,
            typesData.other || 0
          ],
          backgroundColor: ["#EF4444", "#F59E0B", "#3B82F6", "#8B5CF6"],
          borderWidth: 2,
          borderColor: "var(--bg-surface)"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { position: "bottom", labels: { font: { family: "Inter", size: 11 } } }
      }
    }
  });
}

function renderPlotlyHeatmap(hData) {
  const container = document.getElementById("plotlyHeatmap");
  if (!container) return;

  const data = [
    {
      z: hData.z,
      x: hData.x,
      y: hData.y,
      type: "heatmap",
      colorscale: [
        [0, "#F8FAFC"],
        [0.2, "#DBEAFE"],
        [0.5, "#60A5FA"],
        [0.8, "#2563EB"],
        [1.0, "#0B1B3F"]
      ],
      showscale: false
    }
  ];

  const layout = {
    margin: { t: 10, r: 10, b: 35, l: 40 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { family: "Inter", size: 10, color: "#64748B" },
    xaxis: { tickangle: -45, nticks: 12 },
    yaxis: { autorange: "reversed" }
  };

  const config = { responsive: true, displayModeBar: false };
  Plotly.newPlot("plotlyHeatmap", data, layout, config);
}

function renderComplianceTrend(trend) {
  const ctx = document.getElementById("complianceTrendChart")?.getContext("2d");
  if (!ctx) return;

  if (complianceTrendChartInstance) {
    complianceTrendChartInstance.destroy();
  }

  complianceTrendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: trend.dates.map(d => d.slice(5)),
      datasets: [
        {
          label: "Compliance %",
          data: trend.compliance,
          borderColor: "#22C55E",
          backgroundColor: "rgba(34, 197, 94, 0.1)",
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 70, max: 100, grid: { color: "rgba(100, 116, 139, 0.1)" } },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderCameraZoneChart(data) {
  const ctx = document.getElementById("cameraZoneChart")?.getContext("2d");
  if (!ctx) return;

  if (cameraZoneChartInstance) {
    cameraZoneChartInstance.destroy();
  }

  cameraZoneChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.cameras.map(c => c.split("–")[0].trim()),
      datasets: [
        {
          label: "Violations",
          data: data.counts,
          backgroundColor: "#F97316",
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(100, 116, 139, 0.1)" } },
        x: { grid: { display: false } }
      }
    }
  });
}
