/**
 * SafeSight AI — Violation Monitoring Controller
 * Handles server-side search, filtering, pagination, summary card KPI animations,
 * interactive status updates with toast feedback, and keyboard-accessible image preview modal.
 * Strictly adheres to Sunrise Garden color rules (0 black, 0 blue).
 */

(function () {
  "use strict";

  // Application State
  const state = {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    q: "",
    type: "",
    status: "",
    date: "",
    from: "",
    to: "",
    items: [],
    modalIndex: -1,
    counts: { total: 0, pending: 0, reviewed: 0, resolved: 0 },
    isLoading: false
  };

  let searchDebounceTimer = null;

  // DOM Elements cache
  let dom = {};

  document.addEventListener("DOMContentLoaded", () => {
    initDomReferences();
    parseUrlParams();
    setupEventListeners();
    fetchViolations();
  });

  function initDomReferences() {
    dom = {
      // KPI Cards
      kpiTotal: document.getElementById("vmKpiTotal"),
      kpiPending: document.getElementById("vmKpiPending"),
      kpiReviewed: document.getElementById("vmKpiReviewed"),
      kpiResolved: document.getElementById("vmKpiResolved"),
      kpiValTotal: document.getElementById("vmValTotal"),
      kpiValPending: document.getElementById("vmValPending"),
      kpiValReviewed: document.getElementById("vmValReviewed"),
      kpiValResolved: document.getElementById("vmValResolved"),

      // Filter controls
      searchInput: document.getElementById("vmSearchInput"),
      searchClearBtn: document.getElementById("vmSearchClear"),
      typeSelect: document.getElementById("vmTypeFilter"),
      statusSelect: document.getElementById("vmStatusFilter"),
      dateInput: document.getElementById("vmDateFilter"),
      fromInput: document.getElementById("vmFromFilter"),
      toInput: document.getElementById("vmToFilter"),
      pageSizeSelect: document.getElementById("vmPageSizeSelect"),
      clearAllBtn: document.getElementById("vmClearAllBtn"),
      chipsContainer: document.getElementById("vmFilterChips"),

      // Table & Pagination
      tableBody: document.getElementById("vmTableBody"),
      emptyState: document.getElementById("vmEmptyState"),
      loadingSkeleton: document.getElementById("vmLoadingSkeleton"),
      pageInfo: document.getElementById("vmPageInfo"),
      prevPageBtn: document.getElementById("vmPrevPageBtn"),
      nextPageBtn: document.getElementById("vmNextPageBtn"),
      pageNumbersWrap: document.getElementById("vmPageNumbers"),

      // Modal
      modalBackdrop: document.getElementById("vmModalBackdrop"),
      modalCloseBtn: document.getElementById("vmModalCloseBtn"),
      modalPrevBtn: document.getElementById("vmModalPrevBtn"),
      modalNextBtn: document.getElementById("vmModalNextBtn"),
      modalImg: document.getElementById("vmModalImg"),
      modalImgFallback: document.getElementById("vmModalImgFallback"),
      modalTitle: document.getElementById("vmModalTitle"),
      modalId: document.getElementById("vmModalId"),
      modalType: document.getElementById("vmModalType"),
      modalLocation: document.getElementById("vmModalLocation"),
      modalCamera: document.getElementById("vmModalCamera"),
      modalDate: document.getElementById("vmModalDate"),
      modalTime: document.getElementById("vmModalTime"),
      modalStatusSelect: document.getElementById("vmModalStatusSelect"),
      modalNotes: document.getElementById("vmModalNotes"),
      modalReviewer: document.getElementById("vmModalReviewer"),

      // Toast
      toastContainer: document.getElementById("vmToastContainer")
    };
  }

  function parseUrlParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.has("page")) state.page = Math.max(1, parseInt(params.get("page")) || 1);
    if (params.has("page_size")) state.pageSize = parseInt(params.get("page_size")) || 10;
    if (params.has("q")) state.q = params.get("q").trim();
    if (params.has("type")) state.type = params.get("type");
    if (params.has("status")) state.status = params.get("status");
    if (params.has("date")) state.date = params.get("date");
    if (params.has("from")) state.from = params.get("from");
    if (params.has("to")) state.to = params.get("to");

    // Sync input controls with URL state
    if (dom.searchInput && state.q) {
      dom.searchInput.value = state.q;
      if (dom.searchClearBtn) dom.searchClearBtn.style.display = "block";
    }
    if (dom.typeSelect && state.type) dom.typeSelect.value = state.type;
    if (dom.statusSelect && state.status) dom.statusSelect.value = state.status;
    if (dom.dateInput && state.date) dom.dateInput.value = state.date;
    if (dom.fromInput && state.from) dom.fromInput.value = state.from;
    if (dom.toInput && state.to) dom.toInput.value = state.to;
    if (dom.pageSizeSelect) dom.pageSizeSelect.value = String(state.pageSize);

    highlightActiveKpiCard(state.status);
    renderFilterChips();
  }

  function updateUrlParams() {
    const params = new URLSearchParams();
    if (state.page > 1) params.set("page", state.page);
    if (state.pageSize !== 10) params.set("page_size", state.pageSize);
    if (state.q) params.set("q", state.q);
    if (state.type) params.set("type", state.type);
    if (state.status) params.set("status", state.status);
    if (state.date) params.set("date", state.date);
    if (state.from) params.set("from", state.from);
    if (state.to) params.set("to", state.to);

    const queryStr = params.toString();
    const newUrl = window.location.pathname + (queryStr ? "?" + queryStr : "");
    window.history.replaceState({}, "", newUrl);
  }

  function setupEventListeners() {
    // Search with 300ms debounce
    if (dom.searchInput) {
      dom.searchInput.addEventListener("input", (e) => {
        const val = e.target.value.trim();
        if (dom.searchClearBtn) dom.searchClearBtn.style.display = val ? "block" : "none";
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
          state.q = val;
          state.page = 1;
          updateUrlParams();
          renderFilterChips();
          fetchViolations();
        }, 300);
      });
    }

    if (dom.searchClearBtn) {
      dom.searchClearBtn.addEventListener("click", () => {
        dom.searchInput.value = "";
        dom.searchClearBtn.style.display = "none";
        state.q = "";
        state.page = 1;
        updateUrlParams();
        renderFilterChips();
        fetchViolations();
      });
    }

    // Type filter
    if (dom.typeSelect) {
      dom.typeSelect.addEventListener("change", (e) => {
        state.type = e.target.value;
        state.page = 1;
        updateUrlParams();
        renderFilterChips();
        fetchViolations();
      });
    }

    // Status filter
    if (dom.statusSelect) {
      dom.statusSelect.addEventListener("change", (e) => {
        state.status = e.target.value;
        state.page = 1;
        highlightActiveKpiCard(state.status);
        updateUrlParams();
        renderFilterChips();
        fetchViolations();
      });
    }

    // Date filters
    if (dom.dateInput) {
      dom.dateInput.addEventListener("change", (e) => {
        state.date = e.target.value;
        if (state.date) {
          state.from = "";
          state.to = "";
          if (dom.fromInput) dom.fromInput.value = "";
          if (dom.toInput) dom.toInput.value = "";
        }
        state.page = 1;
        updateUrlParams();
        renderFilterChips();
        fetchViolations();
      });
    }

    if (dom.fromInput) {
      dom.fromInput.addEventListener("change", (e) => {
        state.from = e.target.value;
        if (state.from) {
          state.date = "";
          if (dom.dateInput) dom.dateInput.value = "";
        }
        state.page = 1;
        updateUrlParams();
        renderFilterChips();
        fetchViolations();
      });
    }

    if (dom.toInput) {
      dom.toInput.addEventListener("change", (e) => {
        state.to = e.target.value;
        if (state.to) {
          state.date = "";
          if (dom.dateInput) dom.dateInput.value = "";
        }
        state.page = 1;
        updateUrlParams();
        renderFilterChips();
        fetchViolations();
      });
    }

    // Page Size
    if (dom.pageSizeSelect) {
      dom.pageSizeSelect.addEventListener("change", (e) => {
        state.pageSize = parseInt(e.target.value) || 10;
        state.page = 1;
        updateUrlParams();
        fetchViolations();
      });
    }

    // Clear All Filters button
    if (dom.clearAllBtn) {
      dom.clearAllBtn.addEventListener("click", () => {
        resetFilters();
      });
    }

    // Summary Card Click Filtering
    setupKpiCardClick(dom.kpiTotal, "");
    setupKpiCardClick(dom.kpiPending, "pending");
    setupKpiCardClick(dom.kpiReviewed, "reviewed");
    setupKpiCardClick(dom.kpiResolved, "resolved");

    // Pagination
    if (dom.prevPageBtn) {
      dom.prevPageBtn.addEventListener("click", () => {
        if (state.page > 1) {
          state.page--;
          updateUrlParams();
          fetchViolations();
        }
      });
    }

    if (dom.nextPageBtn) {
      dom.nextPageBtn.addEventListener("click", () => {
        if (state.page < state.totalPages) {
          state.page++;
          updateUrlParams();
          fetchViolations();
        }
      });
    }

    // Modal Events
    if (dom.modalCloseBtn) dom.modalCloseBtn.addEventListener("click", closeModal);
    if (dom.modalBackdrop) {
      dom.modalBackdrop.addEventListener("click", (e) => {
        if (e.target === dom.modalBackdrop) closeModal();
      });
    }

    document.addEventListener("keydown", (e) => {
      if (!dom.modalBackdrop || !dom.modalBackdrop.classList.contains("open")) return;
      if (e.key === "Escape") {
        closeModal();
      } else if (e.key === "ArrowLeft") {
        navigateModal(-1);
      } else if (e.key === "ArrowRight") {
        navigateModal(1);
      }
    });

    if (dom.modalPrevBtn) dom.modalPrevBtn.addEventListener("click", () => navigateModal(-1));
    if (dom.modalNextBtn) dom.modalNextBtn.addEventListener("click", () => navigateModal(1));

    if (dom.modalStatusSelect) {
      dom.modalStatusSelect.addEventListener("change", async (e) => {
        const item = state.items[state.modalIndex];
        if (!item) return;
        const newStatus = e.target.value;
        await updateViolationStatus(item.id, newStatus);
      });
    }
  }

  function setupKpiCardClick(cardEl, statusTarget) {
    if (!cardEl) return;
    cardEl.addEventListener("click", () => {
      // Toggle if already selected
      if (state.status === statusTarget && statusTarget !== "") {
        state.status = "";
      } else {
        state.status = statusTarget;
      }
      state.page = 1;
      if (dom.statusSelect) dom.statusSelect.value = state.status;
      highlightActiveKpiCard(state.status);
      updateUrlParams();
      renderFilterChips();
      fetchViolations();
    });
  }

  function highlightActiveKpiCard(activeStatus) {
    [dom.kpiTotal, dom.kpiPending, dom.kpiReviewed, dom.kpiResolved].forEach((c) => {
      if (c) c.classList.remove("active-filter");
    });

    if (!activeStatus) {
      if (dom.kpiTotal) dom.kpiTotal.classList.add("active-filter");
    } else if (activeStatus === "pending") {
      if (dom.kpiPending) dom.kpiPending.classList.add("active-filter");
    } else if (activeStatus === "reviewed") {
      if (dom.kpiReviewed) dom.kpiReviewed.classList.add("active-filter");
    } else if (activeStatus === "resolved") {
      if (dom.kpiResolved) dom.kpiResolved.classList.add("active-filter");
    }
  }

  function resetFilters() {
    state.q = "";
    state.type = "";
    state.status = "";
    state.date = "";
    state.from = "";
    state.to = "";
    state.page = 1;

    if (dom.searchInput) dom.searchInput.value = "";
    if (dom.searchClearBtn) dom.searchClearBtn.style.display = "none";
    if (dom.typeSelect) dom.typeSelect.value = "";
    if (dom.statusSelect) dom.statusSelect.value = "";
    if (dom.dateInput) dom.dateInput.value = "";
    if (dom.fromInput) dom.fromInput.value = "";
    if (dom.toInput) dom.toInput.value = "";

    highlightActiveKpiCard("");
    updateUrlParams();
    renderFilterChips();
    fetchViolations();
  }

  function renderFilterChips() {
    if (!dom.chipsContainer) return;
    dom.chipsContainer.innerHTML = "";

    const chips = [];
    if (state.q) chips.push({ key: "q", label: `Search: "${state.q}"` });
    if (state.type) chips.push({ key: "type", label: `Type: ${state.type}` });
    if (state.status) chips.push({ key: "status", label: `Status: ${state.status}` });
    if (state.date) chips.push({ key: "date", label: `Date: ${state.date}` });
    if (state.from) chips.push({ key: "from", label: `From: ${state.from}` });
    if (state.to) chips.push({ key: "to", label: `To: ${state.to}` });

    if (chips.length === 0) {
      dom.chipsContainer.style.display = "none";
      return;
    }

    dom.chipsContainer.style.display = "flex";

    chips.forEach((c) => {
      const chip = document.createElement("span");
      chip.className = "vm-filter-chip";
      chip.innerHTML = `
        <span>${escapeHtml(c.label)}</span>
        <button type="button" class="vm-chip-remove" title="Remove filter" data-key="${c.key}">✕</button>
      `;
      chip.querySelector(".vm-chip-remove").addEventListener("click", () => {
        removeFilter(c.key);
      });
      dom.chipsContainer.appendChild(chip);
    });

    const clearAll = document.createElement("button");
    clearAll.className = "vm-clear-all-btn";
    clearAll.innerText = "Clear all";
    clearAll.addEventListener("click", resetFilters);
    dom.chipsContainer.appendChild(clearAll);
  }

  function removeFilter(key) {
    if (key === "q") {
      state.q = "";
      if (dom.searchInput) dom.searchInput.value = "";
      if (dom.searchClearBtn) dom.searchClearBtn.style.display = "none";
    } else if (key === "type") {
      state.type = "";
      if (dom.typeSelect) dom.typeSelect.value = "";
    } else if (key === "status") {
      state.status = "";
      if (dom.statusSelect) dom.statusSelect.value = "";
      highlightActiveKpiCard("");
    } else if (key === "date") {
      state.date = "";
      if (dom.dateInput) dom.dateInput.value = "";
    } else if (key === "from") {
      state.from = "";
      if (dom.fromInput) dom.fromInput.value = "";
    } else if (key === "to") {
      state.to = "";
      if (dom.toInput) dom.toInput.value = "";
    }
    state.page = 1;
    updateUrlParams();
    renderFilterChips();
    fetchViolations();
  }

  // Count-up animation respecting prefers-reduced-motion
  function animateCounter(el, targetVal) {
    if (!el) return;
    const target = parseInt(targetVal) || 0;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      el.innerText = target;
      return;
    }

    const startVal = parseInt(el.getAttribute("data-val") || "0") || 0;
    el.setAttribute("data-val", target);
    const duration = 600;
    const startTime = performance.now();

    function step(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startVal + (target - startVal) * ease);
      el.innerText = current;
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.innerText = target;
      }
    }
    requestAnimationFrame(step);
  }

  // Fetch Violations from Backend API
  async function fetchViolations() {
    state.isLoading = true;
    showLoadingSkeleton();

    const params = new URLSearchParams();
    params.set("page", state.page);
    params.set("page_size", state.pageSize);
    if (state.q) params.set("q", state.q);
    if (state.type) params.set("type", state.type);
    if (state.status) params.set("status", state.status);
    if (state.date) params.set("date", state.date);
    if (state.from) params.set("from", state.from);
    if (state.to) params.set("to", state.to);

    try {
      const res = await fetch(`/api/violations?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      if (!json.ok && !json.items && !json.data) throw new Error(json.error || "Fetch error");

      state.items = json.data || json.items || [];
      state.total = json.total || 0;
      state.page = json.page || 1;
      state.pageSize = json.page_size || json.per_page || 10;
      state.totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));

      if (json.counts) {
        state.counts = json.counts;
        updateKpiCards(json.counts);
      }

      renderTable();
      renderPagination();
    } catch (err) {
      console.error("Failed to fetch violations:", err);
      showErrorState(err.message);
    } finally {
      state.isLoading = false;
    }
  }

  function updateKpiCards(counts) {
    animateCounter(dom.kpiValTotal, counts.total);
    animateCounter(dom.kpiValPending, counts.pending);
    animateCounter(dom.kpiValReviewed, counts.reviewed);
    animateCounter(dom.kpiValResolved, counts.resolved);
  }

  function showLoadingSkeleton() {
    if (!dom.tableBody) return;
    if (dom.emptyState) dom.emptyState.style.display = "none";
    let rowsHtml = "";
    for (let i = 0; i < 5; i++) {
      rowsHtml += `
        <tr>
          <td><div class="vm-skeleton" style="height: 18px; width: 30px; margin: 0 auto;"></div></td>
          <td><div class="vm-skeleton" style="height: 24px; width: 140px;"></div></td>
          <td><div class="vm-skeleton" style="height: 18px; width: 90px;"></div></td>
          <td><div class="vm-skeleton" style="height: 18px; width: 80px;"></div></td>
          <td><div class="vm-skeleton" style="height: 18px; width: 130px;"></div></td>
          <td><div class="vm-skeleton" style="height: 48px; width: 48px; border-radius: 10px;"></div></td>
          <td><div class="vm-skeleton" style="height: 26px; width: 90px; border-radius: 20px;"></div></td>
          <td><div class="vm-skeleton" style="height: 28px; width: 130px;"></div></td>
        </tr>
      `;
    }
    dom.tableBody.innerHTML = rowsHtml;
  }

  function showErrorState(msg) {
    if (!dom.tableBody) return;
    dom.tableBody.innerHTML = `
      <tr>
        <td colspan="8" style="padding: 36px 16px; text-align: center;">
          <div style="font-size: 1.8rem; margin-bottom: 8px;">⚠️</div>
          <h4 style="font-size: 1.1rem; color: var(--danger); margin: 0 0 6px 0; font-weight: 800;">Failed to load violations</h4>
          <p style="color: var(--text-muted); font-size: 0.85rem; margin: 0 0 16px 0;">${escapeHtml(msg || "Server connection error")}</p>
          <button class="btn btn-secondary btn-sm" id="vmRetryBtn" style="font-weight: 700;">🔄 Retry</button>
        </td>
      </tr>
    `;
    const retryBtn = document.getElementById("vmRetryBtn");
    if (retryBtn) retryBtn.addEventListener("click", fetchViolations);
  }

  function renderTable() {
    if (!dom.tableBody) return;

    if (!state.items || state.items.length === 0) {
      dom.tableBody.innerHTML = "";
      if (dom.emptyState) dom.emptyState.style.display = "flex";
      return;
    }

    if (dom.emptyState) dom.emptyState.style.display = "none";

    let rowsHtml = "";
    state.items.forEach((item, idx) => {
      const sno = item.sno || (state.page - 1) * state.pageSize + idx + 1;
      const typeLabel = item.type_label || item.violation_type || "Safety Violation";
      const typeTone = item.type_tone || "danger";
      const typeClass = `vm-type-${item.type_icon || "other"}`;
      const uiStatus = item.ui_status || "Pending";
      const badgeClass = item.status_badge_class || "badge-status-pending";
      const dateFormatted = item.date_formatted || "Not recorded";
      const timeFormatted = item.time_formatted || "Not recorded";
      const location = item.location_display || item.location || "Not specified";
      const isDismissed = Boolean(item.is_dismissed);
      const snapshotUrl = item.snapshot_path ? `/outputs/${item.snapshot_path}` : "";

      rowsHtml += `
        <tr data-id="${item.id}" data-idx="${idx}">
          <td class="vm-col-sno" data-label="S.No">${sno}</td>
          <td data-label="Violation Type">
            <span class="vm-type-chip ${typeClass}">
              <span>${getTypeIconSvg(item.type_icon)}</span>
              <span>${escapeHtml(typeLabel)}</span>
            </span>
          </td>
          <td data-label="Detection Date" class="vm-date-cell">${escapeHtml(dateFormatted)}</td>
          <td data-label="Detection Time" class="vm-time-cell">${escapeHtml(timeFormatted)}</td>
          <td data-label="Location / Dept" class="vm-location-cell" title="${escapeHtml(location)}">
            <span>📍</span> ${escapeHtml(location)}
          </td>
          <td data-label="Detected Image">
            <div class="vm-thumb-wrap" onclick="window.vmController.openModal(${idx})" title="Click to inspect image" tabindex="0" role="button" aria-label="Inspect violation image #${item.id}">
              ${
                snapshotUrl
                  ? `<img src="${snapshotUrl}" alt="Violation #${item.id}" class="vm-thumb-img" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
                     <div class="vm-thumb-fallback" style="display:none;"><span>📷</span>No Image</div>`
                  : `<div class="vm-thumb-fallback"><span>📷</span>No Image</div>`
              }
            </div>
          </td>
          <td data-label="Status">
            <span class="vm-status-pill ${badgeClass}" title="${escapeHtml(item.status_tooltip || uiStatus)}">
              <span>●</span>
              <span>${escapeHtml(uiStatus)}</span>
              ${isDismissed ? '<span class="vm-dismissed-tag" title="Dismissed during review">Dismissed</span>' : ""}
            </span>
          </td>
          <td data-label="Actions" class="vm-action-cell">
            <button class="vm-view-btn" onclick="window.vmController.openModal(${idx})" title="View details and audit">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              <span>View</span>
            </button>
            <select class="vm-status-select" onchange="window.vmController.handleStatusChange(${item.id}, this.value)" aria-label="Change status for violation #${item.id}">
              <option value="pending" ${uiStatus === "Pending" ? "selected" : ""}>Pending</option>
              <option value="reviewed" ${uiStatus === "Reviewed" ? "selected" : ""}>Reviewed</option>
              <option value="resolved" ${uiStatus === "Resolved" ? "selected" : ""}>Resolved</option>
            </select>
          </td>
        </tr>
      `;
    });

    dom.tableBody.innerHTML = rowsHtml;
  }

  function getTypeIconSvg(iconType) {
    if (iconType === "helmet") {
      return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 18a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-2a8 8 0 0 0-16 0v2z"/><path d="M12 4v7"/></svg>`;
    } else if (iconType === "vest") {
      return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h4l4 4 4-4h4v16H4z"/><path d="M4 14h16"/></svg>`;
    } else if (iconType === "equipment") {
      return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    }
    return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
  }

  function renderPagination() {
    if (!dom.pageInfo) return;
    const start = state.total === 0 ? 0 : (state.page - 1) * state.pageSize + 1;
    const end = Math.min(state.page * state.pageSize, state.total);
    dom.pageInfo.innerText = `Showing ${start} to ${end} of ${state.total}`;

    if (dom.prevPageBtn) dom.prevPageBtn.disabled = state.page <= 1;
    if (dom.nextPageBtn) dom.nextPageBtn.disabled = state.page >= state.totalPages;

    if (dom.pageNumbersWrap) {
      dom.pageNumbersWrap.innerHTML = "";
      const maxButtons = 5;
      let startP = Math.max(1, state.page - Math.floor(maxButtons / 2));
      let endP = Math.min(state.totalPages, startP + maxButtons - 1);
      if (endP - startP + 1 < maxButtons) {
        startP = Math.max(1, endP - maxButtons + 1);
      }

      for (let p = startP; p <= endP; p++) {
        const btn = document.createElement("button");
        btn.className = `vm-page-btn ${p === state.page ? "active" : ""}`;
        btn.innerText = p;
        btn.addEventListener("click", () => {
          state.page = p;
          updateUrlParams();
          fetchViolations();
        });
        dom.pageNumbersWrap.appendChild(btn);
      }
    }
  }

  // Handle Status Update via PATCH
  async function handleStatusChange(violationId, newUiStatus) {
    await updateViolationStatus(violationId, newUiStatus);
  }

  async function updateViolationStatus(violationId, newUiStatus) {
    try {
      const res = await fetch(`/api/violations/${violationId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ status: newUiStatus })
      });

      const json = await res.json();
      if (!res.ok || !json.ok) {
        throw new Error(json.error || `Failed with status ${res.status}`);
      }

      showToast(`Violation #${violationId} status updated to ${newUiStatus.toUpperCase()}`, "success");

      // Update counters immediately
      if (json.counts) {
        state.counts = json.counts;
        updateKpiCards(json.counts);
      }

      // Update item in local list and re-render row without full page fetch
      const idx = state.items.findIndex((item) => item.id === violationId);
      if (idx !== -1 && json.data) {
        state.items[idx] = json.data;
        renderTable();
        // If modal is currently open on this item, sync modal details
        if (state.modalIndex === idx) {
          populateModal(state.items[idx]);
        }
      } else {
        // Fallback fetch
        fetchViolations();
      }
    } catch (err) {
      console.error("Status update error:", err);
      showToast(`Error updating status: ${err.message}`, "error");
      // Revert select back to current state
      renderTable();
    }
  }

  // Modal Functions
  function openModal(idx) {
    if (!state.items || !state.items[idx]) return;
    state.modalIndex = idx;
    populateModal(state.items[idx]);
    if (dom.modalBackdrop) {
      dom.modalBackdrop.classList.add("open");
      dom.modalBackdrop.setAttribute("aria-hidden", "false");
    }
    // Trap focus inside modal
    if (dom.modalCloseBtn) dom.modalCloseBtn.focus();
  }

  function closeModal() {
    if (dom.modalBackdrop) {
      dom.modalBackdrop.classList.remove("open");
      dom.modalBackdrop.setAttribute("aria-hidden", "true");
    }
    state.modalIndex = -1;
  }

  function navigateModal(direction) {
    const newIdx = state.modalIndex + direction;
    if (newIdx >= 0 && newIdx < state.items.length) {
      state.modalIndex = newIdx;
      populateModal(state.items[newIdx]);
    }
  }

  function populateModal(item) {
    if (!item) return;

    if (dom.modalTitle) dom.modalTitle.innerText = `Violation Audit #${item.id}`;
    if (dom.modalId) dom.modalId.innerText = `#${item.id}`;
    if (dom.modalType) dom.modalType.innerText = item.type_label || item.violation_type || "Safety Violation";
    if (dom.modalLocation) dom.modalLocation.innerText = item.location_display || item.location || "Not specified";
    if (dom.modalCamera) dom.modalCamera.innerText = item.camera_name || "Zone CCTV";
    if (dom.modalDate) dom.modalDate.innerText = item.date_formatted || "Not recorded";
    if (dom.modalTime) dom.modalTime.innerText = item.time_formatted || "Not recorded";
    if (dom.modalReviewer) dom.modalReviewer.innerText = item.reviewed_by || "System Auditor";
    if (dom.modalNotes) dom.modalNotes.innerText = item.notes || "Automated PPE infraction flagged by spatial YOLO inspection.";

    if (dom.modalStatusSelect) {
      const uiSt = (item.ui_status || "Pending").toLowerCase();
      dom.modalStatusSelect.value = uiSt;
    }

    // Prev/Next buttons state
    if (dom.modalPrevBtn) dom.modalPrevBtn.disabled = state.modalIndex <= 0;
    if (dom.modalNextBtn) dom.modalNextBtn.disabled = state.modalIndex >= state.items.length - 1;

    // Image handling
    const snapshotUrl = item.snapshot_path ? `/outputs/${item.snapshot_path}` : "";
    if (snapshotUrl) {
      dom.modalImg.src = snapshotUrl;
      dom.modalImg.style.display = "block";
      dom.modalImgFallback.style.display = "none";
      dom.modalImg.onerror = () => {
        dom.modalImg.style.display = "none";
        dom.modalImgFallback.style.display = "flex";
      };
    } else {
      dom.modalImg.style.display = "none";
      dom.modalImgFallback.style.display = "flex";
    }
  }

  // Toast Notification
  function showToast(message, type = "success") {
    if (!dom.toastContainer) return;
    const toast = document.createElement("div");
    toast.className = `vm-toast ${type === "error" ? "vm-toast-error" : ""}`;
    toast.setAttribute("role", "alert");
    const icon = type === "error" ? "⚠️" : "✅";

    toast.innerHTML = `
      <span class="vm-toast-icon">${icon}</span>
      <p class="vm-toast-msg">${escapeHtml(message)}</p>
    `;

    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-10px)";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Expose methods for inline HTML event handlers
  window.vmController = {
    openModal,
    closeModal,
    handleStatusChange,
    fetchViolations,
    resetFilters
  };
})();
