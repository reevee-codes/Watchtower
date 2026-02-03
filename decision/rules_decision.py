from agent.types import DecisionResult

def decide_rules(ok_count: int, error_count: int, timeout_count: int) -> DecisionResult:
    if ok_count >= 3:
        return DecisionResult(decision="STOP", incident_type="HEALTHY", confidence=1.0, source="RULES")

    if error_count >= 3:
        return DecisionResult(decision="ALERT", incident_type="PERSISTENT_ERROR", confidence=1.0, source="RULES")

    if timeout_count >= 3:
        return DecisionResult(decision="RETRY", incident_type="TIMEOUT_INSTABILITY", confidence=1.0, source="RULES")

    return DecisionResult(decision="CONTINUE", incident_type="RULE_BASED", confidence=1.0, source="RULES")
