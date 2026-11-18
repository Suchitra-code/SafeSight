/**
 * palette.js — Color theme helpers for Mission Control dark/light mode.
 *
 * Reads the current theme from <html data-theme="..."> and exposes colour
 * constants used by Chart.js, the SVG site map, the trust meter, and the
 * heatmap so that every widget stays consistent with the global theme.
 *
 * Usage:
 *   import { getTheme, C, onThemeChange } from './palette.js';
 *   ctx.fillStyle = C.accent;          // orange accent
 *   onThemeChange(() => chart.update()); // re-render on toggle
 */

'use strict';

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Return the current theme name ('dark' | 'light'). */
function getTheme() {
  return document.documentElement.getAttribute('data-theme') || 'dark';
}

// ---------------------------------------------------------------------------
// Colour palettes (one object per theme)
// ---------------------------------------------------------------------------

const PALETTES = {
  dark: {
    // Surface layers
    bg: '#0a0f1e',
    surface: '#12192e',
    card: '#1a2440',
    border: '#2a3a5c',

    // Text
    textPrimary: '#e8ecf5',
    textSecondary: '#8899bb',
    textMuted: '#556080',

    // Brand
    accent: '#ff6b2b',       // SafeSight orange
    accentHover: '#ff8c55',
    navy: '#1a2a4a',

    // Status
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',

    // Chart defaults
    gridLine: 'rgba(42,58,92,0.6)',
    chartText: '#8899bb',

    // Trust meter gradient stops  [low, mid, high]
    trustLow: '#ef4444',
    trustMid: '#f59e0b',
    trustHigh: '#22c55e',

    // Heatmap cell colours [min … max]
    heatMin: '#12192e',
    heatMax: '#ff6b2b',

    // Pipeline node states
    nodeIdle: '#2a3a5c',
    nodeActive: '#ff6b2b',
    nodeDone: '#22c55e',
    nodeError: '#ef4444',

    // Zone compliance colours
    zoneGood: '#22c55e',
    zoneWarn: '#f59e0b',
    zoneBad: '#ef4444',
    zoneUnknown: '#556080',
  },

  light: {
    bg: '#f0f4ff',
    surface: '#ffffff',
    card: '#ffffff',
    border: '#d1d9f0',

    textPrimary: '#1a2440',
    textSecondary: '#4a5a80',
    textMuted: '#8899bb',

    accent: '#e55a1c',
    accentHover: '#c94a10',
    navy: '#1a2a4a',

    success: '#16a34a',
    warning: '#d97706',
    danger: '#dc2626',
    info: '#2563eb',

    gridLine: 'rgba(209,217,240,0.8)',
    chartText: '#4a5a80',

    trustLow: '#dc2626',
    trustMid: '#d97706',
    trustHigh: '#16a34a',

    heatMin: '#e8ecf5',
    heatMax: '#e55a1c',

    nodeIdle: '#d1d9f0',
    nodeActive: '#e55a1c',
    nodeDone: '#16a34a',
    nodeError: '#dc2626',

    zoneGood: '#16a34a',
    zoneWarn: '#d97706',
    zoneBad: '#dc2626',
    zoneUnknown: '#8899bb',
  },
};

// ---------------------------------------------------------------------------
// Live colour proxy — always reflects current theme without re-import
// ---------------------------------------------------------------------------

/**
 * C — a Proxy that returns the correct palette value for the active theme.
 * Access any key from PALETTES directly: `C.accent`, `C.surface`, etc.
 *
 * @type {typeof PALETTES.dark}
 */
export const C = new Proxy(
  {},
  {
    get(_target, key) {
      const theme = getTheme();
      const palette = PALETTES[theme] ?? PALETTES.dark;
      return palette[key] ?? PALETTES.dark[key];
    },
  }
);

// ---------------------------------------------------------------------------
// Theme change subscription
// ---------------------------------------------------------------------------

/** @type {Set<() => void>} */
const _listeners = new Set();

/**
 * Subscribe to theme changes.  The callback is called whenever the theme
 * attribute on <html> changes.  Returns an unsubscribe function.
 *
 * @param {() => void} fn
 * @returns {() => void}  Call to remove the listener.
 */
export function onThemeChange(fn) {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

// Watch the <html> element for data-theme mutations.
const _observer = new MutationObserver(() => {
  _listeners.forEach((fn) => {
    try {
      fn();
    } catch (err) {
      console.warn('[palette] theme change listener threw:', err);
    }
  });
});

_observer.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ['data-theme'],
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Map a 0–100 trust score to a CSS colour string.
 * @param {number} score
 * @returns {string}
 */
export function trustColor(score) {
  if (score >= 80) return C.trustHigh;
  if (score >= 50) return C.trustMid;
  return C.trustLow;
}

/**
 * Map a compliance ratio (0–1) to a zone status colour.
 * @param {number} ratio  Compliance ratio, e.g. 0.85
 * @returns {string}
 */
export function zoneColor(ratio) {
  if (ratio >= 0.9) return C.zoneGood;
  if (ratio >= 0.7) return C.zoneWarn;
  if (ratio < 0) return C.zoneUnknown;
  return C.zoneBad;
}

/**
 * Interpolate between two hex colours.
 * Used by the heatmap to blend between heatMin and heatMax.
 *
 * @param {string} hex1  Start colour (#rrggbb)
 * @param {string} hex2  End colour   (#rrggbb)
 * @param {number} t     0 … 1
 * @returns {string}
 */
export function lerp(hex1, hex2, t) {
  const parse = (h) => [
    parseInt(h.slice(1, 3), 16),
    parseInt(h.slice(3, 5), 16),
    parseInt(h.slice(5, 7), 16),
  ];
  const [r1, g1, b1] = parse(hex1);
  const [r2, g2, b2] = parse(hex2);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r},${g},${b})`;
}

export { getTheme };
