# SafeSight AI: Milestone 4 System Architecture

## 1. Overview
SafeSight Copilot and Mission Control constitute the final operational intelligence layer of SafeSight AI. It combines:
1. **Visual Telemetry:** Real-time detections and violation records from surveillance cameras (YOLOv8 + OpenCV).
2. **Document Intelligence:** Knowledge repository chunks, corporate safety handbooks, and past inspection findings (Hybrid RRF search).
3. **Multi-Agent LangGraph Workflow:** A sequential, self-validating state machine that extracts intent, cross-references sources, computes risk levels, evaluates grounding, and streams live telemetry over Server-Sent Events (SSE).
4. **Mission Control Command Center:** A reactive, single-store dashboard featuring an interactive SVG site map, live execution visualization, Trust Meter, hourly violation heatmaps, and historical trend monitoring.

---

## 2. Multi-Node LangGraph Pipeline

```
                                    START
                                      │
                                      ▼
                            ┌───────────────────┐
                            │  query_analysis   │
                            └─────────┬─────────┘
                                      │
           ┌──────────────┬───────────┼───────────┬──────────────┬─────────────┐
           │ (smalltalk)  │ (refuse)  │ (clarify) │(investigate) │ (visual)    │ (doc only)
           ▼              ▼           ▼           ▼              ▼             ▼
      ┌─────────┐    ┌────────┐  ┌─────────┐ ┌──────────┐ ┌─────────────┐ ┌────────────────────┐
      │smalltalk│    │ refuse │  │ clarify │ │investigate││ visual_ret   │ │ document_retrieval │
      └────┬────┘    └───┬────┘  └───┬─────┘ └────┬─────┘ └──────┬──────┘ └─────────┬──────────┘
           │             │           │            │              │                  │
           │             │           │            │     (needs docs)                │
           │             │           │            │              ├──────────────────┘
           │             │           │            │              ▼
           │             │           │            │     ┌──────────────────┐
           │             │           │            │     │  evidence_check  │
           │             │           │            │     └────────┬─────────┘
           │             │           │            │              │
           │             │           │            │      ┌───────┴───────┐
           │             │           │            │      │ (evidence ok) │ (no evidence)
           │             │           │            │      ▼               ▼
           │             │           │            │ ┌──────────┐   ┌─────────────┐
           │             │           │            │ │answer_gen│   │ no_evidence │
           │             │           │            │ └────┬─────┘   └──────┬──────┘
           │             │           │            │      │                │
           │             │           │            │      ▼                │
           │             │           │            │ ┌──────────┐          │
           │             │           │            │ │validation│          │
           │             │           │            │ └────┬─────┘          │
           │             │           │            │      │                │
           │             │           │            ├──────┴────────────────┤ (pass score >= 80)
           │             │           │            │ (revise & retries < 2)│
           │             │           │            ├───► [answer_gen]      │
           │             │           │            │ (fail/retries used)   │
           │             │           │            ├──────► [safe_fallback]│
           │             │           │            │                       │
           ▼             ▼           ▼            ▼                       ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │                             final_response                             │
      └───────────────────────────────────┬────────────────────────────────────┘
                                          │
                                          ▼
                                         END
```

---

## 3. Data Contracts & State Management

### CopilotState (`app/copilot/state.py`)
- `run_id` (str): Unique run identifier.
- `session_id` (str): Session persistence identifier.
- `question` (str): Raw input query.
- `ui_context` (dict): Active dashboard filters `{zone, violationType, severity}`.
- `plan` (QueryPlan): Structured intent and extracted entities.
- `visual_evidence` (Annotated[list, operator.add]): List of visual events `[V1..Vn]`.
- `document_evidence` (Annotated[list, operator.add]): List of document citations `[D1..Dn]`.
- `facts` (dict): Exact numbers computed by code from SQL (compliance, total violations).
- `answer_card` (AnswerCard): Grounded response with risk rating and citations.
- `validation` (ValidationReport): 0-100% trust score and check verdicts.
- `route` (Annotated[list, operator.add]): Visited node execution path.
- `trace` (Annotated[list, operator.add]): Timing and telemetry milestones.

---

## 4. Trust Meter & Automated Validation

Every generated response undergoes 6 deterministic checks in `app/copilot/validators.py`:
1. **Citations Valid:** Asserts all cited `[Vx]` and `[Dx]` tags exist in retrieved evidence.
2. **Citation Coverage:** Asserts factual statements (>6 words) terminate with citations.
3. **Numbers Match:** Compares all quantities in the answer against database facts (critical check).
4. **Grounding:** Token overlap and similarity against source excerpts.
5. **Scope Agreement:** Verifies query zone and entity alignment.
6. **Safety & Prompt Injection Guard:** Verifies no raw HTML or prompt-injection echoes.
