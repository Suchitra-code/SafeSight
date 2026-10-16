/**
 * SafeSight AI – Events & Violation Verification Controller
 * Handles live filtering, search, pagination, drawer updates, and status mutations.
 */

let currentPage = 1;
let currentTab = "all";
let currentView = "grid";
let activeViolationId = null;

document.addEventListener("DOMContentLoaded", () => {
  loadEvents();

  // Tab Filtering
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => {
        b.classList.remove("active", "btn-primary");
        b.classList.add("btn-secondary");
      });
      btn.classList.add("active", "btn-primary");
      btn.classList.remove("btn-secondary");

      currentTab = btn.getAttribute("data-tab");
      currentPage = 1;
      loadEvents();
    });
  });

  // Apply Left Filters
  document.getElementById("applyEventFiltersBtn")?.addEventListener("click", () => {
    currentPage = 1;
    loadEvents();
  });

  // Search input
  document.getElementById("searchBtn")?.addEventListener("click", () => {
    currentPage = 1;
    loadEvents();
  });
  document.getElementById("searchInput")?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      currentPage = 1;
      loadEvents();
    }
  });

  // Sort change
  document.getElementById("sortBy")?.addEventListener("change", () => {
    currentPage = 1;
    loadEvents();
  });

  // View toggle
  document.getElementById("viewGridBtn")?.addEventListener("click", () => {
    currentView = "grid";
    document.getElementById("viewGridBtn").style.background = "var(--bg-surface)";
    document.getElementById("viewListBtn").style.background = "transparent";
    renderEvents(window.lastLoadedItems || []);
  });
  document.getElementById("viewListBtn")?.addEventListener("click", () => {
    currentView = "list";
    document.getElementById("viewListBtn").style.background = "var(--bg-surface)";
    document.getElementById("viewGridBtn").style.background = "transparent";
    renderEvents(window.lastLoadedItems || []);
  });

  // Export CSV
  document.getElementById("exportCsvBtn")?.addEventListener("click", () => {
    window.location.href = `/api/export/violations-csv?${buildQueryString()}`;
  });

  // Pagination
  document.getElementById("prevPageBtn")?.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      loadEvents();
    }
  });
  document.getElementById("nextPageBtn")?.addEventListener("click", () => {
    currentPage++;
    loadEvents();
  });

  // Drawer Close
  document.getElementById("drawerCloseBtn")?.addEventListener("click", closeDrawer);
  document.getElementById("drawerOverlay")?.addEventListener("click", closeDrawer);

  // Drawer Save Status
  document.getElementById("saveDrawerStatusBtn")?.addEventListener("click", async () => {
    if (!activeViolationId) return;

    const newStatus = document.getElementById("drawerStatusSelect").value;
    const reviewer = document.getElementById("drawerReviewer").value;
    const notes = document.getElementById("drawerNotes").value;

    const btn = document.getElementById("saveDrawerStatusBtn");
    btn.disabled = true;
    btn.innerText = "Saving...";

    try {
      const res = await fetch(`/api/violations/${activeViolationId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus, reviewed_by: reviewer, notes: notes })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Update failed");

      showToast(`Status updated to '${newStatus}'!`, "success");
      closeDrawer();
      loadEvents(); // Reload cards to reflect change
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerText = "Save Changes & Persist Status";
    }
  });
});

function buildQueryString() {
  const params = new URLSearchParams();
  params.append("page", currentPage);
  params.append("per_page", 12);

  const search = document.getElementById("searchInput")?.value.trim();
  if (search) params.append("search", search);

  const sortBy = document.getElementById("sortBy")?.value;
  if (sortBy) params.append("sort_by", sortBy);

  // Types filter
  if (currentTab !== "all") {
    params.append("type", currentTab);
  } else {
    document.querySelectorAll(".filter-type:checked").forEach(cb => {
      params.append("type", cb.value);
    });
  }

  // Statuses filter
  document.querySelectorAll(".filter-status:checked").forEach(cb => {
    params.append("status", cb.value);
  });

  // Cameras filter
  document.querySelectorAll(".filter-cam:checked").forEach(cb => {
    params.append("camera", cb.value);
  });

  return params.toString();
}

async function loadEvents() {
  const container = document.getElementById("eventsContainer");
  if (!container) return;

  container.innerHTML = `<div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--text-muted);">Loading events...</div>`;

  try {
    const res = await fetch(`/api/violations?${buildQueryString()}`);
    const data = await res.json();

    window.lastLoadedItems = data.items || [];
    renderEvents(data.items || []);

    // Update pagination
    const total = data.total || 0;
    const page = data.page || 1;
    const totalPages = data.total_pages || 1;

    document.getElementById("pageInfo").innerText = `Page ${page} of ${totalPages} (${total} total records)`;
    document.getElementById("prevPageBtn").disabled = (page <= 1);
    document.getElementById("nextPageBtn").disabled = (page >= totalPages);

    // Update floating toast text
    const toastText = document.getElementById("floatingLiveText");
    if (toastText) {
      toastText.innerText = `Currently there are ${total} recorded infractions`;
    }
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--danger);">Failed to load events: ${err}</div>`;
  }
}

function renderEvents(items) {
  const container = document.getElementById("eventsContainer");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; padding: 60px; text-align: center; color: var(--text-muted); background: var(--bg-surface); border-radius: var(--radius-md);">No violations matched the selected criteria.</div>`;
    return;
  }

  if (currentView === "list") {
    container.style.gridTemplateColumns = "1fr";
  } else {
    container.style.gridTemplateColumns = "repeat(auto-fill, minmax(320px, 1fr))";
  }

  container.innerHTML = items.map(v => {
    const sevPill = v.severity === "HIGH" ? "pill-high" : (v.severity === "MEDIUM" ? "pill-medium" : "pill-low");
    const statusClass = `status-${(v.status || "detected").replace(" ", "-")}`;
    const imgUrl = v.snapshot_path ? `/outputs/${v.snapshot_path}` : "/static/img/placeholder_worker.jpg";

    return `
      <div class="event-card" onclick="openDrawer(${v.id})">
        <img class="event-thumb" src="${imgUrl}" alt="Snap" onerror="this.src='/static/img/placeholder_worker.jpg'">
        <div class="event-body">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">
              <span class="pill ${sevPill}">${v.severity}</span>
              <span class="badge-status ${statusClass}">${(v.status || "detected").toUpperCase()}</span>
            </div>
            <h4 style="font-size: 14px; font-weight: 700; color: var(--text-main); margin-bottom: 2px;">
              Incorrect PPE – No ${v.violation_type.charAt(0).toUpperCase() + v.violation_type.slice(1)}
            </h4>
            <p style="font-size: 11px; color: var(--text-muted); margin: 0;">${v.camera_name} • ${v.location}</p>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-dim); margin-top: 8px;">
            <span>${(v.detected_at || '').slice(0, 16)}</span>
            <span style="color: var(--accent); font-weight: 600;">Inspect →</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

async function openDrawer(violationId) {
  activeViolationId = violationId;
  const drawer = document.getElementById("sideDrawer");
  const overlay = document.getElementById("drawerOverlay");

  try {
    const res = await fetch(`/api/violations/${violationId}`);
    const v = await res.json();

    document.getElementById("drawerTitle").innerText = `Violation #${v.id}`;
    document.getElementById("drawerId").innerText = `${v.camera_name} • ${v.location}`;
    document.getElementById("drawerType").innerText = v.violation_type.toUpperCase();
    document.getElementById("drawerSeverity").innerText = v.severity;
    document.getElementById("drawerSeverity").className = `pill ${v.severity === 'HIGH' ? 'pill-high' : 'pill-medium'}`;
    document.getElementById("drawerConfidence").innerText = `${Math.round((v.confidence || 0.9) * 100)}%`;
    document.getElementById("drawerCamera").innerText = v.camera_name;
    document.getElementById("drawerLocation").innerText = v.location;
    document.getElementById("drawerTime").innerText = v.detected_at;

    document.getElementById("drawerStatusSelect").value = v.status || "detected";
    document.getElementById("drawerReviewer").value = v.reviewed_by || "";
    document.getElementById("drawerNotes").value = v.notes || "";

    const drawerImg = document.getElementById("drawerImg");
    drawerImg.src = v.snapshot_path ? `/outputs/${v.snapshot_path}` : "/static/img/placeholder_worker.jpg";

    drawer.classList.add("open");
    overlay.classList.add("open");
  } catch (err) {
    showToast("Error loading violation details: " + err, "error");
  }
}

function closeDrawer() {
  document.getElementById("sideDrawer")?.classList.remove("open");
  document.getElementById("drawerOverlay")?.classList.remove("open");
  activeViolationId = null;
}
