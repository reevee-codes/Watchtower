from __future__ import annotations
from agent.state import AgentState
from agent.types import DecisionResult
from decision.llm_decision import llm_decide
from decision.rules_decision import decide_rules
from environment.http_env import check_api


class Agent:
    def __init__(self, goal: str):
        self.goal = goal
        self.state = AgentState()

        self.last_decision: Decision | None = None
        self.last_incident_type: str | None = None
        self.last_confidence: float | None = None
        self.last_source: str | None = None

    async def observe(self) -> tuple[str, float]:
        self.state.steps += 1
        status, latency_ms = await check_api()
        self.state.last_status = status
        self.state.last_latency_ms = latency_ms

        if status == "OK":
            self.state.ok_count += 1
        elif status == "ERROR":
            self.state.error_count += 1
        elif status == "TIMEOUT":
            self.state.timeout_count += 1

        return status, latency_ms

    def decide(self) -> DecisionResult:
        inp = {
            "ok_count": self.state.ok_count,
            "error_count": self.state.error_count,
            "timeout_count": self.state.timeout_count,
            "last_status": self.state.last_status,
            "latency_ms": self.state.last_latency_ms,
        }

        try:
            result = llm_decide(inp)
        except Exception:
            result = decide_rules(
                ok_count=self.state.ok_count,
                error_count=self.state.error_count,
                timeout_count=self.state.timeout_count,
            )

        # store telemetry
        self.last_decision = result.decision
        self.last_incident_type = result.incident_type
        self.last_confidence = result.confidence
        self.last_source = result.source

        return result

    def act(self, result: DecisionResult) -> bool:

        print(
            f"step={self.state.steps} status={self.state.last_status} "
            f"ok={self.state.ok_count} err={self.state.error_count} to={self.state.timeout_count} "
            f"decision={result.decision} incident={result.incident_type} "
            f"source={result.source} conf={result.confidence:.2f} "
            f"latency_ms={self.state.last_latency_ms:.0f}"
        )

        if result.decision == "ALERT" or result.incident_type == "PERSISTENT_ERROR":
            self.send_alert(f"{result.incident_type} after {self.state.steps} steps")
            return True

        if result.decision == "STOP":
            return True

        return False

    def send_alert(self, reason: str) -> None:
        print(f"🚨 ALERT: {reason}")

    async def run(self) -> None:
        while True:
            await self.observe()
            decision_result = self.decide()
            done = self.act(decision_result)
            if done:
                break
