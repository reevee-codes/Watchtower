## AI API Monitoring Agent

Simple system for monitoring API health and deciding what to do next.

The agent checks an API, keeps basic state (OKs, errors, timeouts, latency), and decides whether to continue, retry, alert, or stop. Decisions are made using an LLM when available, with a rule-based fallback to keep the system running if the LLM fails.

The project focuses on clean separation of concerns, explicit control flow, and safe use of LLMs in a non-critical decision role.

How it works
### Observe (HTTP check)

The agent calls the environment layer, which performs asynchronous HTTP request.

It returns:
- a simple status: OK, ERROR, or TIMEOUT

- request latency in milliseconds

### Update state

The agent updates its internal state:

- increments counters: ok_count, error_count, timeout_count

- stores: last_status, last_latency_ms

### Decide (LLM first, rules fallback)

The agent builds a small JSON snapshot of the current state (counters, last status, latency).

It then tries the LLM decision function, which must return strict JSON with:

- decision (STOP, CONTINUE, RETRY, ALERT)

- incident_type (e.g. HEALTHY, TRANSIENT_ERROR, PERSISTENT_ERROR, TIMEOUT_INSTABILITY, 
UNKNOWN)

- confidence (number)

If the LLM call fails or returns invalid output, the agent falls back to deterministic rule-based decisions.

### Act

Based on the decision and incident type, the agent performs a concrete action:

- continue monitoring

- stop the run

- trigger an alert (currently printed to the console; can be replaced with Slack, 
webhook, or email)

### Repeat

The loop continues until the agent decides to stop because the system is stable or an alert condition is reached.

---

### OpenAI API key

#### Windows

```powershell
setx OPENAI_API_KEY "sk-your-api-key"
```

Restart your terminal / IDE after setting the variable.

---

#### macOS / Linux

```bash
export OPENAI_API_KEY="sk-your-api-key"
```

---

### Verify

```python
import os
print(os.getenv("OPENAI_API_KEY"))
```

If it prints the key → setup is correct.

---

### Notes

* API keys are **never** stored in code
* If the key is missing or invalid, the system **automatically falls back** to rule‑based decisions

---
### Run

```bash
python main.py
```
---
**Project focus:** AI‑driven decision system with deterministic fallback.