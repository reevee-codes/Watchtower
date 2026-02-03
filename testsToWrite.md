# Tests to Write

---

## 1) Decision Layer – Rules (`rules_decision`)

### R1. Healthy stop

- **Given:** `ok_count >= 3`
- **Expect:** `decision = STOP`, `incident_type = HEALTHY`, `source = RULES`

### R2. Persistent error → alert

- **Given:** `error_count >= 3`
- **Expect:** `decision = ALERT` (or STOP+ALERT depending on policy), `incident_type = PERSISTENT_ERROR`

### R3. Timeout instability → retry

- **Given:** `timeout_count >= 3`
- **Expect:** `decision = RETRY`, `incident_type = TIMEOUT_INSTABILITY`

### R4. Default path

- **Given:** `ok_count=1`, `error_count=1`, `timeout_count=0`
- **Expect:** `decision = CONTINUE`, `incident_type = RULE_BASED`

### R5. Boundaries (>= vs ==)

- **Given:** `ok_count = 4` (or `error_count=4`)
- **Expect:** still works the same (does not require equality)

---

## 2) Decision Layer – LLM output validation (`llm_decision`)

> You're not testing whether OpenAI is "smart", only whether your code is resilient to garbage input.

### L1. Valid JSON → success

- **Mock:** LLM returns valid JSON with all required fields
- **Expect:** returns `DecisionResult`, `source = LLM`

### L2. Not JSON → error

- **Mock:** plain text or invalid JSON
- **Expect:** exception (`ValueError`)

### L3. Missing field

- **Mock:** JSON without `decision` / `incident_type` / `confidence`
- **Expect:** exception

### L4. Invalid decision value

- **Mock:** `decision = "RETRYYY"`
- **Expect:** exception (so agent falls back)

### L5. Invalid incident_type

- **Mock:** `incident_type = "SERVER_IS_SAD"`
- **Expect:** exception

### L6. Confidence wrong type

- **Mock:** `confidence = "high"`
- **Expect:** exception

---

## 3) Agent.decide() – LLM vs fallback routing

> You're testing orchestration: agent tries LLM; if it fails → rules.

### A1. LLM success path

- **Mock:** `llm_decide` returns `DecisionResult(decision=..., source=LLM)`
- **Expect:**
  - `agent.last_source == "LLM"`
  - `decision` / `incident` / `confidence` set from LLM
  - rules not used

### A2. LLM failure → fallback rules

- **Mock:** `llm_decide` raises exception
- **Expect:**
  - `agent.last_source == "RULES"`
  - decision matches rules for current counters
  - agent does not crash

### A3. LLM returns invalid output → treated as failure

- **Mock:** `llm_decide` returns something invalid (or validation raises)
- **Expect:** fallback to rules

### A4. Decision types are constrained

- **Mock:** `llm_decide` returns decision outside allowed set
- **Expect:** fallback (test for strict typing + validation)

---

## 4) Agent.observe() – state and counters

> You're not testing HTTP; you're testing that the agent correctly updates state.

### O1. OK increments ok_count

- **Mock:** `check_api` returns `("OK", 123.4)`
- **Expect:**
  - `steps +1`
  - `ok_count +1`
  - `last_status == "OK"`
  - `last_latency_ms == 123.4`

### O2. ERROR increments error_count

- Same pattern as O1 (mock `("ERROR", …)`)

### O3. TIMEOUT increments timeout_count

- Same pattern as O1 (mock `("TIMEOUT", …)`)

### O4. steps increments always

- Regardless of status

---

## 5) Agent.act() – concrete actions (alert)

> You're testing that the agent does something tangible.

### ACT1. ALERT sends alert and stops

- **Given:** `DecisionResult(decision="ALERT", incident_type="PERSISTENT_ERROR")`
- **Expect:**
  - `send_alert()` called once
  - `act()` returns `True`

### ACT2. STOP stops without alert

- **Given:** `DecisionResult(decision="STOP", incident_type="HEALTHY")`
- **Expect:**
  - `send_alert()` **not** called
  - `act()` returns `True`

### ACT3. RETRY/CONTINUE continues

- **Given:** `decision="RETRY"` or `"CONTINUE"`
- **Expect:**
  - `send_alert()` **not** called
  - `act()` returns `False`

**Tip:** Test `send_alert` via mock/spy, not by asserting on `print`.

---

## 6) Run loop – integration, but controlled

> Mini E2E without network.

### RUN1. Ends after healthy condition

- **Mock:** environment returns `OK`, `OK`, `OK` (with latency)
- **Mock:** decision layer (rules or LLM)
- **Expect:** `run()` finishes in a reasonable number of iterations and `state.ok_count == 3`

### RUN2. Alerts on persistent failure

- **Environment:** `ERROR`, `ERROR`, `ERROR`
- **Expect:** `send_alert` called, run stops

---

## 7) Observability tests (simple but strong)

If you log in a structured way (e.g. JSON or fields):

### OBS1. decision telemetry is set every loop

- After one cycle: `last_decision` / `last_source` / `last_incident_type` are set

### OBS2. LLM vs RULES usage counter (if you add it)

- After N iterations with mocks: counter matches expected

---

## 8) Bonus: reliability tests (look great on CV)

### REL1. Missing API key doesn't crash system

- **Mock:** `llm_decide` raises `AuthError` / `Exception`
- **Expect:** fallback; program keeps running

### REL2. Slow LLM triggers fallback (if you add timeout handling)

- **Mock:** `llm_decide` "hangs" / times out
- **Expect:** fallback
