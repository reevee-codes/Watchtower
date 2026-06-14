import json
from pathlib import Path
from typing import TypedDict

import yaml
from openai import AsyncOpenAI

CONFIG_PATH = Path(__file__).parent.parent / "config" / "llm.yaml"
CONFIG = yaml.safe_load(CONFIG_PATH.read_text())

MODEL_NAME = CONFIG["model_name"]
TEMPERATURE = CONFIG["temperature"]
MAX_TOKENS = CONFIG["max_tokens"]
TIMEOUT = CONFIG["timeout"]
SYSTEM_PROMPT = CONFIG["prompt"]

_VALID_DECISIONS = {"RETRY", "IGNORE", "ALERT", "ESCALATE"}
_VALID_INCIDENTS = {
    "HEALTHY", "TRANSIENT_ERROR", "PERSISTENT_ERROR",
    "TIMEOUT_INSTABILITY", "UNKNOWN",
}

_client = AsyncOpenAI()


class DecisionInput(TypedDict):
    ok_count: int
    error_count: int
    timeout_count: int
    last_status: str
    latency_ms: float


class DecisionOutput(TypedDict):
    decision: str
    incident_type: str
    confidence: float


async def llm_decide(state: DecisionInput) -> DecisionOutput:
    response = await _client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(state)},
        ],
        timeout=TIMEOUT,
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("LLM returned empty content")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM did not return valid JSON") from exc

    decision = data.get("decision")
    incident_type = data.get("incident_type")
    confidence = data.get("confidence")

    if decision not in _VALID_DECISIONS:
        raise ValueError(f"Invalid decision: {decision!r}")
    if incident_type not in _VALID_INCIDENTS:
        raise ValueError(f"Invalid incident_type: {incident_type!r}")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be a number")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence out of range: {confidence}")

    return {
        "decision": decision,
        "incident_type": incident_type,
        "confidence": float(confidence),
    }
