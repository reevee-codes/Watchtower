import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import openai

from decision.llm_decision import llm_decide
from environment_async import CheckResult, check_all_endpoints
from eval.ground_truth import ground_truth, rule_decide
from eval.report import EvalRecord, generate_report, save_report
from observability.db import init_db, insert_decision
from observability.logger import log_decision


@dataclass
class EndpointState:
    name: str
    url: str
    ok_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    last_status: str = "UNKNOWN"
    last_latency_ms: float = 0.0


class Agent:
    def __init__(self, endpoints: list[dict], goal: str = "all endpoints healthy"):
        self.goal = goal
        self.step = 0
        self.states: dict[str, EndpointState] = {
            ep["name"]: EndpointState(name=ep["name"], url=ep["url"])
            for ep in endpoints
        }
        self._endpoints = endpoints
        self._eval_records: list[EvalRecord] = []
        init_db()

    async def observe(self) -> list[CheckResult]:
        self.step += 1
        results = await check_all_endpoints(self._endpoints)
        for r in results:
            s = self.states[r.name]
            s.last_status = r.status
            s.last_latency_ms = r.latency_ms
            if r.status == "OK":
                s.ok_count += 1
            elif r.status == "ERROR":
                s.error_count += 1
            elif r.status == "TIMEOUT":
                s.timeout_count += 1
            print(f"  [OBSERVE] {r.name:<20} {r.status:<8} {r.latency_ms:6.0f}ms")
        return results

    async def decide(self, results: list[CheckResult]) -> dict[str, dict]:
        outputs = await asyncio.gather(*(self._decide_one(r) for r in results))
        return {r.name: o for r, o in zip(results, outputs)}

    async def _decide_one(self, r: CheckResult) -> dict:
        s = self.states[r.name]
        llm_input = {
            "ok_count": s.ok_count,
            "error_count": s.error_count,
            "timeout_count": s.timeout_count,
            "last_status": s.last_status,
            "latency_ms": s.last_latency_ms,
        }
        llm_start = time.monotonic()
        rule = rule_decide(s.ok_count, s.error_count, s.timeout_count)
        truth = ground_truth(s.ok_count, s.error_count, s.timeout_count)
        try:
            output = await llm_decide(llm_input)
            return {
                "decision": output["decision"],
                "incident_type": output["incident_type"],
                "confidence": output["confidence"],
                "source": "llm",
                "llm_latency_ms": (time.monotonic() - llm_start) * 1000,
                "fallback_reason": None,
                "rule_decision": rule,
                "truth_decision": truth,
            }
        except (ValueError, openai.OpenAIError) as exc:
            output = self._fallback_decide(s)
            return {
                "decision": output["decision"],
                "incident_type": output["incident_type"],
                "confidence": output["confidence"],
                "source": "fallback",
                "llm_latency_ms": 0.0,
                "fallback_reason": repr(exc),
                "rule_decision": rule,
                "truth_decision": truth,
            }

    def _fallback_decide(self, s: EndpointState) -> dict:
        if s.error_count >= 3:
            return {"decision": "ESCALATE", "incident_type": "PERSISTENT_ERROR", "confidence": 1.0}
        if s.error_count >= 2 or s.timeout_count >= 2:
            return {"decision": "ALERT", "incident_type": "TRANSIENT_ERROR", "confidence": 1.0}
        if s.timeout_count >= 1:
            return {"decision": "RETRY", "incident_type": "TIMEOUT_INSTABILITY", "confidence": 1.0}
        return {"decision": "IGNORE", "incident_type": "HEALTHY", "confidence": 1.0}

    def act(self, decisions: dict[str, dict]) -> bool:
        ts = datetime.now(timezone.utc).isoformat()
        for name, d in decisions.items():
            s = self.states[name]
            tag = "" if d["decision"] in ("IGNORE", "RETRY") else f"  *** {d['decision']} ***"
            fallback_note = f"  ({d['fallback_reason']})" if d.get("fallback_reason") else ""
            print(
                f"  [DECIDE]  {name:<20} {d['decision']:<10} "
                f"conf={d['confidence']:.2f}  src={d['source']}{tag}{fallback_note}"
            )
            entry = {
                "ts": ts,
                "step": self.step,
                "endpoint_name": name,
                "endpoint_url": s.url,
                "source": d["source"],
                "last_status": s.last_status,
                "ok_count": s.ok_count,
                "error_count": s.error_count,
                "timeout_count": s.timeout_count,
                "latency_ms": s.last_latency_ms,
                "llm_latency_ms": d["llm_latency_ms"],
                "llm_cost_usd": 0.0,
                "decision": d["decision"],
                "incident_type": d["incident_type"],
                "confidence": float(d["confidence"]),
            }
            log_decision(entry)
            insert_decision(entry)
            self._eval_records.append(EvalRecord(
                endpoint_name=name,
                step=self.step,
                agent_decision=d["decision"],
                source=d["source"],
                rule_decision=d["rule_decision"],
                truth_decision=d["truth_decision"],
                llm_latency_ms=d["llm_latency_ms"],
            ))

        return self.step >= 10

    async def run(self) -> None:
        print(f"[AGENT] Monitoring {len(self.states)} endpoints — goal: {self.goal}\n")
        while True:
            print(f"--- Step {self.step + 1} ---")
            results = await self.observe()
            decisions = await self.decide(results)
            done = self.act(decisions)
            print()
            if done:
                print(f"[AGENT] Finished after {self.step} steps.")
                break
            await asyncio.sleep(3)
        report_text = generate_report(self._eval_records)
        print()
        print(report_text)
        saved = save_report(report_text)
        print(f"\n[AGENT] Report saved → {saved}")
