# Program Flow - API Monitoring Decision Agent

## Introduction

The program is an agent that monitors API health, operating in a loop: **Observe → Decide → Act**. The agent checks the API, collects data about its state, and makes decisions whether to continue monitoring, stop, retry, or send an alert.

---

## Main Flow

### 1. Entry Point (`main.py`)

```python
agent = Agent(goal="API healthy")
await agent.run()
```

Creates an agent with a goal (currently unused) and starts the main loop.

### 2. Main Loop (`agent/agent.py` - `run()` method)

```python
while True:
    await self.observe()           # Step 1: Observation
    decision_result = self.decide()  # Step 2: Decision
    done = self.act(decision_result) # Step 3: Action
    if done:
        break
```

The loop runs until the agent decides to stop (`STOP`) or sends an alert (`ALERT`).

---

## Detailed Step Description

### Step 1: OBSERVE (`observe()`)

**What happens:**
- Calls `check_api()` from `environment/http_env.py`
- `check_api()` randomly selects one of the URLs and performs an asynchronous HTTP request
- Returns:
  - `status`: "OK", "ERROR", or "TIMEOUT"
  - `latency_ms`: response time in milliseconds

**State update:**
- Increments `steps` counter by 1 (loop iteration number)
- Increments appropriate counter:
  - `ok_count++` if status = "OK"
  - `error_count++` if status = "ERROR"
  - `timeout_count++` if status = "TIMEOUT"
- Saves: `last_status`, `last_latency_ms`

### Step 2: DECIDE (`decide()`)

**Building state snapshot:**
```python
inp = {
    "ok_count": self.state.ok_count,
    "error_count": self.state.error_count,
    "timeout_count": self.state.timeout_count,
    "last_status": self.state.last_status,
    "latency_ms": self.state.last_latency_ms,
}
```

**Attempting to use LLM (`decision/llm_decision.py`):**
- Sends prompt to OpenAI with current state
- Expects JSON with:
  - `decision`: "STOP", "CONTINUE", "RETRY", "ALERT"
  - `incident_type`: incident type (e.g., "HEALTHY", "PERSISTENT_ERROR")
  - `confidence`: decision confidence (number)
- Validates response

**Fallback to rules (`decision/rules_decision.py`):**
If LLM:
- Throws an exception
- Returns invalid format
- Is unavailable

**Deterministic rules:**
- `ok_count >= 3` → **STOP** (HEALTHY) - API is stable
- `error_count >= 3` → **ALERT** (PERSISTENT_ERROR) - too many errors
- `timeout_count >= 3` → **RETRY** (TIMEOUT_INSTABILITY) - timeout issues
- Otherwise → **CONTINUE** (RULE_BASED) - continue monitoring

**Telemetry storage:**
- `last_decision`, `last_incident_type`, `last_confidence`, `last_source` (LLM or RULES)

### Step 3: ACT (`act()`)

**Logging:**
Prints telemetry:
```
step=1 status=OK ok=1 err=0 to=0 decision=CONTINUE incident=HEALTHY source=LLM conf=0.95 latency_ms=150
```

**Action execution:**
- **ALERT** or **PERSISTENT_ERROR** → calls `send_alert()` and ends loop (`return True`)
- **STOP** → ends loop (`return True`)
- **RETRY** / **CONTINUE** → continues loop (`return False`)

**Repetition:**
The loop continues until:
- Agent decides **STOP** (e.g., 3+ successes)
- **ALERT** is triggered (e.g., 3+ errors)

---

## Architecture

```
main.py
  └── Agent (agent/agent.py)
       ├── AgentState (agent/state.py) - stores state
       │   ├── steps: int - iteration counter
       │   ├── ok_count, error_count, timeout_count - counters
       │   └── last_status, last_latency_ms - last values
       │
       ├── observe() → environment/http_env.py
       │   └── check_api() - performs HTTP request
       │
       ├── decide() → decision/llm_decision.py (LLM)
       │              └── fallback → decision/rules_decision.py (rules)
       │
       └── act() - executes decision and logs
```

---

## Frequently Asked Questions

### 1. What does the `goal` parameter affect?

**Answer:** Nothing. It's stored in `self.goal`, but it's not used:
- ❌ Not passed to LLM
- ❌ Not used in decisions
- ❌ Not used in rules
- ❌ Not used in agent logic

This is **dead code** - the parameter exists but has no impact on program behavior. It was likely planned for use but never implemented.

### 2. What is `steps`?

**Answer:** `steps` is the **main loop iteration counter**:
- Increments by 1 on each `observe()` call
- Used for:
  - Logging: `f"step={self.state.steps} ..."`
  - Alerts: `f"... after {self.state.steps} steps"`

It's simply the step number in monitoring (1, 2, 3...).

### 3. Why use LLM? Is it just for CV/resume?

**Answer:** In its current form, it appears to be mainly for CV/demonstration purposes. Reasons:

**Why it might be unnecessary:**
- ✅ Rules are very simple and deterministic - easy to code without LLM
- ✅ LLM doesn't receive `goal`, so it can't use it in context
- ✅ Prompt is very simple - can be replaced with rules
- ✅ There's a fallback to rules, so LLM is optional

**Potential benefits of LLM (if better implemented):**
- More flexible decisions (e.g., considering latency)
- Better pattern recognition (e.g., instability)
- Ability to extend with more context

**Conclusion:** In its current form, LLM doesn't add much beyond simple rules, but it could be useful when expanding the system.

### 4. What does `CONTINUE` do?

**Answer:** `CONTINUE` means **"continue the loop - don't stop execution"**.

In `act()`:
```python
if result.decision == "STOP":
    return True  # ends loop
    
# retry/continue = keep running
return False  # continues loop
```

**Difference between `CONTINUE` and `RETRY`:**
- Both return `False` → loop continues
- Difference is only **semantic** (in `incident_type` and logs)
- In practice, they work the same - next loop iteration

**Summary:**
- `CONTINUE` = "keep monitoring, do nothing"
- `RETRY` = "keep monitoring, maybe the problem will resolve"

---

## Key Project Features

1. **Separation of concerns:**
   - `environment/` - environment layer (HTTP requests)
   - `decision/` - decision layer (LLM + rules)
   - `agent/` - agent logic

2. **Rules fallback:**
   - If LLM doesn't work, uses deterministic rules
   - System always works, even without API key

3. **Agent state:**
   - Agent tracks history (counters, last status)
   - State is updated on each observation

4. **Asynchronicity:**
   - Uses `async/await` for HTTP requests
   - Doesn't block execution while waiting for response

---

## Decision Types

- **STOP** - stop monitoring (API is stable)
- **CONTINUE** - continue monitoring (do nothing)
- **RETRY** - continue monitoring (maybe problem will resolve)
- **ALERT** - send alert and stop (critical problem)

## Incident Types

- **HEALTHY** - API is working correctly
- **TRANSIENT_ERROR** - transient error
- **PERSISTENT_ERROR** - persistent error (requires alert)
- **TIMEOUT_INSTABILITY** - timeout issues
- **UNKNOWN** - unknown incident type
- **RULE_BASED** - decision made by rules

---

## Running

```bash
python main.py
```

**Requirements:**
- Environment variable `OPENAI_API_KEY` (optional - works without it using rules)
- Installed dependencies from `requirements.txt`
