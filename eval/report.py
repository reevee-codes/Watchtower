from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from eval.metrics import compute_binary_metrics, agreement_rate, disagreement_summary

_REPORTS_DIR = Path(__file__).parent.parent / "reports"


@dataclass
class EvalRecord:
    endpoint_name: str
    step: int
    agent_decision: str
    source: str            # "llm" | "fallback"
    rule_decision: str
    truth_decision: str
    llm_latency_ms: float


def generate_report(records: list[EvalRecord]) -> str:
    if not records:
        return "No evaluation data."

    total = len(records)
    llm_count = sum(1 for r in records if r.source == "llm")

    agent_decisions = [r.agent_decision for r in records]
    rule_decisions = [r.rule_decision for r in records]
    truth_decisions = [r.truth_decision for r in records]

    vs_truth = compute_binary_metrics(agent_decisions, truth_decisions)
    vs_rule_agr = agreement_rate(agent_decisions, rule_decisions)
    vs_rule_dis = disagreement_summary(agent_decisions, rule_decisions, "Agent", "Rules")

    llm_latencies = [r.llm_latency_ms for r in records if r.source == "llm"]
    avg_latency = sum(llm_latencies) / len(llm_latencies) if llm_latencies else 0.0

    lines = [
        "=== EVALUATION REPORT ===",
        f"Total decisions: {total}  |  LLM: {llm_count}  |  Fallback: {total - llm_count}",
        "",
        "Agent vs Ground Truth:",
        f"  Accuracy:  {vs_truth.accuracy:.1%}",
        f"  Precision: {vs_truth.precision:.2f}",
        f"  Recall:    {vs_truth.recall:.2f}",
        f"  TP: {vs_truth.tp}  FP: {vs_truth.fp}  FN: {vs_truth.fn}  TN: {vs_truth.tn}",
        "",
        "Agent vs Rule-based:",
        f"  Agreement: {vs_rule_agr:.1%}",
        f"  Disagreements: {', '.join(vs_rule_dis) if vs_rule_dis else 'none'}",
        "",
        f"Avg LLM latency: {avg_latency:.0f}ms  |  Avg cost/decision: $0.0000 (tracking TBD)",
    ]
    return "\n".join(lines)


def save_report(text: str) -> Path:
    _REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    path = _REPORTS_DIR / f"eval_{ts}.txt"
    path.write_text(text, encoding="utf-8")
    return path
