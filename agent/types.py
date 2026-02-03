from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, TypedDict

Decision = Literal["STOP", "CONTINUE", "RETRY", "ALERT"]
DecisionSource = Literal["LLM", "RULES"]

IncidentType = Literal[
    "HEALTHY",
    "TRANSIENT_ERROR",
    "PERSISTENT_ERROR",
    "TIMEOUT_INSTABILITY",
    "UNKNOWN",
    "RULE_BASED",
]

class DecisionInput(TypedDict):
    ok_count: int
    error_count: int
    timeout_count: int
    last_status: str
    latency_ms: float

class DecisionOutput(TypedDict):
    decision: Decision
    incident_type: IncidentType
    confidence: float

@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    incident_type: IncidentType
    confidence: float
    source: DecisionSource
