/**
 * Workplace Safety KPI Dashboard Module
 * Handles independent fetching, count-up animations, 60s auto-refresh
 * (pausing when tab is hidden), and isolated error/retry states for KpiCards.
 */

let kpiAutoRefreshTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  initWorkplaceKpis();
  setupVisibilityHandler();
});

function initWorkplaceKpis() {
  // Start periodic 60s auto-refresh
  startAutoRefresh();
}

function setupVisibilityHandler() {
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopAutoRefresh();
    } else {
      // Refresh immediately on tab focus and resume timer
      fetchWorkplaceKpis();
      startAutoRefresh();
    }
  });
}

function startAutoRefresh() {
  stopAutoRefresh();
  kpiAutoRefreshTimer = setInterval(() => {
    if (!document.hidden) {
      fetchWorkplaceKpis();
    }
  }, 60000); // 60 seconds
}

function stopAutoRefresh() {
  if (kpiAutoRefreshTimer) {
    clearInterval(kpiAutoRefreshTimer);
    kpiAutoRefreshTimer = null;
  }
}

/**
 * Animate numeric counter from current to target value.
 * Respects prefers-reduced-motion settings.
 */
function animateKpiNumber(el, targetVal, isFloat = false) {
  if (!el) return;
  const target = parseFloat(targetVal);
  if (isNaN(target)) {
    el.innerText = targetVal || "No data";
    return;
  }

  // Check prefers-reduced-motion
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReduced) {
    el.innerText = isFloat ? target.toFixed(1) : Math.round(target);
    return;
  }

  const startVal = parseFloat(el.getAttribute("data-val") || "0") || 0;
  el.setAttribute("data-val", target);
  const duration = 750;
  const startTime = performance.now();

  function updateStep(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // easeOutQuad curve
    const ease = 1 - (1 - progress) * (1 - progress);
    const current = startVal + (target - startVal) * ease;

    el.innerText = isFloat ? current.toFixed(1) : Math.round(current);

    if (progress < 1) {
      requestAnimationFrame(updateStep);
    } else {
      el.innerText = isFloat ? target.toFixed(1) : Math.round(target);
    }
  }

  requestAnimationFrame(updateStep);
}

/**
 * Sets visual state for a KpiCard ('ready', 'loading', 'error', 'empty').
 */
function setCardState(cardId, state) {
  const card = document.getElementById(cardId);
  if (!card) return;
  card.classList.remove("kpi-state-ready", "kpi-state-loading", "kpi-state-error", "kpi-state-empty");
  card.classList.add(`kpi-state-${state}`);
}

/**
 * Fetches workplace safety KPIs from the dedicated backend endpoint.
 */
async function fetchWorkplaceKpis() {
  const timeEl = document.getElementById("workplaceKpiUpdateTime");
  const refreshBtn = document.getElementById("manualKpiRefreshBtn");

  if (refreshBtn) {
    refreshBtn.classList.add("spinning");
  }

  try {
    const res = await fetch("/api/kpis/workplace-safety");
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const json = await res.json();
    if (!json.ok || !json.data) {
      throw new Error(json.error || "Malformed response");
    }

    const data = json.data;
    renderWorkplaceKpis(data);

    if (timeEl && data.generated_at) {
      timeEl.innerText = `Updated ${data.generated_at.slice(11)}`;
    }
  } catch (err) {
    console.warn("Workplace safety KPI fetch failed:", err);
    // Set all cards to error state with retry buttons
    const allCardIds = ["kpiCardInspections", "kpiCardViolations", "kpiCardResolved", "kpiCardCompliance"].concat(window.EXTENDED_KPI_CARD_IDS || []);
    allCardIds.forEach(id => {
      setCardState(id, "error");
    });
  } finally {
    if (refreshBtn) {
      setTimeout(() => refreshBtn.classList.remove("spinning"), 400);
    }
  }
}

/**
 * Renders verified data into the 4 KpiCards.
 */
function renderWorkplaceKpis(data) {
  // 1. Total Inspections Card
  const c1 = document.getElementById("kpiCardInspections");
  if (c1) {
    const valEl = document.getElementById("kpiCardInspections_val");
    setCardState("kpiCardInspections", "ready");
    animateKpiNumber(valEl, data.total_inspections, false);
    c1.setAttribute("aria-label", `Total Inspections: ${data.total_inspections}`);
  }

  // 2. Total PPE Violations Card
  const c2 = document.getElementById("kpiCardViolations");
  if (c2) {
    const valEl = document.getElementById("kpiCardViolations_val");
    setCardState("kpiCardViolations", "ready");
    animateKpiNumber(valEl, data.total_violations, false);
    c2.setAttribute("aria-label", `Total PPE Violations: ${data.total_violations}`);
  }

  // 3. Resolved Violations Card
  const c3 = document.getElementById("kpiCardResolved");
  if (c3) {
    const valEl = document.getElementById("kpiCardResolved_val");
    const descEl = document.getElementById("kpiCardResolved_desc");
    setCardState("kpiCardResolved", "ready");
    animateKpiNumber(valEl, data.resolved_violations, false);
    if (descEl) {
      descEl.innerText = `${data.resolved_violations} of ${data.total_violations} total violations resolved`;
    }
    c3.setAttribute("aria-label", `Resolved Violations: ${data.resolved_violations} of ${data.total_violations}`);
  }

  // 4. Compliance Percentage Card
  const c4 = document.getElementById("kpiCardCompliance");
  if (c4) {
    const valEl = document.getElementById("kpiCardCompliance_val");
    if (data.compliance_percentage === null || data.compliance_percentage === undefined) {
      setCardState("kpiCardCompliance", "empty");
      c4.setAttribute("aria-label", "Compliance Percentage: No data yet");
    } else {
      setCardState("kpiCardCompliance", "ready");
      animateKpiNumber(valEl, data.compliance_percentage, true);

      // Update tone threshold class dynamically
      c4.classList.remove("kpi-tone-success", "kpi-tone-warning", "kpi-tone-danger");
      const pct = data.compliance_percentage;
      let tone = "success";
      if (pct < 75.0) tone = "danger";
      else if (pct < 90.0) tone = "warning";
      c4.classList.add(`kpi-tone-${tone}`);
      c4.setAttribute("aria-label", `Compliance Percentage: ${pct}%`);
    }
  }

  if (typeof window.renderExtendedWorkplaceKpis === "function") {
    window.renderExtendedWorkplaceKpis(data);
  }
}

/**
 * Manual retry handler for individual cards.
 */
function refreshWorkplaceKpiCard(cardId) {
  setCardState(cardId, "loading");
  setTimeout(() => fetchWorkplaceKpis(), 250);
}

// Global exposure for retry buttons and manual refresh
window.fetchWorkplaceKpis = fetchWorkplaceKpis;
window.refreshWorkplaceKpiCard = refreshWorkplaceKpiCard;
