# SafeSight AI — Design Principles
_Created: 2026-11-22. Applies to the entire SafeSight AI project forever._

---

## 1. The Golden Rule: Enhance, Never Change

**Whenever a reference image or screenshot is uploaded, keep its style and appearance exactly as shown — the same layout, sections, components, sidebar items, chart types, wording, and overall concept — then enhance only the finish**: more elegant colours, richer backgrounds, refined typography, and finer details.

This rule overrides any suggestion (including AI-generated) to change layouts, move components, rename sections, or add new chart types. The concept is locked. The quality of execution is what improves.

---

## 2. Colour Rule (Highest Priority — From Project Mentor)

**NO black and NO blue anywhere in the application.**

- **Forbidden hues:** black, near-black, charcoal, dark greys, dark-mode backgrounds, navy, blue, indigo, cyan, teal, and any purple with hue 175°–275° and saturation > 12%.
- **Darkest text allowed:** deep plum `#4A1D2F` (lightness ≈ 20%).
- Use `tools/check_colors.py` before every commit. It must report **0 forbidden colours**.
- Photos and real evidence images keep their own colours; everything around them follows the rule.

---

## 3. The Rosewood & Champagne Design System

The active palette is **Rosewood and Champagne** — a refinement of the original Sunrise Garden. It retains the coral/pink/orange/green energy but shifts saturated brights into richer, more elegant tones.

| Role | Variable | Value |
|---|---|---|
| Page ivory | `--bg-page` | `#FFFBF5` |
| Cream surface | `--bg-cream` | `#FFF6EA` |
| Blush | `--bg-blush` | `#FDE9E4` |
| Champagne | `--bg-champagne` | `#F6E7CB` |
| Gold accent | `--gold` | `#C9A24B` |
| Soft gold | `--gold-soft` | `#E8D3A0` |
| Coral (primary) | `--coral` | `#E2634B` |
| Rose | `--rose` | `#D94F70` |
| Orchid | `--orchid` | `#A83E97` |
| Amber | `--amber` | `#E8A33D` |
| Emerald (safe) | `--emerald` | `#1F9D6E` |
| Soft emerald | `--emerald-soft` | `#D9F2E6` |
| Burgundy (critical) | `--burgundy` | `#B8283F` |
| Soft burgundy | `--burgundy-soft` | `#FBE1E5` |
| Text strong | `--text-strong` | `#4A1D2F` |
| Text main | `--text-main` | `#6B3A4D` |
| Text soft | `--text-soft` | `#8A6577` |
| Border warm | `--border` | `#F1DED2` |
| Border gold | `--border-gold` | `rgba(201,162,75,0.30)` |

**Semantic Meaning:**
- Safe / Resolved = Emerald
- Violation / Critical = Burgundy / Rose
- Warning / Pending = Amber
- AI features = Orchid / Rose

---

## 4. Typography

| Role | Font | Size | Weight |
|---|---|---|---|
| Body / UI | Manrope (local), system fallback | 14–15px | 400–500 |
| Display headings | Fraunces (local), Playfair Display fallback | 28–44px | 700 |
| Card titles | Manrope semibold | 16–18px | 600 |
| KPI numbers | Fraunces, tabular lining | 36–44px | 700 |
| Small uppercase labels | Manrope | 11–12px, 0.08em tracking | 500 |

Font files must be local WOFF2 with `font-display: swap`. No external CDN font calls. App must work offline.

---

## 5. Backgrounds

- Page: ivory `#FFFBF5` with a soft blush–peach–champagne mesh gradient plus 2–3 slow blurred floating blobs (transform + opacity only; hidden for `prefers-reduced-motion`).
- Sidebar: ivory-to-blush vertical gradient, thin gold hairline right edge, soft logo glow.
- Cards: white/light surface, 24px radius, 1px warm border or gold hairline, layered warm shadow, subtle hover lift 4px.
- Shadows: always warm-tinted (`rgba(74,29,47,...)` or `rgba(226,99,75,...)`), never `rgba(0,0,0,...)`.

---

## 6. Charts

- Chart.js and Plotly defaults must be explicitly overridden: no default blue/grey/black.
- `Chart.defaults.color = '#6B3A4D'` (text-main), grid lines `#F1DED2`, tooltip background `#FFFBF5` with plum text.
- PPE category fixed colours: Helmet = coral `#E2634B`, Safety Vest = gold `#C9A24B`, Goggles = rose `#D94F70`, Other = orchid `#A83E97`.
- With PPE = emerald `#1F9D6E`, Without PPE = burgundy `#B8283F`.
- Lines: 2–2.5px, smooth, area fills 10–18% opacity gradient. No filled overlapping series at full opacity.
- Tooltips: cream background, plum text, warm border, 8px radius.

---

## 7. No-Regression Contract

- Never delete, rename, or break existing routes, endpoints, DB tables, element IDs or classes used by JavaScript or tests.
- Add new CSS classes; never remove old ones that may be in use.
- Database changes: additive only (`IF NOT EXISTS`, nullable columns).
- Run the full test suite (`pytest tests/`) and smoke test before every commit. Zero regressions permitted.

---

_Last updated: 2026-11-22. Source of truth for all visual decisions._
