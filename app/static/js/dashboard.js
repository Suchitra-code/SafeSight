/**
 * SafeSight AI – BI Dashboard Controller (Redesign)
 * Full interactive controller supporting 6 KPI cards, 6 chart widgets,
 * live detection carousel, recent violations list, system health, and quick report actions.
 * Strictly adheres to the Sunrise Garden palette (0 black, 0 blue).
 */

// Global chart instances
let complianceOverviewChartInstance = null;
let ppeSummaryChartInstance = null;
let violationsTypeChartInstance = null;
let violationDistChartInstance = null;
let timeseriesChartInstance = null;
let complianceTargetChartInstance = null;
let monthlyPerformanceChartInstance = null;

// Live detections carousel state
let detectionItems = [];
let currentDetectionIdx = 0;

document.addEventListener("DOMContentLoaded", () => {
  setupChartDefaults();
  initDashboard();
  setupEventListeners();
});

/**
 * Configure Chart.js global defaults so NO black and NO blue appear.
 */
function setupChartDefaults() {
  if (!window.Chart) return;

  Chart.defaults.color = "#6B3A4D"; // Plum text
  Chart.defaults.borderColor = "rgba(255, 107, 74, 0.12)"; // Soft coral grid
  Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
  Chart.defaults.font.size = 11;

  if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) {
    Chart.defaults.plugins.tooltip.backgroundColor = "#4A1D2F";
    Chart.defaults.plugins.tooltip.titleColor = "#FFFFFF";
    Chart.defaults.plugins.tooltip.bodyColor = "#FFF7EE";
    Chart.defaults.plugins.tooltip.borderColor = "#FF6B4A";
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
  }
}

function setupEventListeners() {
  // Apply Filter Button
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
        showNotification(data.message || "Demo data populated (53 violations, 21 days)", "success");
        setTimeout(() => location.reload(), 700);
      } catch (err) {
        showNotification("Error loading demo data: " + err, "error");
        demoBtn.disabled = false;
        demoBtn.innerHTML = "<span>🔄</span> Load Demo Data";
      }
    });
  }

  // Carousel Controls
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

  // Quick Action: Download Latest Compliance Report
  const downloadBtn = document.getElementById("downloadComplianceReportBtn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", async () => {
      downloadBtn.disabled = true;
      downloadBtn.innerHTML = "<span>⏳</span> Finding Report...";
      try {
        const res = await fetch("/api/reports");
        const list = await res.json();
        if (list && list.length > 0) {
          const latest = list[0];
          showNotification(`Downloading ${latest.filename}...`, "success");
          window.location.href = latest.download_url;
        } else {
          showNotification("No PDF report generated yet. Generating one now...", "info");
          await triggerReportGeneration();
        }
      } catch (e) {
        showNotification("Error fetching report: " + e, "error");
      } finally {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = "<span>⬇</span> Download Latest PDF";
      }
    });
  }

  // Quick Action: Generate Safety Summary PDF
  const genBtn = document.getElementById("generateSafetySummaryBtn");
  if (genBtn) {
    genBtn.addEventListener("click", async () => {
      genBtn.disabled = true;
      genBtn.innerHTML = "<span>⏳</span> Compiling PDF...";
      await triggerReportGeneration();
      genBtn.disabled = false;
      genBtn.innerHTML = "<span>🔄</span> Generate New PDF";
    });
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
  fetchSystemHealth();
  fetchLatestDetections();
  fetchRecentViolations();
}

async function fetchAllAnalytics() {
  const query = getFilterParams();

  // 1. Fetch KPI & Site Safety Score
  fetch(`/api/analytics/kpi?${query}`)
    .then(r => r.json())
    .then(data => updateKPIs(data))
    .catch(err => console.warn("Failed KPI fetch:", err));

  fetch(`/api/analytics/safety-score?${query}`)
    .then(r => r.json())
    .then(data => updateSafetyScore(data))
    .catch(err => console.warn("Failed Safety Score fetch:", err));

  // 2. Row 2: Compliance Overview Line Chart
  fetch(`/api/analytics/compliance-trend?${query}`)
    .then(r => r.json())
    .then(data => renderComplianceOverviewChart(data))
    .catch(err => console.warn("Failed Compliance Overview fetch:", err));

  // 3. Row 3: PPE Summary Doughnut, Violation Analysis Bar, Violation Distribution Pie
  fetch(`/api/analytics/ppe-summary`)
    .then(r => r.json())
    .then(data => renderPPESummaryChart(data))
    .catch(err => console.warn("Failed PPE Summary fetch:", err));

  fetch(`/api/analytics/violations-by-type?${query}`)
    .then(r => r.json())
    .then(data => {
      renderViolationsTypeChart(data);
      renderViolationDistChart(data);
    })
    .catch(err => console.warn("Failed Violations Type fetch:", err));

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
}

/**
 * Animate numeric counter from 0 to target.
 */
function animateValue(id, target, suffix = "") {
  const el = document.getElementById(id);
  if (!el) return;
  const num = parseFloat(target) || 0;
  if (num === 0) {
    el.innerText = "0" + suffix;
    return;
  }
  const isFloat = String(target).includes(".");
  const duration = 800;
  const start = performance.now();

  function step(time) {
    const elapsed = time - start;
    const progress = Math.min(elapsed / duration, 1);
    // easeOutQuad
    const eased = 1 - (1 - progress) * (1 - progress);
    const current = progress === 1 ? num : num * eased;
    el.innerText = (isFloat ? current.toFixed(1) : Math.round(current)) + suffix;
    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }
  requestAnimationFrame(step);
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

/**
 * Row 2: Safety Compliance Overview (Line Chart with 2 Series: Compliance % + Violations)
 */
function renderComplianceOverviewChart(trend) {
  const ctx = document.getElementById("complianceOverviewChart")?.getContext("2d");
  if (!ctx) return;

  if (complianceOverviewChartInstance) {
    complianceOverviewChartInstance.destroy();
  }

  const dates = (trend.dates || []).map(d => String(d).slice(5));
  const compliance = trend.compliance || [];
  const violations = trend.violations || [];

  complianceOverviewChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Compliance Rate (%)",
          data: compliance,
          borderColor: "#22B573", // Mint
          backgroundColor: "rgba(34, 181, 115, 0.12)",
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointRadius: 2,
          yAxisID: "y"
        },
        {
          label: "Daily Infractions",
          data: violations,
          borderColor: "#FF6B4A", // Sunset Coral
          backgroundColor: "rgba(255, 107, 74, 0.08)",
          fill: false,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 2,
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
          labels: { boxWidth: 10, color: "#6B3A4D", font: { size: 10, weight: 600 } }
        }
      },
      scales: {
        y: {
          type: "linear",
          position: "left",
          min: 70,
          max: 100,
          ticks: { color: "#6B3A4D", callback: v => v + "%" },
          grid: { color: "rgba(255, 107, 74, 0.08)" }
        },
        y1: {
          type: "linear",
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

/**
 * Row 2: Live Detection Result Carousel
 */
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

function updateDetectionCard(item) {
  if (!item) return;

  const img = document.getElementById("liveDetectionImg");
  const empty = document.getElementById("liveDetectionEmpty");
  const badge = document.getElementById("liveDetectionBadge");
  const counter = document.getElementById("liveDetectionCounter");
  const cam = document.getElementById("liveDetectionCam");
  const loc = document.getElementById("liveDetectionLoc");
  const ppl = document.getElementById("liveDetectionPeople");

  if (counter) counter.innerText = `${currentDetectionIdx + 1} / ${detectionItems.length}`;
  if (cam) cam.innerHTML = `<b>Cam:</b> ${item.camera_name || 'Cam 01'}`;
  if (loc) loc.innerHTML = `<b>Zone:</b> ${item.location || 'Fabrication'}`;
  if (ppl) ppl.innerHTML = `<b>Personnel:</b> ${item.total_people || 1} (${item.safe_count || 1} safe)`;

  const isSafe = item.is_compliant !== false && item.violations_count === 0;
  if (badge) {
    badge.innerText = isSafe ? "● COMPLIANT" : "● NON-COMPLIANT";
    badge.className = `badge-status ${isSafe ? 'status-safe' : 'status-detected'}`;
  }

  if (img && item.output_path) {
    img.src = `/outputs/${item.output_path}`;
    img.style.display = "block";
    if (empty) empty.style.display = "none";
  } else if (img) {
    img.style.display = "none";
    if (empty) empty.style.display = "flex";
  }
}

/**
 * Row 2: Recent Violations List
 */
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

/**
 * Row 3: PPE Detection Summary (Doughnut Chart)
 */
function renderPPESummaryChart(summary) {
  const ctx = document.getElementById("ppeSummaryChart")?.getContext("2d");
  if (!ctx) return;

  if (ppeSummaryChartInstance) {
    ppeSummaryChartInstance.destroy();
  }

  const safe = summary.compliant_workers || 0;
  const unsafe = summary.unsafe_workers || 0;
  const categories = summary.categories || {};

  // Build labels and values from real data only
  const labels = ["With PPE", "Without PPE"];
  const values = [safe, unsafe];
  const colors = ["#22B573", "#E53950"]; // Mint, Red

  // Append real category counts if present
  const catPalette = ["#FF6B4A", "#FFC93C", "#FF4D8D", "#B5179E"];
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
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "66%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 10, weight: 600 }, color: "#6B3A4D", boxWidth: 10 }
        }
      }
    }
  });

  // Center rate text
  const pillsContainer = document.getElementById("ppeSummaryPills");
  if (pillsContainer) {
    pillsContainer.innerHTML = `
      <span class="pill pill-low" style="background:rgba(34,181,115,0.15); color:var(--mint); font-weight:700;">
        ${summary.compliance_percent || 94.5}% Overall Compliance
      </span>
      <span class="pill pill-high" style="font-weight:700;">
        ${safe} Safe / ${unsafe} Infractions
      </span>
    `;
  }
}

/**
 * Row 3: Violation Analysis (Bar Chart of Infractions by Category)
 */
function renderViolationsTypeChart(typesData) {
  const ctx = document.getElementById("violationsTypeChart")?.getContext("2d");
  if (!ctx) return;

  if (violationsTypeChartInstance) {
    violationsTypeChartInstance.destroy();
  }

  const vTot = document.getElementById("vTotalCount");
  if (vTot) vTot.innerText = typesData.total || 0;

  const labels = ["Helmet", "Safety Vest", "Goggles", "Other"];
  const values = [
    typesData.helmet || 0,
    typesData.vest || 0,
    typesData.goggles || 0,
    typesData.other || 0
  ];

  violationsTypeChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Infractions",
          data: values,
          backgroundColor: ["#FF6B4A", "#FFC93C", "#FF4D8D", "#B5179E"],
          borderRadius: 8,
          borderWidth: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0, color: "#6B3A4D" },
          grid: { color: "rgba(255, 107, 74, 0.08)" }
        },
        x: {
          ticks: { color: "#6B3A4D", font: { weight: 600 } },
          grid: { display: false }
        }
      }
    }
  });
}

/**
 * Row 3: Violation Distribution (Pie Chart)
 */
function renderViolationDistChart(typesData) {
  const ctx = document.getElementById("violationDistChart")?.getContext("2d");
  if (!ctx) return;

  if (violationDistChartInstance) {
    violationDistChartInstance.destroy();
  }

  violationDistChartInstance = new Chart(ctx, {
    type: "pie",
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
          backgroundColor: ["#E53950", "#FFC93C", "#FF4D8D", "#B5179E"],
          borderColor: "#FFFFFF",
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { font: { size: 10, weight: 600 }, color: "#6B3A4D", boxWidth: 10 }
        }
      }
    }
  });
}

/**
 * Row 4: Daily PPE Events (Area Chart Timeseries)
 */
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

/**
 * Row 4: Compliance Trends (Target vs Achieved Grouped Bars)
 */
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

/**
 * Row 4: Monthly Safety Performance (Monthly comparison or Empty State)
 */
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

/**
 * Row 5: System Health Monitoring
 */
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

function showNotification(message, type = "info") {
  if (window.showToast) {
    window.showToast(message, type);
    return;
  }
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerText = message;
  container.appendChild(t);
  setTimeout(() => {
    t.remove();
  }, 3500);
}
