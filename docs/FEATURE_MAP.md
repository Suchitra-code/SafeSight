# SafeSight AI — Feature Map (Milestone 5)

> **Note:** No screenshots were attached to this prompt. Features are inferred from the spec's Section 7 (LangGraph Investigation), Section 8 (Other features), Section 4 (Design System), and Section 9 (Integration). Assumptions are listed at the bottom.

## Feature Traceability Table

| # | Feature | Source | Exists? | Plan | Route/Page | Backend | Frontend | DB Change | Test | Status |
|---|---------|--------|---------|------|-----------|---------|----------|-----------|------|--------|
| 1 | Sunrise Garden colour theme | Spec §3 | NO | Build new `theme.css` | All pages | — | `static/css/theme.css` | — | `test_no_forbidden_colors.py` | TODO |
| 2 | Reusable component library | Spec §4.4 | NO | Build new | `/ui-kit` (dev) | — | `static/css/components.css` | — | Manual | TODO |
| 3 | Animation system | Spec §4.5 | PARTLY (M4 has some) | Extend | All pages | — | `static/css/animations.css` | — | Manual | TODO |
| 4 | UI utilities (count-up, toast, tour, cmd palette) | Spec §4.6 | PARTLY (toast exists) | Extend | All pages | — | `static/js/ui.js` | — | Manual | TODO |
| 5 | Local fonts (Poppins + Inter) | Spec §4.2 | NO (CDN) | Download to `static/fonts/` | All pages | — | `base.html`, `theme.css` | — | — | TODO |
| 6 | Colour checker tool | Spec §3.6 | NO | Build new | — | `tools/check_colors.py` | — | — | `test_no_forbidden_colors.py` | TODO |
| 7 | Re-theme: Sidebar + Top bar | Spec §5 | YES (navy) | Re-colour only | All pages | — | `base.html`, `style.css` | — | Smoke test | TODO |
| 8 | Re-theme: Home/Landing | Spec §5 | YES | Re-colour only | `/` | — | `landing.html` | — | Smoke test | TODO |
| 9 | Re-theme: Upload page | Spec §5 | YES | Re-colour only | `/upload` | — | `upload.html` | — | Smoke test | TODO |
| 10 | Re-theme: Dashboard + charts | Spec §5 | YES | Fix chart colours | `/dashboard` | — | `dashboard.html`, `dashboard.js` | — | Smoke test | TODO |
| 11 | Re-theme: Live Monitor | Spec §5 | YES | Re-colour only | `/live` | — | `live.html`, `live.js` | — | Smoke test | TODO |
| 12 | Re-theme: Events page | Spec §5 | YES | Re-colour only | `/events` | — | `events.html`, `events.js` | — | Smoke test | TODO |
| 13 | Re-theme: Documents + Knowledge + Repos | Spec §5 | YES | Re-colour only | `/documents`, `/knowledge`, `/repositories` | — | Templates + JS | — | Smoke test | TODO |
| 14 | Re-theme: AI Assistant (Copilot/RAG) | Spec §5 | YES | Re-colour only | `/assistant` | — | `assistant.html` | — | Smoke test | TODO |
| 15 | Re-theme: Investigations | Spec §5 | YES | Re-colour only | `/investigations` | — | Templates | — | Smoke test | TODO |
| 16 | Re-theme: Mission Control (M4) | Spec §5 | YES (dark theme) | Convert to light | `/command-center` | — | `command_center.html`, `command_center.css`, `cc/*.js` | — | Smoke test | TODO |
| 17 | Re-theme: Reports page | Spec §5 | YES | Re-colour only | `/reports` | — | `reports.html` | — | Smoke test | TODO |
| 18 | Re-theme: Login/Register | Spec §5 | YES | Re-colour only | `/login`, `/register` | — | `login.html`, `register.html` | — | Smoke test | TODO |
| 19 | Annotated image box colours | Spec §3.5.6 | YES (may be blue/black) | Fix colours | — | `detector.py` | — | — | Manual | TODO |
| 20 | PDF report colours | Spec §3.5.8 | YES (may be black) | Fix palette | — | `incident_report_pdf.py` | — | — | Test PDF | TODO |
| 21 | Enhanced AI Investigation (10 nodes) | Spec §7 | PARTLY (M3 has 7 nodes) | Extend | `/investigations` | `app/agents/*` | Investigation UI | `investigations` table extension | Node tests | TODO |
| 22 | Investigation UI: live pipeline, risk gauge, timeline | Spec §7.3 | PARTLY | Extend | `/investigations/<id>` | — | `investigation_detail.html` | — | Smoke test | TODO |
| 23 | Investigation PDF with palette colours | Spec §7.4 | YES | Fix colours | — | `incident_report_pdf.py` | — | — | Test PDF | TODO |
| 24 | "Investigate with AI" button on violation cards | Spec §9 | PARTLY | Wire up | `/events` | — | `events.html` | — | Manual | TODO |
| 25 | Guided first-run tour | Spec §4.6 | NO | Build new | All pages | — | `static/js/ui.js` | — | Manual | TODO |
| 26 | Global command palette (Ctrl+K) | Spec §4.6 | PARTLY (M4 Ctrl+K) | Extend to global | All pages | — | `static/js/ui.js` | — | Manual | TODO |
| 27 | Cross-filtering on dashboard | Spec §4.6 | PARTLY (M4 has it) | Add to M1 dashboard | `/dashboard` | — | `dashboard.js` | — | Manual | TODO |
| 28 | Confetti on resolve | Spec §4.5.9 | NO | Build new | Investigations | — | `static/js/ui.js` | — | Manual | TODO |
| 29 | Demo Mode (re-coloured) | Spec §4.6 | YES (M4) | Re-colour | `/command-center` | — | `demo_mode.js` | — | Manual | TODO |
| 30 | Health page: colour checker status | Spec §9 | PARTLY | Add field | `/api/health` | `health.py` | — | — | Test | TODO |
| 31 | Toast system (re-coloured) | Spec §4.4 | YES | Re-colour | All pages | — | `base.html` | — | — | TODO |
| 32 | Remove dark mode toggle | Spec §3.1 | YES (exists) | Remove toggle, force light | All pages | — | `base.html` | — | — | TODO |

## Assumptions (no screenshots provided)
1. The "screenshots from mam" were not attached. All features are derived from the textual spec sections 3-9.
2. The layout structure (sidebar + topbar + content) stays the same; only colours, fonts, and animations change.
3. The existing M3 investigation graph (7 nodes) will be extended to 10 nodes as specified in Section 7.2.
4. No new pages beyond what already exists, except `/ui-kit` for development testing (can be removed).
5. Where the spec says "match the screenshot layout", we follow the textual description instead since no screenshots are available.
