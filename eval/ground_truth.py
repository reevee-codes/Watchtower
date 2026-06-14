def rule_decide(ok_count: int, error_count: int, timeout_count: int) -> str:
    """Deterministic fallback rules — mirrors _fallback_decide in agent_async."""
    if error_count >= 3:
        return "ESCALATE"
    if error_count >= 2 or timeout_count >= 2:
        return "ALERT"
    if timeout_count >= 1:
        return "RETRY"
    return "IGNORE"


def ground_truth(ok_count: int, error_count: int, timeout_count: int) -> str:
    """Idealised oracle: what *should* happen given this state."""
    if error_count >= 3:
        return "ESCALATE"
    if error_count >= 2 or timeout_count >= 2:
        return "ALERT"
    if ok_count >= 3:
        return "IGNORE"
    return "RETRY"
