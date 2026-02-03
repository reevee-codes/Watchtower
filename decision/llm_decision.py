from __future__ import annotations
import json
from typing import cast
import yaml
from pathlib import Path
from openai import OpenAI

from agent.types import DecisionInput, DecisionResult, Decision, IncidentType

CONFIG_PATH = Path(__file__).parent.parent / "config" / "llm.yaml"
CONFIG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

MODEL_NAME = CONFIG["model_name"]
TEMPERATURE = CONFIG["temperature"]
MAX_TOKENS = CONFIG["max_tokens"]
TIMEOUT = CONFIG["timeout"]
SYSTEM_PROMPT = CONFIG["prompt"]

_ALLOWED_DECISIONS: set[str] = {"STOP", "CONTINUE", "RETRY", "ALERT"}
_ALLOWED_INCIDENTS: set[str] = {
    "HEALTHY", "TRANSIENT_ERROR", "PERSISTENT_ERROR", "TIMEOUT_INSTABILITY", "UNKNOWN"
}

def llm_decide(state: DecisionInput) -> DecisionResult:
    client = OpenAI()

    resp = client.chat.completions.create(
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

    raw = resp.choices[0].message.content or ""
    data = json.loads(raw)

    # validate keys
    for key in ("decision", "incident_type", "confidence"):
        if key not in data:
            raise ValueError(f"Missing field: {key}")

    decision = data["decision"]
    incident = data["incident_type"]
    confidence = data["confidence"]

    if decision not in _ALLOWED_DECISIONS:
        raise ValueError(f"Invalid decision: {decision}")
    if incident not in _ALLOWED_INCIDENTS:
        raise ValueError(f"Invalid incident_type: {incident}")
    if not isinstance(confidence, (float, int)):
        raise ValueError("confidence must be float")

    return DecisionResult(
        decision=cast(Decision, decision),
        incident_type=cast(IncidentType, incident),
        confidence=float(confidence),
        source="LLM",
    )