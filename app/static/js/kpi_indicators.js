/**
 * SafeSight AI — Extended 4 Core Safety Indicators Renderer
 * Hydrates Open Incidents, Reports Generated, Active Safety Alerts,
 * and Pending Reviews independently with unavailable/error state support.
 */
(function () {
  const EXTENDED_CARDS = [
    {
      id: "kpiCardOpenIncidents",
      key: "open_incidents",
      title: "Open Incidents",
    },
    {
      id: "kpiCardReportsGenerated",
      key: "reports_generated",
      title: "Reports Generated",
    },
    {
      id: "kpiCardActiveAlerts",
      key: "active_safety_alerts",
      title: "Active Safety Alerts",
    },
    {
      id: "kpiCardPendingReviews",
      key: "pending_reviews",
      title: "Pending Reviews",
    },
  ];

  function setIndicatorCardState(card, state) {
    if (!card) return;
    card.classList.remove(
      "kpi-state-ready",
      "kpi-state-loading",
      "kpi-state-error",
      "kpi-state-empty",
      "kpi-state-unavailable"
    );
    card.classList.add("kpi-state-" + state);
  }

  window.renderExtendedWorkplaceKpis = function (data) {
    if (!data) return;
    EXTENDED_CARDS.forEach(function (cfg) {
      const card = document.getElementById(cfg.id);
      if (!card) return;

      const val = data[cfg.key];
      const valEl = document.getElementById(cfg.id + "_val");

      if (val === null || val === undefined) {
        setIndicatorCardState(card, "unavailable");
        card.setAttribute("aria-label", cfg.title + ": No data source yet");
      } else {
        setIndicatorCardState(card, "ready");
        if (valEl) {
          if (typeof window.animateKpiNumber === "function") {
            window.animateKpiNumber(valEl, val, false);
          } else {
            valEl.innerText = val;
          }
        }
        card.setAttribute("aria-label", cfg.title + ": " + val);
      }
    });
  };

  window.EXTENDED_KPI_CARD_IDS = EXTENDED_CARDS.map(function (c) {
    return c.id;
  });
})();
