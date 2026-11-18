/**
 * palette.js — Color theme helpers for Mission Control (Milestone 5 - Sunrise Garden).
 *
 * Strictly NO blue, NO black. 100% compliant with theme.css.
 */

'use strict';

export function getTheme() {
  return 'light';
}

const PALETTES = {
  light: {
    // Surface layers
    bg: '#FFF7EE',
    surface: '#FFFFFF',
    card: '#FFFFFF',
    border: '#F3D9CF',

    // Text
    textPrimary: '#4A1D2F',
    textSecondary: '#6B3A4D',
    textMuted: '#9A6B7E',

    // Brand
    accent: '#FF6B4A',
    accentHover: '#FF8566',
    navy: '#FF6B4A',

    // Status
    success: '#22B573',
    warning: '#FF9F1C',
    danger: '#E53950',
    info: '#FF4D8D', // pink

    // Chart defaults
    gridLine: '#F3D9CF',
    chartText: '#6B3A4D',

    // Trust meter gradient stops [low, mid, high]
    trustLow: '#E53950',
    trustMid: '#FF9F1C',
    trustHigh: '#22B573',

    // Heatmap cell colours [min … max]
    heatMin: '#FFE3D3',
    heatMax: '#FF6B4A',

    // Pipeline node states
    nodeIdle: '#F3D9CF',
    nodeActive: '#FF6B4A',
    nodeDone: '#22B573',
    nodeError: '#E53950',

    // Zone compliance colours
    zoneGood: '#22B573',
    zoneWarn: '#FF9F1C',
    zoneBad: '#E53950',
    zoneUnknown: '#9A6B7E',
  },
  dark: {
    // Fallback identical to light (dark forbidden)
    bg: '#FFF7EE',
    surface: '#FFFFFF',
    card: '#FFFFFF',
    border: '#F3D9CF',
    textPrimary: '#4A1D2F',
    textSecondary: '#6B3A4D',
    textMuted: '#9A6B7E',
    accent: '#FF6B4A',
    accentHover: '#FF8566',
    navy: '#FF6B4A',
    success: '#22B573',
    warning: '#FF9F1C',
    danger: '#E53950',
    info: '#FF4D8D',
    gridLine: '#F3D9CF',
    chartText: '#6B3A4D',
    trustLow: '#E53950',
    trustMid: '#FF9F1C',
    trustHigh: '#22B573',
    heatMin: '#FFE3D3',
    heatMax: '#FF6B4A',
    nodeIdle: '#F3D9CF',
    nodeActive: '#FF6B4A',
    nodeDone: '#22B573',
    nodeError: '#E53950',
    zoneGood: '#22B573',
    zoneWarn: '#FF9F1C',
    zoneBad: '#E53950',
    zoneUnknown: '#9A6B7E',
  }
};

export const C = new Proxy(
  {},
  {
    get(_target, key) {
      return PALETTES.light[key] ?? PALETTES.light.accent;
    },
  }
);

const _listeners = new Set();
export function onThemeChange(fn) {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

export function trustColor(score) {
  if (score >= 80) return C.trustHigh;
  if (score >= 50) return C.trustMid;
  return C.trustLow;
}

export function zoneColor(ratio) {
  if (ratio >= 0.9) return C.zoneGood;
  if (ratio >= 0.7) return C.zoneWarn;
  if (ratio < 0) return C.zoneUnknown;
  return C.zoneBad;
}

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
