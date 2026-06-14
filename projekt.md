# AI API Monitoring Decision Agent — LLM CONTEXT

## PURPOSE

This document is **context for an LLM**, not a human tutorial.
It defines:

* what the system is
* how decisions are made
* how the project should evolve

The LLM should use this as **persistent project memory**.

---

## SYSTEM SUMMARY

An **autonomous AI decision system** for API monitoring.

Core properties:

* agent-based (observe → decide → act)
* LLM used ONLY as a decision layer
* deterministic fallback logic
* evaluation and observability built-in

Not a chatbot.
Not prompt engineering.

---

## CURRENT STATE (BASELINE)

* Deterministic agent implemented
* Async HTTP environment (`httpx`)
* Rule-based decision logic
* Unit tests for decision behavior

---

## CORE ARCHITECTURE

```
Runner (cron / main)
  ↓
Agent
  - observe()
  - decide()
  - act()
  ↓
Decision Layer
  - rules (fallback)
  - LLM (primary)
  ↓
Environment
  - HTTP
  - metrics
```

---

## DECISION CONTRACT

### Input to decision layer

```
{
  ok_count: int,
  error_count: int,
  timeout_count: int,
  last_status: str,
  latency_ms: float
}
```

### Output from decision layer (strict JSON)

```
{
  decision: RETRY | IGNORE | ALERT | ESCALATE,
  incident_type: HEALTHY | TRANSIENT_ERROR | PERSISTENT_ERROR | TIMEOUT_INSTABILITY | UNKNOWN,
  confidence: float
}
```

---

## LLM USAGE RULES

* LLM is NOT conversational
* LLM does NOT generate text
* LLM only returns structured decisions
* LLM failures MUST trigger fallback

---

## FALLBACK LOGIC (MANDATORY)

If LLM:

* times out
* errors
* is unavailable

System must:

* switch to rule-based decisions
* continue operating

This demonstrates reliability.

---

## EVALUATION (EVAL)

Metrics to compute:

* decision precision
* false positives
* false negatives

Compare:

* LLM decision
* rule-based decision
* simulated ground truth

---

## OBSERVABILITY

Track per decision:

* HTTP latency
* LLM latency
* cost per decision
* decision source (LLM vs fallback)

Structured logs only (JSON).

---

## NEXT IMPLEMENTATION STEPS

1. Replace rule-based `decide()` with LLM-backed decision layer
2. Enforce strict JSON output
3. Implement fallback routing
4. Add evaluation framework
5. Add observability metrics

---

## FINAL PROJECT CLAIM

"Built an AI-driven decision system for API monitoring with fallback logic, evaluation, and observability."
