"""Small synthetic engine-shaped results for workflow algorithm tests."""


def requirement(
    requirement_id,
    state="APPLICABLE",
    sla_days=1,
    depends_on=None,
    candidate_dependencies=None,
    missing_facts=None,
):
    return {
        "requirement_id": requirement_id,
        "name": f"Requirement {requirement_id}",
        "requirement_type": "LICENCE",
        "department": "Synthetic Department",
        "authority": "Synthetic Authority",
        "statute": "Synthetic Rule",
        "state": state,
        "confidence": "high",
        "sla_days": sla_days,
        "depends_on": depends_on or [],
        "candidate_dependencies": candidate_dependencies or [],
        "missing_facts": missing_facts or [],
        "missing_fact_origin": {},
    }


def dependency(requirement_id, dependency_type="LEGAL", verification_status="VERIFIED"):
    return {
        "requirement_id": requirement_id,
        "dependency_type": dependency_type,
        "verification_status": verification_status,
        "basis": "synthetic test edge",
    }


def engine_result(*requirements):
    result = {"applicable": [], "unknown": [], "not_applicable": [], "conflict": []}
    bucket_for_state = {
        "APPLICABLE": "applicable",
        "UNKNOWN": "unknown",
        "NOT_APPLICABLE": "not_applicable",
        "CONFLICT": "conflict",
    }
    for req in requirements:
        result[bucket_for_state[req["state"]]].append(req)
    return result


def catalogue(*requirements):
    return {
        req["requirement_id"]: {
            "name": req["name"],
            "requirement_type": req["requirement_type"],
            "department": req["department"],
            "authority": req["authority"],
            "statute": req["statute"],
            "sla_days": req["sla_days"],
        }
        for req in requirements
    }
