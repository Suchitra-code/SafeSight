/**
 * SafeSight AI — Premium Workplace Safety Intelligence Platform Controller
 * Manages live data synchronization, URL filter state, Chart.js visualizations,
 * count-up animations, inspection scheduling, and AI Insights interactions.
 * Strictly adheres to the Sunrise Garden palette (0 black, 0 blue).
 */

// Strict Sunrise Garden Palette Constants (0 black, 0 blue)
const PALETTE = {
  coral: "#FF6B4A",
  pink: "#E76B9A",
  mint: "#35B982",
  orchid: "#C94BB5",
  sun: "#F2B705",
  lime: "#8CC63F",
  peach: "#F0A45D",
  red: "#E53950",
  textStrong: "#4A1D2F",
  textMuted: "#7A5563",
  border: "#F3DDD3"
};

// Global chart instances
let complianceTrendChartInstance = null;
let violationsTypeChartInstance = null;
let deptPerformanceChartInstance = null;

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
  fetchAllAnalytics();
});

/**
 * Configure Chart.js global defaults so NO black and NO blue appear.
 */
function setupChartDefaults() {
  if (!window.Chart) return;

  Chart.defaults.color = PALETTE.textMuted;
  Chart.defaults.borderColor = "rgba(243, 221, 211, 0.7)";
  Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
  Chart.defaults.font.size = 11;

  if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) {
    Chart.defaults.plugins.tooltip.backgroundColor = PALETTE.textStrong;
    Chart.defaults.plugins.tooltip.titleColor = "#FFFFFF";
    Chart.defaults.plugins.tooltip.bodyColor = "#FFF9F2";
    Chart.defaults.plugins.tooltip.borderColor = PALETTE.coral;
    Chart.defaults.plugins.tooltip.borderWidth = 1.5;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
  }
}

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

  // 1. Core Workplace Safety KPIs
  fetchWorkplaceKpis(query);

  // 2. Compliance Trend Line Chart
  fetchComplianceTrend(query);

  // 3. Violations by Type Donut
  fetchViolationsByType(query);

  // 4. Spatial Safety Risk Heatmap
  fetchZoneRiskHeatmap(query);

  // 5. Department Performance
  fetchDepartmentPerformance(query);

  // 6. Safety Score Index
  fetchSafetyPerformanceScore();

  // 7. Update Last Loaded Timestamp
  const timeEl = document.getElementById("lastLoadedTimestamp");
  if (timeEl) {
    const now = new Date();
    timeEl.innerText = `Last loaded: ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
  }
}

function buildQueryString() {
  const params = new URLSearchParams();
  if (currentFilters.department !== "all") params.set("department", currentFilters.department);
  if (currentFilters.location !== "all") params.set("location", currentFilters.location);
  if (currentFilters.type !== "all") params.set("type", currentFilters.type);
  if (currentFilters.dateFrom) params.set("from", currentFilters.dateFrom);
  if (currentFilters.dateTo) params.set("to", currentFilters.dateTo);
  if (currentFilters.status !== "all") params.set("status", currentFilters.status);
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
  const canvas = document.getElementById("complianceOverviewChart");
  if (!canvas || !window.Chart) return;

  const dates = data.dates || [];
  const compliance = data.compliance || [];
  const target = Array(dates.length).fill(95.0);

  if (complianceTrendChartInstance) {
    complianceTrendChartInstance.destroy();
  }

  complianceTrendChartInstance = new Chart(canvas, {
    type: "line",
    data: {
      labels: dates.map(d => d.slice(5)), // MM-DD
      datasets: [
        {
          label: "Achieved Compliance (%)",
          data: compliance,
          borderColor: PALETTE.mint,
          backgroundColor: "rgba(53, 185, 130, 0.12)",
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointBackgroundColor: PALETTE.mint,
          pointRadius: 3
        },
        {
          label: "Safety Target (95.0%)",
          data: target,
          borderColor: PALETTE.coral,
          borderDash: [5, 5],
          borderWidth: 2,
          pointRadius: 0,
          fill: false
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
          labels: {
            boxWidth: 12,
            font: { size: 10, weight: "700" },
            color: PALETTE.textStrong
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
            font: { size: 10 }
          },
          grid: { color: "rgba(243, 221, 211, 0.6)" }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 10 } }
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
  const canvas = document.getElementById("violationsTypeChart");
  if (!canvas || !window.Chart) return;

  const totalBadge = document.getElementById("donutTotalBadge");
  if (totalBadge) totalBadge.innerText = `${data.total || 0} Total`;

  const counts = {
    Helmet: data.helmet || 0,
    Vest: data.vest || 0,
    Goggles: data.goggles || 0,
    Other: data.other || 0
  };

  const labels = Object.keys(counts);
  const values = Object.values(counts);
  const colors = [PALETTE.coral, PALETTE.sun, PALETTE.pink, PALETTE.orchid];

  if (violationsTypeChartInstance) {
    violationsTypeChartInstance.destroy();
  }

  violationsTypeChartInstance = new Chart(canvas, {
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
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw} infractions (${Math.round((ctx.raw / Math.max(1, data.total)) * 100)}%)`
          }
        }
      }
    }
  });

  // Render clickable legend pills underneath
  const pillsWrap = document.getElementById("violationTypePills");
  if (pillsWrap) {
    pillsWrap.innerHTML = labels.map((l, i) => `
      <div class="filter-chip" style="cursor: pointer; background: var(--bg-page); color: var(--text-strong); border-color: var(--border-soft);" onclick="filterByType('${l}')" title="Filter by ${l}">
        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${colors[i]};"></span>
        <span><b>${l}:</b> ${counts[l]}</span>
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
          borderRadius: 6
        },
        {
          label: "Violations",
          data: viol,
          backgroundColor: PALETTE.pink,
          borderRadius: 6
        },
        {
          label: "Resolved",
          data: res,
          backgroundColor: PALETTE.mint,
          borderRadius: 6
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
          labels: { boxWidth: 10, font: { size: 10, weight: "700" } }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { font: { size: 10 } },
          grid: { color: "rgba(243, 221, 211, 0.6)" }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 10, weight: "700" } }
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
      badge.innerText = "● COMPLIANT";
    } else {
      badge.className = "badge-status status-danger";
      badge.innerText = `● ${item.violations_count || 1} VIOLATIONS`;
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
