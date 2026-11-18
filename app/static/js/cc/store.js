/**
 * Central State Store for Mission Control (Section 8.2).
 * Enables synchronized, reactive interaction across all dashboard widgets.
 */
class CommandStore {
  constructor() {
    this.filters = {
      zone: null,
      violationType: null,
      severity: null,
      dateRange: "7d"
    };
    this.listeners = [];
    this.activeRunId = null;
    this._loadFromUrl();
  }

  _loadFromUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("zone")) this.filters.zone = params.get("zone");
    if (params.get("type")) this.filters.violationType = params.get("type");
    if (params.get("severity")) this.filters.severity = params.get("severity");
  }

  _syncToUrl() {
    const params = new URLSearchParams();
    if (this.filters.zone) params.set("zone", this.filters.zone);
    if (this.filters.violationType) params.set("type", this.filters.violationType);
    if (this.filters.severity) params.set("severity", this.filters.severity);
    const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
    window.history.replaceState({}, '', newUrl);
  }

  subscribe(fn) {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter(l => l !== fn);
    };
  }

  setFilter(key, value) {
    if (this.filters[key] === value) return;
    this.filters[key] = value;
    this._syncToUrl();
    this.notify();
  }

  clearFilters() {
    this.filters = {
      zone: null,
      violationType: null,
      severity: null,
      dateRange: "7d"
    };
    this._syncToUrl();
    this.notify();
  }

  notify() {
    this.listeners.forEach(fn => fn(this.filters));
  }
}

export const store = new CommandStore();
