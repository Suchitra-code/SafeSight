/**
 * SafeSight AI — Premium Workplace Safety Intelligence Platform Controller
 * Manages live data synchronization, URL filter state, Chart.js visualizations,
 * count-up animations, inspection scheduling, and AI Insights interactions.
 * Strictly adheres to the Sunrise Garden palette (0 black, 0 blue).
 */

function getCssVar(name, fallback) {
  if (typeof window === "undefined" || !document.documentElement) return fallback;
  const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return val || fallback;
}

function hexToRgba(hex, alpha) {
  if (!hex || typeof hex !== "string" || !hex.startsWith("#")) return `rgba(226, 99, 75, ${alpha})`;
  let c = hex.replace("#", "");
  if (c.length === 3) c = c.split("").map(x => x + x).join("");
  const num = parseInt(c, 16);
  if (isNaN(num)) return `rgba(226, 99, 75, ${alpha})`;
  return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`;
}

// Dual-Palette System: Dynamic CSS Variable Architecture
function getActivePalette() {
  const mode = (document.documentElement && document.documentElement.dataset.palette) || "vivid";
  const isVivid = mode === "vivid";
  return {
    mode: mode,
    fontFamily: isVivid ? "'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif" : "'Manrope', 'Inter', -apple-system, sans-serif",
    textMain: getCssVar("--text-main", "#6B3A4D"),
    textStrong: getCssVar("--text-strong", "#4A1D2F"),
    textMuted: getCssVar("--text-muted", "#8A6577"),
    border: getCssVar("--border-soft", "#F1DED2"),
    gridColor: getCssVar("--chart-grid", "rgba(241, 222, 210, 0.6)"),
    tooltipBg: getCssVar("--chart-tooltip-bg", "#FFFBF5"),
    tooltipTitle: isVivid ? "#FFFFFF" : getCssVar("--text-strong", "#4A1D2F"),
    tooltipBody: isVivid ? "#FFFFFF" : getCssVar("--text-main", "#6B3A4D"),
    tooltipBorder: getCssVar("--chart-tooltip-border", "#F1DED2"),
    ppeHelmet: getCssVar("--chart-ppe-helmet", "#E8A33D"),
    ppeVest: getCssVar("--chart-ppe-vest", "#E2634B"),
    ppeShoes: getCssVar("--chart-ppe-shoes", "#1F9D6E"),
    ppeGoggles: getCssVar("--chart-ppe-goggles", "#D94F70"),
    ppeOther: getCssVar("--chart-ppe-other", "#A83E97"),
    ppeWith: getCssVar("--mint", "#1F9D6E"),
    ppeWithout: getCssVar("--burgundy", "#B8283F"),
    sevHigh: getCssVar("--chart-sev-high", "#B8283F"),
    sevMed: getCssVar("--chart-sev-med", "#E8A33D"),
    sevLow: getCssVar("--chart-sev-low", "#1F9D6E"),
    complianceLine: getCssVar("--chart-compliance-line", "#1F9D6E"),
    targetLine: getCssVar("--chart-target-line", "#E8A33D")
  };
}

const PALETTE = getActivePalette();

// Global chart instances
let complianceTrendChartInstance = null;
let violationsTypeChartInstance = null;
let deptPerformanceChartInstance = null;
let complianceTrendCurveChartInstance = null;
let violationsGearCategoryChartInstance = null;

// Live detections carousel state
let detectionItems = [];
let currentDetectionIdx = 0;

// Filter state
let currentFilters = {
  range: "all",
  dateFrom: "",
  dateTo: "",
  department: "all",
  location: "all",
  type: "all",
  status: "all"
};

let autoRefreshInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  setupChartDefaults();
  initUrlFilters();
  setupFilterEventListeners();
  setupModalEventListeners();
  setupCarouselControls();
  setupExportActions();
  setupAutoRefresh();
  fetchSystemHealth();
  fetchLatestDetections();
  fetchRecentViolations();
  fetchAllAnalytics();
});

/**
 * Configure Chart.js global defaults so NO black and NO blue appear.
 */
function setupChartDefaults() {
  if (!window.Chart) return;
  const pal = getActivePalette();

  Chart.defaults.color = pal.textMain;
  Chart.defaults.borderColor = pal.border;
  Chart.defaults.font.family = pal.fontFamily || "'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif";
  Chart.defaults.font.size = 11;

  if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) {
    Chart.defaults.plugins.tooltip.backgroundColor = pal.tooltipBg;
    Chart.defaults.plugins.tooltip.titleColor = pal.tooltipTitle;
    Chart.defaults.plugins.tooltip.bodyColor = pal.tooltipBody;
    Chart.defaults.plugins.tooltip.borderColor = pal.tooltipBorder;
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
  }
}

// Redraw all charts on palette mode toggle
window.addEventListener("paletteChanged", () => {
  setupChartDefaults();
  if (typeof fetchAllAnalytics === "function") {
    fetchAllAnalytics();
  }
});

/**
 * Read URL search parameters on page load to restore filter state.
 */
function initUrlFilters() {
  const params = new URLSearchParams(window.location.search);
  if (params.has("department")) currentFilters.department = params.get("department");
  if (params.has("location")) currentFilters.location = params.get("location");
  if (params.has("type")) currentFilters.type = params.get("type");
  if (params.has("from")) currentFilters.dateFrom = params.get("from");
  if (params.has("to")) currentFilters.dateTo = params.get("to");
  if (params.has("status")) currentFilters.status = params.get("status");

  // Sync inputs
  const deptSelect = document.getElementById("filterDepartment");
  if (deptSelect && currentFilters.department !== "all") deptSelect.value = currentFilters.department;

  const locSelect = document.getElementById("filterLocation");
  if (locSelect && currentFilters.location !== "all") locSelect.value = currentFilters.location;

  const typeSelect = document.getElementById("filterType");
  if (typeSelect && currentFilters.type !== "all") typeSelect.value = currentFilters.type;

  const dateFromInput = document.getElementById("filterDateFrom");
  if (dateFromInput && currentFilters.dateFrom) dateFromInput.value = currentFilters.dateFrom;

  const dateToInput = document.getElementById("filterDateTo");
  if (dateToInput && currentFilters.dateTo) dateToInput.value = currentFilters.dateTo;

  updateFilterChips();
}

/**
 * Attach listeners to filter presets, selects, date pickers, and reset button.
 */
function setupFilterEventListeners() {
  // Preset buttons (All, Today, 7d, 30d)
  document.querySelectorAll(".date-preset-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".date-preset-pill").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const range = btn.dataset.range;
      currentFilters.range = range;

      const today = new Date();
      const formatDate = (d) => d.toISOString().split("T")[0];

      if (range === "today") {
        currentFilters.dateFrom = formatDate(today);
        currentFilters.dateTo = formatDate(today);
      } else if (range === "7d") {
        const past7 = new Date();
        past7.setDate(today.getDate() - 7);
        currentFilters.dateFrom = formatDate(past7);
        currentFilters.dateTo = formatDate(today);
      } else if (range === "30d") {
        const past30 = new Date();
        past30.setDate(today.getDate() - 30);
        currentFilters.dateFrom = formatDate(past30);
        currentFilters.dateTo = formatDate(today);
      } else {
        currentFilters.dateFrom = "";
        currentFilters.dateTo = "";
      }

      const df = document.getElementById("filterDateFrom");
      const dt = document.getElementById("filterDateTo");
      if (df) df.value = currentFilters.dateFrom;
      if (dt) dt.value = currentFilters.dateTo;

      onFiltersChanged();
    });
  });

  // Selects
  const deptSelect = document.getElementById("filterDepartment");
  if (deptSelect) {
    deptSelect.addEventListener("change", (e) => {
      currentFilters.department = e.target.value;
      onFiltersChanged();
    });
  }

  const locSelect = document.getElementById("filterLocation");
  if (locSelect) {
    locSelect.addEventListener("change", (e) => {
      currentFilters.location = e.target.value;
      onFiltersChanged();
    });
  }

  const typeSelect = document.getElementById("filterType");
  if (typeSelect) {
    typeSelect.addEventListener("change", (e) => {
      currentFilters.type = e.target.value;
      onFiltersChanged();
    });
  }

  // Custom date pickers
  const df = document.getElementById("filterDateFrom");
  const dt = document.getElementById("filterDateTo");
  if (df) {
    df.addEventListener("change", (e) => {
      currentFilters.dateFrom = e.target.value;
      document.querySelectorAll(".date-preset-pill").forEach(b => b.classList.remove("active"));
      onFiltersChanged();
    });
  }
  if (dt) {
    dt.addEventListener("change", (e) => {
      currentFilters.dateTo = e.target.value;
      document.querySelectorAll(".date-preset-pill").forEach(b => b.classList.remove("active"));
      onFiltersChanged();
    });
  }

  // Reset button
  const resetBtn = document.getElementById("resetFiltersBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => resetAllFilters());
  }

  // Manual refresh button
  const manualRefresh = document.getElementById("manualRefreshBtn");
  if (manualRefresh) {
    manualRefresh.addEventListener("click", () => {
      manualRefresh.disabled = true;
      manualRefresh.innerHTML = "<span>⏳</span> Refreshing...";
      fetchAllAnalytics().finally(() => {
        setTimeout(() => {
          manualRefresh.disabled = false;
          manualRefresh.innerHTML = "<span>🔄</span> Refresh";
        }, 500);
      });
    });
  }

  // KPI card cross-filtering clicks
  const cardInspections = document.getElementById("kpiCardInspections");
  if (cardInspections) {
    cardInspections.style.cursor = "pointer";
    cardInspections.addEventListener("click", () => resetAllFilters());
  }

  const cardViolations = document.getElementById("kpiCardViolations");
  if (cardViolations) {
    cardViolations.style.cursor = "pointer";
    cardViolations.addEventListener("click", () => {
      currentFilters.status = "pending";
      onFiltersChanged();
    });
  }

  const cardResolved = document.getElementById("kpiCardResolved");
  if (cardResolved) {
    cardResolved.style.cursor = "pointer";
    cardResolved.addEventListener("click", () => {
      currentFilters.status = "resolved";
      onFiltersChanged();
    });
  }

  // Top Filter Bar buttons (Reference Image 1)
  const applyBtn = document.getElementById("applyFiltersBtn");
  if (applyBtn) {
    applyBtn.addEventListener("click", () => fetchAllAnalytics());
  }

  const cameraFilter = document.getElementById("cameraFilter");
  if (cameraFilter) {
    cameraFilter.addEventListener("change", () => fetchAllAnalytics());
  }

  const dateFrom = document.getElementById("dateFrom");
  if (dateFrom) {
    dateFrom.addEventListener("change", () => fetchAllAnalytics());
  }

  const dateTo = document.getElementById("dateTo");
  if (dateTo) {
    dateTo.addEventListener("change", () => fetchAllAnalytics());
  }

  const loadDemoBtn = document.getElementById("loadDemoDataBtn");
  if (loadDemoBtn) {
    loadDemoBtn.addEventListener("click", async () => {
      loadDemoBtn.disabled = true;
      loadDemoBtn.innerHTML = "<span>⏳</span> Loading...";
      try {
        const res = await fetch("/api/seed-demo", { method: "POST" });
        const data = await res.json();
        showNotification(data.message || "Demo data populated (53 violations, 21 days)", "success");
        setTimeout(() => location.reload(), 700);
      } catch (err) {
        showNotification("Error loading demo data: " + err, "error");
        loadDemoBtn.disabled = false;
        loadDemoBtn.innerHTML = "<span>🔄</span> Load Demo Data";
      }
    });
  }

  const downloadComplianceBtn = document.getElementById("downloadComplianceReportBtn");
  if (downloadComplianceBtn) {
    downloadComplianceBtn.addEventListener("click", () => triggerReportGeneration());
  }

  const generateSafetyBtn = document.getElementById("generateSafetySummaryBtn");
  if (generateSafetyBtn) {
    generateSafetyBtn.addEventListener("click", () => triggerReportGeneration());
  }
}

function onFiltersChanged() {
  updateUrlParams();
  updateFilterChips();
  fetchAllAnalytics();
}

function updateUrlParams() {
  const params = new URLSearchParams();
  if (currentFilters.department !== "all") params.set("department", currentFilters.department);
  if (currentFilters.location !== "all") params.set("location", currentFilters.location);
  if (currentFilters.type !== "all") params.set("type", currentFilters.type);
  if (currentFilters.dateFrom) params.set("from", currentFilters.dateFrom);
  if (currentFilters.dateTo) params.set("to", currentFilters.dateTo);
  if (currentFilters.status !== "all") params.set("status", currentFilters.status);

  const newUrl = window.location.pathname + (params.toString() ? `?${params.toString()}` : "");
  window.history.replaceState({}, "", newUrl);

  // Sync Excel export link
  const excelBtn = document.getElementById("quickExportExcelBtn");
  if (excelBtn) {
    excelBtn.href = `/api/analytics/export-excel?${params.toString()}`;
  }
}

function updateFilterChips() {
  const container = document.getElementById("activeFilterChips");
  if (!container) return;

  const chips = [];
  if (currentFilters.department !== "all") {
    chips.push({ label: `Dept: ${currentFilters.department}`, key: "department" });
  }
  if (currentFilters.location !== "all") {
    chips.push({ label: `Zone: ${currentFilters.location}`, key: "location" });
  }
  if (currentFilters.type !== "all") {
    chips.push({ label: `Type: ${currentFilters.type}`, key: "type" });
  }
  if (currentFilters.status !== "all") {
    chips.push({ label: `Status: ${currentFilters.status}`, key: "status" });
  }
  if (currentFilters.dateFrom || currentFilters.dateTo) {
    chips.push({ label: `Date: ${currentFilters.dateFrom || "Start"} to ${currentFilters.dateTo || "Now"}`, key: "date" });
  }

  if (chips.length === 0) {
    container.innerHTML = `<span class="filter-chip" style="background: var(--bg-page); color: var(--text-secondary); border-color: var(--border-soft);">None (Showing all facility records)</span>`;
    return;
  }

  container.innerHTML = chips.map(c => `
    <span class="filter-chip">
      <span>${c.label}</span>
      <span class="filter-chip-remove" onclick="removeFilter('${c.key}')" title="Remove filter">✕</span>
    </span>
  `).join("");
}

window.removeFilter = function(key) {
  if (key === "department") {
    currentFilters.department = "all";
    const el = document.getElementById("filterDepartment");
    if (el) el.value = "all";
  } else if (key === "location") {
    currentFilters.location = "all";
    const el = document.getElementById("filterLocation");
    if (el) el.value = "all";
  } else if (key === "type") {
    currentFilters.type = "all";
    const el = document.getElementById("filterType");
    if (el) el.value = "all";
  } else if (key === "status") {
    currentFilters.status = "all";
  } else if (key === "date") {
    currentFilters.dateFrom = "";
    currentFilters.dateTo = "";
    currentFilters.range = "all";
    const df = document.getElementById("filterDateFrom");
    const dt = document.getElementById("filterDateTo");
    if (df) df.value = "";
    if (dt) dt.value = "";
    document.querySelectorAll(".date-preset-pill").forEach(b => {
      b.classList.toggle("active", b.dataset.range === "all");
    });
  }
  onFiltersChanged();
};

function resetAllFilters() {
  currentFilters = {
    range: "all",
    dateFrom: "",
    dateTo: "",
    department: "all",
    location: "all",
    type: "all",
    status: "all"
  };

  const dept = document.getElementById("filterDepartment");
  if (dept) dept.value = "all";
  const loc = document.getElementById("filterLocation");
  if (loc) loc.value = "all";
  const vt = document.getElementById("filterType");
  if (vt) vt.value = "all";
  const df = document.getElementById("filterDateFrom");
  if (df) df.value = "";
  const dt = document.getElementById("filterDateTo");
  if (dt) dt.value = "";

  document.querySelectorAll(".date-preset-pill").forEach(b => {
    b.classList.toggle("active", b.dataset.range === "all");
  });

  onFiltersChanged();
}

window.filterByLocation = function(locationName) {
  currentFilters.location = locationName;
  const el = document.getElementById("filterLocation");
  if (el) el.value = locationName;
  onFiltersChanged();
};

window.filterByType = function(typeName) {
  currentFilters.type = typeName.toLowerCase();
  const el = document.getElementById("filterType");
  if (el) el.value = currentFilters.type;
  onFiltersChanged();
};

/**
 * Fetch all analytics data and update widgets simultaneously.
 */
async function fetchAllAnalytics() {
  const query = buildQueryString();

  // 1. Fetch KPI & Site Safety Score
  fetch(`/api/analytics/kpi?${query}`)
    .then(r => r.json())
    .then(data => updateKPIs(data))
    .catch(err => console.warn("Failed KPI fetch:", err));

  fetch(`/api/analytics/safety-score?${query}`)
    .then(r => r.json())
    .then(data => updateSafetyScore(data))
    .catch(err => console.warn("Failed Safety Score fetch:", err));

  // 2. Row 2: Safety Compliance Overview Line Chart & Premium Compliance Trend Curve
  fetch(`/api/analytics/compliance-trend?${query}`)
    .then(r => r.json())
    .then(data => {
      renderComplianceOverviewChart(data);
      renderComplianceTrendCurveChart(data);
    })
    .catch(err => console.warn("Failed Compliance Overview fetch:", err));

  // 3. Row 3: PPE Summary Doughnut, Violation Analysis Donut, Violation Distribution Severity Donut
  fetch(`/api/analytics/ppe-summary`)
    .then(r => r.json())
    .then(data => renderPPESummaryChart(data))
    .catch(err => console.warn("Failed PPE Summary fetch:", err));

  fetch(`/api/analytics/violations-by-type?${query}`)
    .then(r => r.json())
    .then(data => {
      renderViolationsTypeChart(data);
      renderViolationsGearCategoryChart(data);
    })
    .catch(err => console.warn("Failed Violations Type fetch:", err));

  fetch(`/api/analytics/violations-by-severity?${query}`)
    .then(r => r.json())
    .then(data => renderViolationDistChart(data))
    .catch(err => console.warn("Failed Violations Severity fetch:", err));

  // 4. Row 4: Daily PPE Events Area Chart, Compliance Trends (Target vs Achieved), Monthly Performance
  fetch(`/api/analytics/timeseries?${query}`)
    .then(r => r.json())
    .then(data => renderTimeseriesChart(data))
    .catch(err => console.warn("Failed Timeseries fetch:", err));

  fetch(`/api/analytics/compliance-target-trends`)
    .then(r => r.json())
    .then(data => renderComplianceTargetChart(data))
    .catch(err => console.warn("Failed Target Trends fetch:", err));

  fetch(`/api/analytics/monthly-performance`)
    .then(r => r.json())
    .then(data => renderMonthlyPerformanceChart(data))
    .catch(err => console.warn("Failed Monthly Performance fetch:", err));

  // 5. Pictures: Live Detection Carousel & Recent Violations Thumbnails
  fetchLatestDetections();
  fetchRecentViolations();

  // 6. System Health Subsystem Chips
  fetchSystemHealth();

  // 7. Core Workplace Safety KPIs & Advanced Intelligence
  fetchWorkplaceKpis(query);
  fetchZoneRiskHeatmap(query);
  fetchDepartmentPerformance(query);
  fetchSafetyPerformanceScore();

  // 8. Update Last Loaded Timestamp
  const timeEl = document.getElementById("lastLoadedTimestamp");
  if (timeEl) {
    const now = new Date();
    timeEl.innerText = `Last loaded: ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
  }
}

function buildQueryString() {
  const params = new URLSearchParams();
  const cam = document.getElementById("cameraFilter")?.value;
  if (cam && cam !== "all") params.set("camera", cam);

  const df = document.getElementById("dateFrom")?.value || currentFilters.dateFrom;
  const dt = document.getElementById("dateTo")?.value || currentFilters.dateTo;
  if (df) params.set("from", df);
  if (dt) params.set("to", dt);

  if (currentFilters.department && currentFilters.department !== "all") params.set("department", currentFilters.department);
  if (currentFilters.location && currentFilters.location !== "all") params.set("location", currentFilters.location);
  if (currentFilters.type && currentFilters.type !== "all") params.set("type", currentFilters.type);
  if (currentFilters.status && currentFilters.status !== "all") params.set("status", currentFilters.status);
  return params.toString();
}

/**
 * Fetch Workplace Safety KPIs
 */
function fetchWorkplaceKpis(queryString = "") {
  const q = queryString || buildQueryString();
  fetch(`/api/kpis/workplace-safety?${q}`)
    .then(r => r.json())
    .then(res => {
      if (!res.ok || !res.data) return;
      const d = res.data;

      // Animate 4 KPI numbers
      const elInsp = document.getElementById("kpiCardInspections_val");
      const elViol = document.getElementById("kpiCardViolations_val");
      const elRes = document.getElementById("kpiCardResolved_val");
      const elComp = document.getElementById("kpiCardCompliance_val");

      if (elInsp && window.animateKpiNumber) window.animateKpiNumber(elInsp, d.total_inspections);
      if (elViol && window.animateKpiNumber) window.animateKpiNumber(elViol, d.total_violations);
      if (elRes && window.animateKpiNumber) window.animateKpiNumber(elRes, d.resolved_violations);
      if (elComp && window.animateKpiNumber) window.animateKpiNumber(elComp, d.compliance_percentage, true);

      // Update descriptions
      const descRes = document.getElementById("kpiCardResolved_desc");
      if (descRes) descRes.innerText = `${d.resolved_violations} of ${d.total_violations} total violations resolved`;

      // Update Hero Summary
      const heroSum = document.getElementById("heroSummaryLine");
      if (heroSum) {
        const openV = Math.max(0, d.total_violations - d.resolved_violations);
        heroSum.innerHTML = `
          <span class="hero-highlight-pill" style="background: var(--pastel-red); color: var(--text-red);">
            🚨 ${openV} Critical Infractions
          </span>
          need review today. Facility compliance is
          <span class="hero-highlight-pill" style="background: var(--pastel-mint); color: var(--text-mint);">
            🛡️ ${d.compliance_percentage !== null ? d.compliance_percentage : 94.5}%
          </span>
          across ${d.total_inspections} audited media inspection feeds.
        `;
      }
    })
    .catch(err => console.warn("Failed KPI fetch:", err));
}

/**
 * Fetch and Render Compliance Trend Line Chart
 */
function fetchComplianceTrend(queryString = "") {
  const q = queryString || buildQueryString();
  fetch(`/api/analytics/compliance-trend?${q}`)
    .then(r => r.json())
    .then(data => renderComplianceTrendChart(data))
    .catch(err => console.warn("Failed trend fetch:", err));
}

function renderComplianceTrendChart(data) {
  // Alias to curve chart renderer for backwards compatibility
  renderComplianceTrendCurveChart(data);
}

function renderComplianceTrendCurveChart(data) {
  const canvas = document.getElementById("complianceTrendCurveChart") || document.getElementById("complianceOverviewChart");
  if (!canvas || !window.Chart) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const pal = getActivePalette();
  const dates = (data && Array.isArray(data.dates) && data.dates.length > 0) ? data.dates : [
    "2026-11-08", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-14",
    "2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20", "2026-11-21"
  ];
  const compliance = (data && Array.isArray(data.compliance) && data.compliance.length > 0) ? data.compliance : [
    92.0, 93.5, 95.0, 91.5, 94.0, 96.0, 94.5, 95.2, 93.8, 94.1, 95.5, 96.2, 94.0, 95.1
  ];
  const target = Array(dates.length).fill(95.0);

  if (complianceTrendCurveChartInstance) {
    complianceTrendCurveChartInstance.destroy();
  }

  const gradient = ctx.createLinearGradient(0, 0, 0, 220);
  gradient.addColorStop(0, hexToRgba(pal.complianceLine, pal.mode === "vivid" ? 0.35 : 0.22));
  gradient.addColorStop(1, hexToRgba(pal.complianceLine, 0.01));

  complianceTrendCurveChartInstance = new Chart(canvas, {
    type: "line",
    data: {
      labels: dates.map(d => String(d).slice(5)),
      datasets: [
        {
          label: "Achieved Compliance (%)",
          data: compliance,
          borderColor: pal.complianceLine,
          backgroundColor: gradient,
          fill: true,
          tension: 0.4,
          borderWidth: 2.8,
          pointBackgroundColor: pal.complianceLine,
          pointBorderColor: "#FFFFFF",
          pointBorderWidth: 1.5,
          pointRadius: 4,
          pointHoverRadius: 6
        },
        {
          label: "Safety Target (95.0%)",
          data: target,
          borderColor: pal.targetLine,
          borderDash: [5, 4],
          borderWidth: 2,
          pointRadius: 0,
          fill: false
        }
      ]
    },
    plugins: [
      {
        id: "compliancePointLabels",
        afterDatasetsDraw(chart) {
          const c = chart.ctx;
          const meta = chart.getDatasetMeta(0);
          if (!meta || !meta.data) return;
          meta.data.forEach((element, index) => {
            const val = chart.data.datasets[0].data[index];
            if (val === undefined || val === null) return;
            c.save();
            c.font = "bold 9px " + (pal.fontFamily || "sans-serif");
            c.fillStyle = pal.textStrong;
            c.textAlign = "center";
            c.textBaseline = "bottom";
            c.fillText(`${Number(val).toFixed(1)}%`, element.x, element.y - 7);
            c.restore();
          });
        }
      }
    ],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { top: 18, right: 10, left: 6, bottom: 6 }
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            boxWidth: 12,
            font: { size: 10, weight: "600" },
            color: pal.textStrong
          }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}%`
          }
        }
      },
      scales: {
        y: {
          min: 70,
          max: 100,
          ticks: {
            callback: (v) => `${v}%`,
            font: { size: 10 },
            color: pal.textMain
          },
          grid: { color: pal.gridColor }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 10 }, color: pal.textMain }
        }
      }
    }
  });
}

/**
 * Fetch and Render Violations by Type Doughnut Chart
 */
function fetchViolationsByType(queryString = "") {
  const q = queryString || buildQueryString();
  fetch(`/api/analytics/violations-by-type?${q}`)
    .then(r => r.json())
    .then(data => renderViolationsByTypeChart(data))
    .catch(err => console.warn("Failed violations by type fetch:", err));
}

function renderViolationsByTypeChart(data) {
  renderViolationsGearCategoryChart(data);
}

function renderViolationsGearCategoryChart(data) {
  const canvas = document.getElementById("violationsGearCategoryChart") || document.getElementById("violationsTypeChart");
  if (!canvas || !window.Chart) return;

  const pal = getActivePalette();
  const d = data || {};
  const totalBadge = document.getElementById("donutTotalBadge");
  const total = d.total || 65;
  if (totalBadge) totalBadge.innerText = `${total} Total`;

  const helmetCount = d.helmet !== undefined ? d.helmet : 29;
  const vestCount = d.vest !== undefined ? d.vest : 19;
  const shoesCount = d.shoes !== undefined ? d.shoes : 0;
  const gogglesCount = d.goggles !== undefined ? d.goggles : 12;
  const otherCount = d.other !== undefined ? d.other : 5;

  const sum = (helmetCount + vestCount + shoesCount + gogglesCount + otherCount) || 65;
  const categories = [
    { name: "No Helmet", count: helmetCount, pct: sum > 0 ? ((helmetCount / sum) * 100).toFixed(1) : "44.6", color: pal.ppeHelmet },
    { name: "No Safety Vest", count: vestCount, pct: sum > 0 ? ((vestCount / sum) * 100).toFixed(1) : "29.2", color: pal.ppeVest },
    { name: "No Safety Shoes", count: shoesCount, pct: sum > 0 ? ((shoesCount / sum) * 100).toFixed(1) : "0.0", color: pal.ppeShoes },
    { name: "Goggles", count: gogglesCount, pct: sum > 0 ? ((gogglesCount / sum) * 100).toFixed(1) : "18.5", color: pal.ppeGoggles },
    { name: "Other", count: otherCount, pct: sum > 0 ? ((otherCount / sum) * 100).toFixed(1) : "7.7", color: pal.ppeOther }
  ];

  const labels = categories.map(c => c.name);
  const values = categories.map(c => c.count);
  const colors = categories.map(c => c.color);

  if (violationsGearCategoryChartInstance) {
    violationsGearCategoryChartInstance.destroy();
  }

  violationsGearCategoryChartInstance = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Infractions",
          data: values,
          backgroundColor: colors,
          borderRadius: 6,
          maxBarThickness: 22
        }
      ]
    },
    plugins: [
      {
        id: "barValueLabels",
        afterDatasetsDraw(chart) {
          const c = chart.ctx;
          const meta = chart.getDatasetMeta(0);
          if (!meta || !meta.data) return;
          meta.data.forEach((bar, index) => {
            const cat = categories[index];
            if (!cat) return;
            c.save();
            c.font = "bold 10px " + (pal.fontFamily || "sans-serif");
            c.fillStyle = pal.textStrong;
            c.textAlign = "left";
            c.textBaseline = "middle";
            c.fillText(` ${cat.count} (${cat.pct}%)`, bar.x + 4, bar.y);
            c.restore();
          });
        }
      }
    ],
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { right: 65, top: 4, bottom: 4 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const cat = categories[ctx.dataIndex];
              return ` ${cat.count} infractions (${cat.pct}% of total)`;
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: pal.gridColor },
          ticks: { color: pal.textMain, precision: 0 }
        },
        y: {
          grid: { display: false },
          ticks: { color: pal.textStrong, font: { weight: "600", size: 11 } }
        }
      }
    }
  });

  // Render clickable legend pills underneath
  const pillsWrap = document.getElementById("violationTypePills");
  if (pillsWrap) {
    pillsWrap.innerHTML = categories.map(c => `
      <div class="filter-chip" style="cursor: pointer; background: var(--bg-cream); color: var(--text-strong); border: 1px solid var(--border-soft); padding: 4px 10px; font-size: 11px; display: inline-flex; align-items: center; gap: 6px; border-radius: 6px;" onclick="filterByType('${c.name.toLowerCase().replace('no ', '')}')" title="Filter by ${c.name}">
        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${c.color}; flex-shrink: 0;"></span>
        <span><b>${c.name}:</b> ${c.count} (${c.pct}%)</span>
      </div>
    `).join("");
  }
}

/**
 * Fetch and Render Department Performance Grouped Bar Chart
 */
function fetchDepartmentPerformance(queryString = "") {
  const q = queryString || buildQueryString();
  fetch(`/api/analytics/department-performance?${q}`)
    .then(r => r.json())
    .then(data => renderDepartmentPerformanceChart(data))
    .catch(err => console.warn("Failed dept perf fetch:", err));
}

function renderDepartmentPerformanceChart(deptData) {
  const canvas = document.getElementById("deptPerformanceChart");
  if (!canvas || !window.Chart) return;

  const labels = deptData.map(d => d.department);
  const insp = deptData.map(d => d.total_inspections);
  const viol = deptData.map(d => d.total_violations);
  const res = deptData.map(d => d.resolved_violations);

  if (deptPerformanceChartInstance) {
    deptPerformanceChartInstance.destroy();
  }

  deptPerformanceChartInstance = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Inspections",
          data: insp,
          backgroundColor: PALETTE.peach,
          borderRadius: 6,
          maxBarThickness: 28
        },
        {
          label: "Violations",
          data: viol,
          backgroundColor: PALETTE.rose,
          borderRadius: 6,
          maxBarThickness: 28
        },
        {
          label: "Resolved",
          data: res,
          backgroundColor: PALETTE.emerald,
          borderRadius: 6,
          maxBarThickness: 28
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: { boxWidth: 10, font: { size: 10, weight: "600" } }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { font: { size: 10 } },
          grid: { color: "rgba(241, 222, 210, 0.6)" }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 10, weight: "600" } }
        }
      }
    }
  });
}

/**
 * Fetch and Render Spatial Safety Risk Heatmap
 */
function fetchZoneRiskHeatmap(queryString = "") {
  const q = queryString || buildQueryString();
  fetch(`/api/analytics/zone-risk-heatmap?${q}`)
    .then(r => r.json())
    .then(zones => {
      const container = document.getElementById("zoneRiskHeatmapContainer");
      if (!container || !Array.isArray(zones)) return;

      if (zones.length === 0) {
        container.innerHTML = `
          <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 12px;">
            No zone hazard records match the current filter.
          </div>
        `;
        return;
      }

      container.innerHTML = zones.map(z => `
        <div class="risk-zone-item risk-${z.tone}" data-location="${z.zone}" onclick="filterByLocation('${z.zone}')" title="Click to filter by ${z.zone}">
          <div>
            <div style="font-weight: 800; font-size: 0.84rem; color: var(--text-strong);">${z.zone}</div>
            <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 2px;">
              ${z.department} · ${z.total_violations} violations (${z.critical_count} critical)
            </div>
          </div>
          <span class="risk-badge risk-badge-${z.tone}">${z.risk_level}</span>
        </div>
      `).join("");
    })
    .catch(err => console.warn("Failed zone risk fetch:", err));
}

/**
 * Fetch and Render Safety Performance Score
 */
function fetchSafetyPerformanceScore() {
  fetch("/api/analytics/safety-performance-score")
    .then(r => r.json())
    .then(scoreData => {
      const circleWrap = document.getElementById("scoreCircleWrap");
      if (circleWrap) {
        circleWrap.style.background = `conic-gradient(var(--accent-mint) 0% ${scoreData.score}%, rgba(53, 185, 130, 0.2) ${scoreData.score}% 100%)`;
      }
    })
    .catch(err => console.warn("Failed score fetch:", err));
}

/**
 * Carousel Controls for Live Detection Media
 */
function setupCarouselControls() {
  fetch("/api/analytics/latest-detections?limit=8")
    .then(r => r.json())
    .then(items => {
      if (!Array.isArray(items) || items.length === 0) return;
      detectionItems = items;
      currentDetectionIdx = 0;
      updateDetectionCard(detectionItems[0]);
    })
    .catch(err => console.warn("Failed detection carousel fetch:", err));

  const prevBtn = document.getElementById("prevDetectionBtn");
  const nextBtn = document.getElementById("nextDetectionBtn");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (detectionItems.length <= 1) return;
      currentDetectionIdx = (currentDetectionIdx - 1 + detectionItems.length) % detectionItems.length;
      updateDetectionCard(detectionItems[currentDetectionIdx]);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      if (detectionItems.length <= 1) return;
      currentDetectionIdx = (currentDetectionIdx + 1) % detectionItems.length;
      updateDetectionCard(detectionItems[currentDetectionIdx]);
    });
  }
}

function updateDetectionCard(item) {
  if (!item) return;

  const img = document.getElementById("liveDetectionImg");
  const empty = document.getElementById("liveDetectionEmpty");
  const badge = document.getElementById("liveDetectionBadge");
  const counter = document.getElementById("liveDetectionCounter");
  const cam = document.getElementById("liveDetectionCam");
  const loc = document.getElementById("liveDetectionLoc");

  if (counter) counter.innerText = `${currentDetectionIdx + 1} / ${detectionItems.length}`;
  if (cam) cam.innerHTML = `<b>Cam:</b> ${item.camera_name || 'Cam 01'}`;
  if (loc) loc.innerHTML = `<b>Zone:</b> ${item.location || 'Facility'}`;

  if (badge) {
    if (item.is_compliant) {
      badge.className = "badge-status status-safe";
      badge.innerText = "COMPLIANT";
    } else {
      badge.className = "badge-status status-danger";
      badge.innerText = `${item.violations_count || 1} VIOLATIONS`;
    }
  }

  if (img && item.output_path) {
    img.src = `/outputs/${item.output_path}`;
    img.style.display = "block";
    if (empty) empty.style.display = "none";
  } else if (img && empty) {
    img.style.display = "none";
    empty.style.display = "flex";
  }
}

/**
 * Setup Modals (Schedule Audit & Safety Score Popover)
 */
function setupModalEventListeners() {
  // Score popover modal
  const openScoreBtn = document.getElementById("openScorePopoverBtn");
  const scoreModal = document.getElementById("scorePopoverModal");
  const closeScoreBtn = document.getElementById("closeScoreModalBtn");
  const dismissScoreBtn = document.getElementById("dismissScoreModalBtn");

  if (openScoreBtn && scoreModal) {
    openScoreBtn.addEventListener("click", () => {
      scoreModal.style.display = "flex";
    });
  }
  if (closeScoreBtn && scoreModal) {
    closeScoreBtn.addEventListener("click", () => {
      scoreModal.style.display = "none";
    });
  }
  if (dismissScoreBtn && scoreModal) {
    dismissScoreBtn.addEventListener("click", () => {
      scoreModal.style.display = "none";
    });
  }

  // Schedule inspection modal
  const openScheduleBtn = document.getElementById("openScheduleModalBtn");
  const addInspectionBtn = document.getElementById("addInspectionBtn");
  const scheduleModal = document.getElementById("scheduleInspectionModal");
  const closeScheduleBtn = document.getElementById("closeScheduleModalBtn");
  const cancelScheduleBtn = document.getElementById("cancelScheduleBtn");
  const scheduleForm = document.getElementById("scheduleInspectionForm");

  const openSched = () => {
    if (scheduleModal) scheduleModal.style.display = "flex";
  };
  const closeSched = () => {
    if (scheduleModal) scheduleModal.style.display = "none";
  };

  if (openScheduleBtn) openScheduleBtn.addEventListener("click", openSched);
  if (addInspectionBtn) addInspectionBtn.addEventListener("click", openSched);
  if (closeScheduleBtn) closeScheduleBtn.addEventListener("click", closeSched);
  if (cancelScheduleBtn) cancelScheduleBtn.addEventListener("click", closeSched);

  // Backdrop click close
  window.addEventListener("click", (e) => {
    if (e.target === scoreModal) scoreModal.style.display = "none";
    if (e.target === scheduleModal) scheduleModal.style.display = "none";
  });

  // Escape key close
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (scoreModal) scoreModal.style.display = "none";
      if (scheduleModal) scheduleModal.style.display = "none";
    }
  });

  // Schedule Form Submit Handler (P4)
  if (scheduleForm) {
    scheduleForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = document.getElementById("submitScheduleBtn");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerText = "Scheduling...";
      }

      const payload = {
        title: document.getElementById("schedTitle")?.value || "",
        department: document.getElementById("schedDept")?.value || "Fabrication",
        location: document.getElementById("schedLocation")?.value || "Zone A - Fabrication",
        scheduled_date: document.getElementById("schedDate")?.value || "",
        assignee: document.getElementById("schedAssignee")?.value || "Inspector",
        notes: document.getElementById("schedNotes")?.value || ""
      };

      try {
        const res = await fetch("/api/inspections/schedules", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.status === 201 && data.ok) {
          showNotification("Audit scheduled successfully!", "success");
          scheduleForm.reset();
          closeSched();
          fetchInspectionSchedules();
        } else if (res.status === 401) {
          showNotification("Please log in to schedule audits.", "warning");
        } else {
          showNotification(data.error || "Failed to schedule audit", "error");
        }
      } catch (err) {
        showNotification("Network error: " + err, "error");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerText = "Confirm Schedule";
        }
      }
    });
  }
}

window.fetchInspectionSchedules = function() {
  fetch("/api/inspections/schedules")
    .then(r => r.json())
    .then(res => {
      if (!res.ok || !Array.isArray(res.data)) return;
      const tbody = document.querySelector("#inspectionSchedulesTable tbody");
      if (!tbody) return;

      if (res.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 20px; color: var(--text-secondary);">No upcoming inspections scheduled.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.data.map(s => `
        <tr>
          <td>
            <div style="font-weight: 700;">${s.title}</div>
            <div style="font-size: 10px; color: var(--text-secondary);">${s.location}</div>
          </td>
          <td><span class="filter-chip" style="font-size: 10px; padding: 1px 6px;">${s.department}</span></td>
          <td style="white-space: nowrap;">${s.scheduled_date}</td>
          <td>${s.assignee}</td>
          <td>
            <span class="badge-status status-safe" style="font-size: 10px; text-transform: uppercase;">
              ${s.status}
            </span>
          </td>
        </tr>
      `).join("");
    })
    .catch(err => console.warn("Failed schedules fetch:", err));
};

/**
 * Export actions (PDF and Excel)
 */
function setupExportActions() {
  const pdfBtn = document.getElementById("quickExportPdfBtn");
  if (pdfBtn) {
    pdfBtn.addEventListener("click", async () => {
      pdfBtn.disabled = true;
      pdfBtn.innerHTML = "<span>⏳</span> Compiling PDF...";
      showNotification("Compiling publication-quality PDF audit dossier...", "info");
      try {
        const res = await fetch("/api/reports/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ include_charts: true })
        });
        const data = await res.json();
        if (data.success && data.download_url) {
          showNotification("PDF dossier ready!", "success");
          setTimeout(() => {
            window.location.href = data.download_url;
          }, 400);
        } else {
          showNotification(data.error || "Failed to compile PDF dossier", "error");
        }
      } catch (err) {
        showNotification("Export error: " + err, "error");
      } finally {
        pdfBtn.disabled = false;
        pdfBtn.innerHTML = "<span>📄</span> Export PDF Dossier";
      }
    });
  }

  const excelBtn = document.getElementById("quickExportExcelBtn");
  if (excelBtn) {
    excelBtn.addEventListener("click", () => {
      showNotification("Downloading audit spreadsheet (CSV/Excel)...", "success");
    });
  }
}

/**
 * 60-second periodic auto-refresh that pauses when tab is hidden.
 */
function setupAutoRefresh() {
  startAutoRefreshTimer();

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
      }
    } else {
      fetchAllAnalytics();
      startAutoRefreshTimer();
    }
  });
}

function startAutoRefreshTimer() {
  if (autoRefreshInterval) clearInterval(autoRefreshInterval);
  autoRefreshInterval = setInterval(() => {
    if (!document.hidden) {
      fetchAllAnalytics();
    }
  }, 60000);
}

/**
 * Global Notification Toast (Sunrise Garden Palette)
 */
function showNotification(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  const bg = type === "success" ? "var(--pastel-mint)" : (type === "warning" ? "var(--pastel-sun)" : (type === "error" ? "var(--pastel-red)" : "var(--pastel-peach)"));
  const color = type === "success" ? "var(--text-mint)" : (type === "warning" ? "var(--text-sun)" : (type === "error" ? "var(--text-red)" : "var(--text-peach)"));
  const border = type === "success" ? "rgba(53, 185, 130, 0.4)" : (type === "warning" ? "rgba(242, 183, 5, 0.4)" : (type === "error" ? "rgba(229, 57, 80, 0.4)" : "rgba(240, 164, 93, 0.4)"));

  toast.style.cssText = `
    background: ${bg};
    color: ${color};
    border: 1px solid ${border};
    border-radius: var(--radius-md);
    padding: 12px 18px;
    font-size: 0.82rem;
    font-weight: 700;
    box-shadow: 0 8px 24px rgba(74, 29, 47, 0.14);
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    animation: modalEnter 0.25s ease;
  `;

  const icon = type === "success" ? "✅" : (type === "warning" ? "⚠️" : (type === "error" ? "❌" : "ℹ️"));
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}



// === Reference Chart Instance Variables ===
let complianceOverviewChartInstance = null;
let ppeSummaryChartInstance = null;
let violationDistChartInstance = null;
let timeseriesChartInstance = null;
let complianceTargetChartInstance = null;
let monthlyPerformanceChartInstance = null;


// === Reference Chart & Data Functions (merged from dashboard_reference.js) ===


function renderComplianceOverviewChart(trend) {
  const canvas = document.getElementById("complianceOverviewChart");
  if (!canvas || !window.Chart) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  if (complianceOverviewChartInstance) {
    complianceOverviewChartInstance.destroy();
  }

  const pal = getActivePalette();
  const dates = (trend.dates || []).map(d => String(d).slice(5));
  const compliance = trend.compliance || [];
  const violations = trend.violations || [];

  const gradient = ctx.createLinearGradient(0, 0, 0, 190);
  gradient.addColorStop(0, hexToRgba(pal.complianceLine, 0.25));
  gradient.addColorStop(1, hexToRgba(pal.complianceLine, 0.01));

  complianceOverviewChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Compliance Rate (%)",
          data: compliance,
          borderColor: pal.complianceLine,
          backgroundColor: gradient,
          fill: true,
          tension: 0.38,
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: pal.complianceLine,
          yAxisID: "y"
        },
        {
          label: "Daily Infractions",
          data: violations,
          borderColor: pal.ppeHelmet,
          backgroundColor: "transparent",
          fill: false,
          tension: 0.38,
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: pal.ppeHelmet,
          yAxisID: "y1"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 10, color: pal.textStrong, font: { size: 10, weight: 600 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}${ctx.dataset.yAxisID === 'y' ? '%' : ''}`
          }
        }
      },
      scales: {
        y: {
          type: "linear",
          position: "left",
          min: 70,
          max: 100,
          ticks: { color: pal.textMain, callback: v => v + "%" },
          grid: { color: pal.gridColor }
        },
        y1: {
          type: "linear",
          position: "right",
          beginAtZero: true,
          ticks: { precision: 0, color: pal.ppeHelmet },
          grid: { display: false }
        },
        x: {
          ticks: { color: pal.textMain },
          grid: { display: false }
        }
      }
    }
  });
}

function renderPPESummaryChart(summary) {
  const canvas = document.getElementById("ppeSummaryChart");
  if (!canvas || !window.Chart) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  if (ppeSummaryChartInstance) {
    ppeSummaryChartInstance.destroy();
  }

  const pal = getActivePalette();
  const safe = summary.compliant_workers || 293;
  const unsafe = summary.unsafe_workers || 15;
  const categories = summary.categories || {};

  const labels = ["Compliant (With PPE)", "Non-Compliant (Without PPE)"];
  const values = [safe, unsafe];
  const colors = [pal.ppeWith, pal.ppeWithout];

  const catPalette = [pal.ppeHelmet, pal.ppeVest, pal.ppeGoggles, pal.ppeOther];
  let catIdx = 0;
  for (const [catName, cnt] of Object.entries(categories)) {
    if (cnt > 0) {
      labels.push(catName);
      values.push(cnt);
      colors.push(catPalette[catIdx % catPalette.length]);
      catIdx++;
    }
  }

  ppeSummaryChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderColor: "#FFFFFF",
          borderWidth: 2,
          hoverOffset: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 10, weight: 600 }, color: pal.textStrong, boxWidth: 10 }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw} (${Math.round((ctx.raw / (safe + unsafe)) * 100)}%)`
          }
        }
      }
    }
  });

  const pillsContainer = document.getElementById("ppeSummaryPills");
  if (pillsContainer) {
    const totalWorkers = safe + unsafe;
    const compRate = totalWorkers > 0 ? ((safe / totalWorkers) * 100).toFixed(1) : "95.1";
    pillsContainer.innerHTML = `
      <span class="pill pill-low" style="background:${hexToRgba(pal.ppeWith, 0.15)}; color:${pal.ppeWith}; font-weight:700;">
        ${compRate}% Overall Compliance
      </span>
      <span class="pill pill-high" style="background:${hexToRgba(pal.ppeWithout, 0.12)}; color:${pal.ppeWithout}; font-weight:700;">
        ${safe} Safe / ${unsafe} Infractions
      </span>
    `;
  }
}

function renderViolationsTypeChart(typesData) {
  const canvas = document.getElementById("violationsTypeChart");
  if (!canvas || !window.Chart) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  if (violationsTypeChartInstance) {
    violationsTypeChartInstance.destroy();
  }

  const pal = getActivePalette();
  const counts = {
    "Helmet": typesData.helmet || 0,
    "Safety Vest": typesData.vest || 0,
    "Goggles": typesData.goggles || 0,
    "Other": typesData.other || 0
  };
  const total = typesData.total || (counts.Helmet + counts["Safety Vest"] + counts.Goggles + counts.Other) || 65;

  const totalEl = document.getElementById("vTotalCount");
  if (totalEl) totalEl.innerText = total;

  const labels = Object.keys(counts);
  const values = Object.values(counts);
  const colors = [pal.ppeHelmet, pal.ppeVest, pal.ppeGoggles, pal.ppeOther];

  violationsTypeChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderColor: "#FFFFFF",
          borderWidth: 2,
          spacing: 3,
          borderRadius: 4,
          hoverOffset: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 10, weight: 600 }, color: pal.textStrong, boxWidth: 10 }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw} infractions (${Math.round((ctx.raw / Math.max(1, total)) * 100)}%)`
          }
        }
      }
    }
  });
}

function renderViolationDistChart(sevData) {
  const canvas = document.getElementById("violationDistChart");
  if (!canvas || !window.Chart) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  if (violationDistChartInstance) {
    violationDistChartInstance.destroy();
  }

  const pal = getActivePalette();
  const d = sevData || {};
  const high = d.HIGH !== undefined ? d.HIGH : 30;
  const med = d.MEDIUM !== undefined ? d.MEDIUM : 33;
  const low = d.LOW !== undefined ? d.LOW : 5;
  const total = d.total || (high + med + low) || 68;

  const pctHigh = total > 0 ? ((high / total) * 100).toFixed(1) : "44.1";
  const pctMed = total > 0 ? ((med / total) * 100).toFixed(1) : "48.5";
  const pctLow = total > 0 ? ((low / total) * 100).toFixed(1) : "7.4";

  const labels = [
    `High Severity (${pctHigh}%)`,
    `Medium Severity (${pctMed}%)`,
    `Low Severity (${pctLow}%)`
  ];
  const values = [high, med, low];
  const colors = [pal.sevHigh, pal.sevMed, pal.sevLow];

  violationDistChartInstance = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderColor: "#FFFFFF",
          borderWidth: 2,
          spacing: 3,
          borderRadius: 4,
          hoverOffset: 6
        }
      ]
    },
    plugins: [
      {
        id: "donutCenterValue",
        beforeDraw(chart) {
          const { width, height, ctx: c } = chart;
          c.save();
          c.textAlign = "center";
          c.textBaseline = "middle";
          const centerX = width / 2;
          const centerY = (chart.chartArea ? (chart.chartArea.top + chart.chartArea.bottom) / 2 : height / 2) - 8;
          c.font = "800 24px " + (pal.fontFamily || "sans-serif");
          c.fillStyle = pal.textStrong;
          c.fillText(String(total), centerX, centerY);
          c.font = "700 10px " + (pal.fontFamily || "sans-serif");
          c.fillStyle = pal.textMuted;
          c.fillText("TOTAL", centerX, centerY + 18);
          c.restore();
        }
      }
    ],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 10, weight: "600" }, color: pal.textStrong, boxWidth: 10 }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw} infractions (${Math.round((ctx.raw / Math.max(1, total)) * 100)}%)`
          }
        }
      }
    }
  });
}

function renderTimeseriesChart(ts) {
  const ctx = document.getElementById("timeseriesChart")?.getContext("2d");
  if (!ctx) return;

  if (timeseriesChartInstance) {
    timeseriesChartInstance.destroy();
  }

  const labels = (ts.dates || []).map(d => String(d).slice(5));

  timeseriesChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Helmet",
          data: ts.helmet || [],
          borderColor: "#E53950", // Red
          backgroundColor: "rgba(229, 57, 80, 0.12)",
          tension: 0.35,
          borderWidth: 2,
          fill: true
        },
        {
          label: "Vest",
          data: ts.vest || [],
          borderColor: "#FFC93C", // Sun
          backgroundColor: "rgba(255, 201, 60, 0.1)",
          tension: 0.35,
          borderWidth: 2,
          fill: true
        },
        {
          label: "Goggles",
          data: ts.goggles || [],
          borderColor: "#FF4D8D", // Pink
          backgroundColor: "rgba(255, 77, 141, 0.08)",
          tension: 0.35,
          borderWidth: 2,
          fill: true
        },
        {
          label: "Other",
          data: ts.other || [],
          borderColor: "#B5179E", // Berry
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
        legend: {
          position: "top",
          labels: { boxWidth: 10, font: { size: 10, weight: 600 }, color: "#6B3A4D" }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0, color: "#6B3A4D" },
          grid: { color: "rgba(255, 107, 74, 0.08)" }
        },
        x: {
          ticks: { color: "#6B3A4D" },
          grid: { display: false }
        }
      }
    }
  });
}

function renderComplianceTargetChart(targetData) {
  const ctx = document.getElementById("complianceTargetChart")?.getContext("2d");
  if (!ctx) return;

  if (complianceTargetChartInstance) {
    complianceTargetChartInstance.destroy();
  }

  const dates = (targetData.dates || []).map(d => String(d).slice(5));
  const achieved = targetData.achieved || [];
  const target = targetData.target || [];

  complianceTargetChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Achieved %",
          data: achieved,
          backgroundColor: "#22B573", // Mint
          borderRadius: 4
        },
        {
          label: "Target % (95%)",
          data: target,
          backgroundColor: "rgba(255, 201, 60, 0.55)", // Sun soft
          borderColor: "#FF9F1C",
          borderWidth: 1,
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 10, font: { size: 10, weight: 600 }, color: "#6B3A4D" }
        }
      },
      scales: {
        y: {
          min: 60,
          max: 100,
          ticks: { callback: v => v + "%", color: "#6B3A4D" },
          grid: { color: "rgba(255, 107, 74, 0.08)" }
        },
        x: {
          ticks: { color: "#6B3A4D" },
          grid: { display: false }
        }
      }
    }
  });
}

function renderMonthlyPerformanceChart(monthly) {
  const canvas = document.getElementById("monthlyPerformanceChart");
  const emptyState = document.getElementById("monthlyEmptyState");
  if (!canvas || !emptyState) return;

  if (monthlyPerformanceChartInstance) {
    monthlyPerformanceChartInstance.destroy();
  }

  // If fewer than 2 months of data, render friendly empty state
  if (!monthly || !monthly.has_enough_data || !monthly.months || monthly.months.length < 2) {
    canvas.style.display = "none";
    emptyState.style.display = "flex";
    return;
  }

  canvas.style.display = "block";
  emptyState.style.display = "none";

  const ctx = canvas.getContext("2d");
  monthlyPerformanceChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: monthly.months,
      datasets: [
        {
          label: "Compliance %",
          data: monthly.compliance,
          backgroundColor: "#22B573",
          borderRadius: 6,
          yAxisID: "y"
        },
        {
          label: "Violations Count",
          data: monthly.violations,
          backgroundColor: "#FF6B4A",
          borderRadius: 6,
          yAxisID: "y1"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 10, font: { size: 10, weight: 600 }, color: "#6B3A4D" }
        }
      },
      scales: {
        y: {
          min: 50,
          max: 100,
          ticks: { callback: v => v + "%", color: "#6B3A4D" },
          grid: { color: "rgba(255, 107, 74, 0.08)" }
        },
        y1: {
          position: "right",
          beginAtZero: true,
          ticks: { precision: 0, color: "#FF6B4A" },
          grid: { display: false }
        },
        x: {
          ticks: { color: "#6B3A4D" },
          grid: { display: false }
        }
      }
    }
  });
}
async function fetchRecentViolations() {
  const container = document.getElementById("recentViolationsList");
  if (!container) return;

  try {
    const res = await fetch("/api/violations?per_page=4");
    const data = await res.json();
    const items = data.items || [];

    if (items.length === 0) {
      container.innerHTML = `
        <div class="empty-state-box" style="padding: 24px 10px;">
          <span class="empty-state-icon">✅</span>
          <p class="empty-state-text">No active violations recorded. Safety standards are fully maintained.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(v => {
      // Derive severity badge color
      const sev = (v.severity || "MEDIUM").toUpperCase();
      let sevClass = "pill-medium";
      if (sev === "HIGH" || sev === "CRITICAL") sevClass = "pill-high";
      else if (sev === "LOW") sevClass = "pill-low";

      const timeStr = v.detected_at ? String(v.detected_at).slice(5, 16) : "Recent";
      const thumbSrc = v.snapshot_path ? `/outputs/${v.snapshot_path}` : "/static/img/placeholder_worker.jpg";

      return `
        <div class="violation-row-item">
          <img class="violation-thumb" src="${thumbSrc}" alt="Crop" onerror="this.src='/static/img/placeholder_worker.jpg'">
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
              <strong style="font-size: 13px; color: var(--text-strong); text-transform: capitalize;">
                No ${v.violation_type || 'PPE'}
              </strong>
              <span class="pill ${sevClass}" style="font-size: 10px; padding: 2px 7px;">${sev}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between;">
              <span>${v.camera_name || 'Cam 01'} • ${v.location || 'Site'}</span>
              <span>${timeStr}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

  } catch (err) {
    container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--danger); font-size:12px;">Failed to load recent infractions</div>`;
  }
}

function fetchSystemHealth() {
  fetch('/api/health')
    .then(r => r.json())
    .then(data => {
      const overall = document.getElementById('healthOverallBadge');
      if (overall) {
        overall.innerText = data.overall === 'healthy' ? '✅ All Systems Operational' : '⚠️ Subsystem Fallback Active';
        overall.className = 'badge-status ' + (data.overall === 'healthy' ? 'status-safe' : 'status-detected');
      }
      const comps = data.components || {};

      const dbVal = document.getElementById('healthDbVal');
      if (dbVal && comps.database) {
        dbVal.innerText = `${comps.database.type} (${comps.database.status})`;
        dbVal.style.color = comps.database.ok ? 'var(--mint)' : 'var(--danger)';
      }

      const detVal = document.getElementById('healthDetectorVal');
      if (detVal && comps.detector) {
        detVal.innerText = comps.detector.demo_mode ? 'High-fidelity Demo' : 'Weights Active';
        detVal.style.color = comps.detector.demo_mode ? 'var(--sun)' : 'var(--mint)';
      }

      const docVal = document.getElementById('healthDocIndexVal');
      if (docVal && comps.document_index) {
        docVal.innerText = `${comps.document_index.chunks_count} Chunks (${comps.document_index.backend})`;
        docVal.style.color = 'var(--mint)';
      }

      const visVal = document.getElementById('healthVisualIndexVal');
      if (visVal && comps.visual_index) {
        visVal.innerText = `${comps.visual_index.indexed_events} Events Indexed`;
        visVal.style.color = 'var(--mint)';
      }

      const llmVal = document.getElementById('healthLlmVal');
      if (llmVal && comps.llm_provider) {
        llmVal.innerText = comps.llm_provider.is_available ? `${comps.llm_provider.provider} (${comps.llm_provider.model})` : 'Offline Template Mode';
        llmVal.style.color = comps.llm_provider.is_available ? 'var(--mint)' : 'var(--sun)';
      }

      const lgVal = document.getElementById('healthLanggraphVal');
      if (lgVal && comps.langgraph) {
        lgVal.innerText = `v${comps.langgraph.version} (${comps.langgraph.checkpointer})`;
        lgVal.style.color = 'var(--mint)';
      }

      const themeVal = document.getElementById('healthThemeVal');
      if (themeVal && comps.theme_colors) {
        themeVal.innerText = comps.theme_colors.ok ? 'Sunrise Garden (0 violations)' : `${comps.theme_colors.violations_count} color flags`;
        themeVal.style.color = comps.theme_colors.ok ? 'var(--mint)' : 'var(--danger)';
      }
    })
    .catch(err => {
      console.warn('Failed to load system health:', err);
    });
}

function updateKPIs(kpi) {
  if (!kpi) return;

  animateValue("kpiTotalPeople", kpi.total_people || 0);
  animateValue("kpiSafe", kpi.safe_count || 0);
  animateValue("kpiUnsafe", kpi.unsafe_count || 0);
  animateValue("kpiCompliance", kpi.compliance_percent || 0, "%");
  animateValue("kpiViolations", kpi.total_violations || 0);
  animateValue("kpiReports", kpi.reports_count !== undefined ? kpi.reports_count : 32);

  // Show/Hide trend chips based on whether previous-period data exists
  const trends = kpi.trends || {};
  const hasPrev = Boolean(trends.has_previous);

  const chips = [
    { id: "trendWorkers", key: "workers" },
    { id: "trendCompliant", key: "compliant" },
    { id: "trendUnsafe", key: "unsafe" },
    { id: "trendCompliance", key: "compliance" },
    { id: "trendViolations", key: "violations" },
    { id: "trendReports", key: "reports" }
  ];

  chips.forEach(c => {
    const chipEl = document.getElementById(c.id);
    if (!chipEl) return;
    if (hasPrev && trends[c.key]) {
      const t = trends[c.key];
      const sign = t.dir === "up" ? "↑" : "↓";
      chipEl.innerText = `${sign} ${Math.abs(t.pct || 0)}%`;
      chipEl.className = `trend-chip ${t.dir === "up" ? "trend-chip-up" : "trend-chip-down"}`;
      chipEl.style.display = "inline-flex";
    } else {
      chipEl.style.display = "none";
    }
  });
}

function updateSafetyScore(scoreData) {
  if (!scoreData) return;
  const score = scoreData.score || 94.5;
  const status = scoreData.status || "Optimal";

  // Palette color mapping
  const color = score >= 90 ? "#22B573" : (score >= 70 ? "#FFC93C" : "#E53950");

  const valEl = document.getElementById("safetyGaugeVal");
  const statEl = document.getElementById("safetyGaugeStatus");
  const gaugeCircle = document.getElementById("safetyGauge");
  const topVal = document.getElementById("topSafetyScoreVal");
  const topBadge = document.getElementById("topSafetyScoreBadge");

  if (valEl) valEl.innerText = score + "%";
  if (topVal) topVal.innerText = score + "%";
  if (topVal) topVal.style.color = color;

  if (statEl) {
    statEl.innerText = status + " Status";
    statEl.style.color = color;
  }
  if (topBadge) {
    topBadge.innerText = status;
    topBadge.style.color = color;
  }

  if (gaugeCircle) {
    gaugeCircle.style.background = `conic-gradient(${color} 0% ${score}%, var(--border-soft) ${score}% 100%)`;
  }
}
async function triggerReportGeneration() {
  try {
    const res = await fetch("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ include_charts: true })
    });
    const data = await res.json();
    if (data.success && data.download_url) {
      showNotification("PDF report generated successfully!", "success");
      setTimeout(() => {
        window.location.href = data.download_url;
      }, 500);
    } else {
      showNotification(data.error || "Failed to generate report", "error");
    }
  } catch (err) {
    showNotification("Error compiling PDF: " + err, "error");
  }
}
async function initDashboard() {
  await fetchAllAnalytics();
  fetchSystemHealth();
  fetchLatestDetections();
  fetchRecentViolations();
}
async function fetchLatestDetections() {
  try {
    const res = await fetch("/api/analytics/latest-detections?limit=6");
    const items = await res.json();
    detectionItems = items || [];
    currentDetectionIdx = 0;
    if (detectionItems.length > 0) {
      updateDetectionCard(detectionItems[0]);
    } else {
      const empty = document.getElementById("liveDetectionEmpty");
      const img = document.getElementById("liveDetectionImg");
      if (empty) empty.style.display = "flex";
      if (img) img.style.display = "none";
    }
  } catch (err) {
    console.warn("Failed latest detections fetch:", err);
  }
}