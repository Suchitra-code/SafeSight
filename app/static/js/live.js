/**
 * SafeSight AI – Live Stream Surveillance Controller
 * Dynamically switches MJPEG camera streams and polls live metrics/events.
 */

document.addEventListener("DOMContentLoaded", () => {
  const cameraCards = document.querySelectorAll(".camera-card");
  const mjpegFeed = document.getElementById("mjpegFeed");
  const activeCamHeader = document.getElementById("activeCamHeader");
  const activeZoneHeader = document.getElementById("activeZoneHeader");

  // Camera channel switcher
  cameraCards.forEach(card => {
    card.addEventListener("click", () => {
      cameraCards.forEach(c => {
        c.classList.remove("active");
        c.style.borderColor = "var(--border-color)";
      });
      card.classList.add("active");
      card.style.borderColor = "var(--accent)";

      const srcId = card.getAttribute("data-source");
      const camName = card.getAttribute("data-name");
      const zone = card.getAttribute("data-zone");

      if (activeCamHeader) activeCamHeader.innerText = camName;
      if (activeZoneHeader) activeZoneHeader.innerText = `(${zone})`;

      // Switch feed URL
      if (mjpegFeed) {
        mjpegFeed.src = `/video_feed/${srcId}`;
      }
    });
  });

  // Periodic metrics refresh (every 3.5 seconds)
  setInterval(async () => {
    try {
      const res = await fetch("/api/analytics/kpi");
      const kpi = await res.json();
      const compEl = document.getElementById("liveComplianceRate");
      const workEl = document.getElementById("liveWorkersCount");
      const violEl = document.getElementById("liveViolationsCount");

      if (compEl) compEl.innerText = `${kpi.compliance_percent}%`;
      if (workEl) workEl.innerText = kpi.total_people;
      if (violEl) violEl.innerText = kpi.total_violations;

      // Update incident stream
      const vRes = await fetch("/api/violations?per_page=6");
      const vData = await vRes.json();
      const container = document.getElementById("liveIncidentsList");
      if (container && vData.items) {
        container.innerHTML = vData.items.map(v => `
          <div style="display: flex; gap: 10px; align-items: center; padding: 8px; background: var(--bg-surface-alt); border-radius: 6px; border-left: 3px solid ${v.severity === 'HIGH' ? 'var(--danger)' : 'var(--warning)'};">
            <div style="flex-grow: 1;">
              <div style="display: flex; justify-content: space-between;">
                <span style="font-size: 11px; font-weight: 700; color: var(--text-main);">${v.violation_type.toUpperCase()}</span>
                <span style="font-size: 10px; color: var(--text-muted);">${(v.detected_at || '').slice(11, 16)}</span>
              </div>
              <p style="font-size: 10px; color: var(--text-muted); margin: 0;">${v.camera_name}</p>
            </div>
          </div>
        `).join("");
      }
    } catch (e) {
      // Background poll silently retry
    }
  }, 3500);
});
