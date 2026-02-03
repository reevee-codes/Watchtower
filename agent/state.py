from dataclasses import dataclass

@dataclass
class AgentState:
    steps: int = 0
    ok_count: int = 0
    error_count: int = 0
    timeout_count: int = 0

    last_status: str = "UNKNOWN"
    last_latency_ms: float = 0.0
