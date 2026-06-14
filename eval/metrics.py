from collections import Counter
from dataclasses import dataclass

_ACTION = {"ALERT", "ESCALATE"}


@dataclass
class BinaryMetrics:
    accuracy: float
    precision: float
    recall: float
    tp: int
    fp: int
    fn: int
    tn: int


def compute_binary_metrics(predicted: list[str], actual: list[str]) -> BinaryMetrics:
    tp = fp = fn = tn = 0
    for p, a in zip(predicted, actual):
        p_pos = p in _ACTION
        a_pos = a in _ACTION
        if p_pos and a_pos:
            tp += 1
        elif p_pos and not a_pos:
            fp += 1
        elif not p_pos and a_pos:
            fn += 1
        else:
            tn += 1
    total = tp + fp + fn + tn
    return BinaryMetrics(
        accuracy=(tp + tn) / total if total else 0.0,
        precision=tp / (tp + fp) if (tp + fp) else 0.0,
        recall=tp / (tp + fn) if (tp + fn) else 0.0,
        tp=tp, fp=fp, fn=fn, tn=tn,
    )


def agreement_rate(a: list[str], b: list[str]) -> float:
    return sum(x == y for x, y in zip(a, b)) / len(a) if a else 0.0


def disagreement_summary(a: list[str], b: list[str], label_a: str, label_b: str) -> list[str]:
    counts = Counter((x, y) for x, y in zip(a, b) if x != y)
    return [f"{n}x {label_a}={p}, {label_b}={q}" for (p, q), n in counts.most_common()]
