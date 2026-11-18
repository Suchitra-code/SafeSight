# SafeSight AI: Milestone 4 Competition Demo Script

This script walks through the winning interactive demonstration of SafeSight AI for judges and mentors.

---

### Step 1: Open Mission Control
1. Start the platform: `python run.py`.
2. Navigate to **`http://127.0.0.1:5000/command-center`**.
3. **Point out:**
   - The **"Powered by LangGraph v1.2.20"** badge in the top bar.
   - The glowing **System Health: Nominal** status pill (integrates `/api/health`).
   - The dark "Control Room" aesthetic matching the navy + orange design language.

---

### Step 2: Interactive Filtering & Reactivity (Single Store)
1. Click on **Zone A** in the SVG facility map.
2. **Observe:**
   - Active filter chip appears: `Zone: Zone A`.
   - The URL updates to `/command-center?zone=Zone+A` (shareable link).
   - KPI metrics and the 14-day compliance trend chart update dynamically without page reloads.
3. Click on the **Active Violations** KPI card.
   - Severity filter applies: `Severity: HIGH`.
4. Click **Clear All** on the chip bar.

---

### Step 3: Ask SafeSight Copilot & Watch Live LangGraph Execution
1. Click one of the dynamic prompt chips:
   `"What are the top safety infractions recorded today across all zones?"`
   or type your own query:
   `"What are the rules for safety vests in Zone A?"`
2. **Watch the live LangGraph execution pipeline diagram:**
   - Each node illuminates in sequence:
     `Query Analysis` ➔ `Visual Retrieval` ➔ `Document Retrieval` ➔ `Evidence Check` ➔ `Answer Generation` ➔ `Answer Validation` ➔ `Final Response`
   - Node timing and status stream in real time via Server-Sent Events (SSE).

---

### Step 4: Inspect the Verified Answer & Trust Meter
1. **Headline & Factual Answer:**
   - Every factual claim contains a clickable citation tag like `[V1]` or `[D1]`.
2. **Trust Meter Score:**
   - Score gauge displays trust rating (e.g. `95% (PASS)`).
   - Shows the 6 underlying verification checks:
     - Citations Valid (100%)
     - Citation Coverage (100%)
     - Numbers Match (100%)
     - Grounding (90%)
     - Scope Agreement (100%)
     - Safety & Sanitization (100%)
3. **Evidence Citations Tab:**
   - Blue cards show camera events, cameras, and detection confidence.
   - Orange cards show safety manual excerpts and page numbers.

---

### Step 5: Test Verification & Zero-Bug Proof
Show judges the test evidence:
```bash
python scripts/check_langgraph.py
python -m pytest tests/ -q
python scripts/smoke_test.py
```
- **33/33** Smoke test checks PASS across Milestones 1, 2, 3, and 4.
- **63/63** Automated unit and API tests PASS.
