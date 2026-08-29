"""
Derivation engine with bounded fixed-point evaluation.

Layering, deliberately distinct:
  CONDITION level     three-valued Kleene logic       engine/evaluator.py
  DERIVATION level    typed, fixed-registry ops       engine/derived.py
  REQUIREMENT level   four-state resolution           engine/resolve.py

Fixed-point loop:
  supplied facts -> evaluate rules -> collect derived facts
                 -> merge new facts -> re-evaluate -> ... -> quiesce

Bounded by MAX_DERIVATION_PASSES. Identical re-derivations are suppressed.
Contradictory derivations are withheld from the working fact set so that
downstream consumers evaluate to UNKNOWN rather than to a guess.
"""

import json
from datetime import date
from pathlib import Path

from .tri import T, F, U
from .evaluator import evaluate, select_version
from .resolve import State, Evidence, classify, resolve
from .quantity import compute as compute_quantity
from .validate_data import validate_registry, CRITICAL_PATH_TYPES
from .derived import (DerivedFact, IndeterminateDerivation, DerivedFactConflict,
                      DerivationError, execute as execute_derivation)

MAX_DERIVATION_PASSES = 10


class Registry:
    def __init__(self, root, validate=True, strict=False):
        self.root = Path(root)
        self.catalogue = self._load("approvals/catalogue.json", {})
        self.sources = self._load("sources/sources.json", {})
        self.dependencies = self._load("workflows/dependencies.json", {})
        self.rules = []
        for path in sorted((self.root / "rules").glob("*.json")):
            self.rules.extend(json.loads(path.read_text()))

        self.issues = validate_registry(self) if validate else []
        self.errors = [i for i in self.issues if i.severity == "error"]
        if strict and self.errors:
            raise ValueError(
                f"{len(self.errors)} error(s) in regulatory data:\n  "
                + "\n  ".join(str(e) for e in self.errors))

    def _load(self, rel, default):
        p = self.root / rel
        return json.loads(p.read_text()) if p.exists() else default

    def versions_of(self, rule_id):
        return [r for r in self.rules if r["rule_id"] == rule_id]

    @property
    def rule_ids(self):
        # deterministic order: sorted, so evaluation is reproducible
        return sorted({r["rule_id"] for r in self.rules})

    def scheduling_dependencies(self, req_id):
        spec = self.dependencies.get(req_id, {})
        return [d for d in spec.get("depends_on", [])
                if d.get("dependency_type") in CRITICAL_PATH_TYPES]


def derive(facts, registry, as_of=None, max_passes=MAX_DERIVATION_PASSES):
    as_of = as_of or date.today()

    working = dict(facts)
    supplied_names = {k for k, v in facts.items() if v is not None}

    derived_facts = {}        # fact name -> DerivedFact (accepted)
    indeterminate = []        # IndeterminateDerivation
    conflicts = []            # DerivedFactConflict
    seen_signatures = set()   # repeated-derivation suppression
    contradicted = set()      # facts withheld due to conflict
    warnings = []
    passes_run = 0
    suppressed_repeats = 0

    # ── bounded fixed point ──
    for pass_no in range(1, max_passes + 1):
        passes_run = pass_no
        produced_this_pass = {}
        new_signature_seen = False

        for rule_id in registry.rule_ids:
            rule = select_version(registry.versions_of(rule_id), as_of)
            if rule is None:
                continue
            specs = rule.get("effect", {}).get("derives", [])
            if not specs:
                continue

            result, _trace = evaluate(rule["condition"], working)

            if result is F:
                continue

            if result is U:
                missing = sorted({t["fact"] for t in _trace
                                  if t["result"] == "UNKNOWN"})
                for spec in specs:
                    name = spec.get("fact")
                    if name in derived_facts or name in contradicted:
                        continue
                    rec = IndeterminateDerivation(
                        fact=name,
                        rule_id=rule["rule_id"], rule_version=rule["version"],
                        source=rule.get("source", {}),
                        verification_status=rule.get("verification_status",
                                                     "UNVERIFIED"),
                        missing_facts=missing,
                        reason=(f"Cannot derive {name}: rule condition is "
                                f"indeterminate. Missing: {', '.join(missing)}."),
                        derived_in_pass=pass_no)
                    if not any(x.fact == name and x.rule_id == rec.rule_id
                               for x in indeterminate):
                        indeterminate.append(rec)
                continue

            # condition TRUE
            for spec in specs:
                try:
                    outcome = execute_derivation(spec, working, rule, pass_no)
                except DerivationError as e:
                    warnings.append({
                        "type": "DERIVATION_ERROR", "severity": "error",
                        "rule_id": rule["rule_id"],
                        "message": str(e),
                    })
                    continue

                if isinstance(outcome, IndeterminateDerivation):
                    if not any(x.fact == outcome.fact
                               and x.rule_id == outcome.rule_id
                               for x in indeterminate):
                        indeterminate.append(outcome)
                    continue

                sig = outcome.signature()
                if sig in seen_signatures:
                    suppressed_repeats += 1
                    continue
                seen_signatures.add(sig)
                new_signature_seen = True
                produced_this_pass.setdefault(outcome.fact, []).append(outcome)

        if not produced_this_pass and not new_signature_seen:
            break   # quiescence

        # ── merge, detecting contradiction ──
        merged_any = False
        for name, candidates in sorted(produced_this_pass.items()):
            prior = derived_facts.get(name)
            all_for_fact = ([prior] if prior else []) + candidates
            distinct = {repr(d.value) for d in all_for_fact}

            if name in supplied_names:
                warnings.append({
                    "type": "DERIVATION_SHADOWS_SUPPLIED_FACT",
                    "severity": "warning", "fact": name,
                    "rule_id": candidates[0].rule_id,
                    "message": (f"Rule {candidates[0].rule_id} derives {name}, "
                                "which the applicant also supplied. The supplied "
                                "value is retained; the derivation is recorded "
                                "but not merged."),
                })
                continue

            if len(distinct) > 1:
                conflict = DerivedFactConflict(
                    fact=name,
                    competing=[d.as_dict() for d in all_for_fact],
                    derived_in_pass=pass_no)
                conflicts.append(conflict)
                contradicted.add(name)
                derived_facts.pop(name, None)
                working.pop(name, None)
                warnings.append({
                    "type": "DERIVED_FACT_CONFLICT", "severity": "error",
                    "fact": name,
                    "rules": sorted({d.rule_id for d in all_for_fact}),
                    "message": (f"Contradictory derivations of {name}: "
                                + "; ".join(f"{d.rule_id} -> {d.value!r}"
                                            for d in all_for_fact)
                                + ". The fact is withheld; consumers evaluate "
                                  "to UNKNOWN."),
                })
                continue

            if name in contradicted:
                continue

            chosen = candidates[0]
            if prior is None:
                derived_facts[name] = chosen
                working[name] = chosen.value
                merged_any = True

        if not merged_any:
            break

    else:
        # loop exhausted without break -> bound hit
        warnings.append({
            "type": "INFERENCE_LIMIT_EXCEEDED", "severity": "error",
            "max_passes": max_passes,
            "message": (f"Derivation did not reach a fixed point within "
                        f"{max_passes} passes. This indicates an inference "
                        "cycle or oscillating derivation. Results are partial."),
        })

    # indeterminate records superseded by a later successful derivation
    indeterminate = [i for i in indeterminate
                     if i.fact not in derived_facts]

    # ── requirement evaluation, once, against the settled fact set ──
    collected = {}
    rules_run = 0

    for rule_id in registry.rule_ids:
        rule = select_version(registry.versions_of(rule_id), as_of)
        if rule is None:
            warnings.append({
                "type": "NO_VERSION_IN_FORCE", "severity": "warning",
                "rule_id": rule_id,
                "message": f"No version of {rule_id} was in force on {as_of}.",
            })
            continue

        effect = rule.get("effect", {})
        if not (effect.get("requires") or effect.get("excludes")):
            continue

        rules_run += 1
        result, trace = evaluate(rule["condition"], working)

        rule_evidence = {
            "rule_id": rule["rule_id"],
            "version": rule["version"],
            "rule_name": rule["name"],
            "result": result.value,
            "facts_used": _annotate_trace(trace, derived_facts),
            "source": rule.get("source", {}),
            "verification_status": rule.get("verification_status", "UNVERIFIED"),
            "last_verified": rule.get("last_verified"),
            "note": rule.get("note"),
        }
        sid = rule.get("source", {}).get("source_id")
        if sid and sid in registry.sources:
            rule_evidence["source_detail"] = registry.sources[sid]

        used_derived = [t["fact"] for t in trace if t["fact"] in derived_facts]
        if used_derived:
            rule_evidence["derived_facts_used"] = [
                derived_facts[f].as_dict() for f in sorted(set(used_derived))]

        for effect_key in ("requires", "excludes"):
            kind = classify(effect_key, result.value)
            if kind is None:
                continue
            for req_id in effect.get(effect_key, []):
                collected.setdefault(req_id, []).append(
                    Evidence(kind, rule_evidence))

        if rule.get("verification_status") == "UNVERIFIED" and result is not F:
            warnings.append({
                "type": "UNVERIFIED_RULE", "severity": "warning",
                "rule_id": rule["rule_id"],
                "message": (f"{rule['rule_id']} is UNVERIFIED and affected the "
                            "outcome. Not usable as a demo claim."),
            })

    buckets = {s: [] for s in State}

    for req_id, evidences in sorted(collected.items()):
        state, reasons, req_warnings = resolve(evidences)
        meta = registry.catalogue.get(req_id, {})

        item = {
            "requirement_id": req_id,
            "name": meta.get("name", req_id),
            "requirement_type": meta.get("requirement_type", "UNKNOWN"),
            "authority": meta.get("authority"),
            "department": meta.get("department"),
            "statute": meta.get("statute"),
            "sla_days": meta.get("sla_days"),
            "state": state.value,
            "evidence": [e.as_dict() for e in reasons],
            "confidence": _confidence(reasons),
        }

        missing = sorted({f for e in evidences for f in e.missing_facts})
        if missing:
            item["missing_facts"] = missing
            item["missing_fact_origin"] = {
                f: ("WITHHELD_DUE_TO_CONFLICT" if f in contradicted
                    else "NOT_SUPPLIED")
                for f in missing}

        if meta.get("quantity"):
            item["quantity"] = compute_quantity(meta["quantity"], working)

        deps = registry.dependencies.get(req_id, {})
        if deps.get("depends_on"):
            item["depends_on"] = deps["depends_on"]
            item["scheduling_depends_on"] = [
                d["requirement_id"]
                for d in registry.scheduling_dependencies(req_id)]
        if deps.get("candidate_dependencies"):
            item["candidate_dependencies"] = deps["candidate_dependencies"]

        for w in req_warnings:
            w = dict(w)
            w["requirement_id"] = req_id
            warnings.append(w)

        buckets[state].append(item)

    return {
        "as_of": as_of.isoformat(),
        "summary": {
            "applicable": len(buckets[State.APPLICABLE]),
            "not_applicable": len(buckets[State.NOT_APPLICABLE]),
            "unknown": len(buckets[State.UNKNOWN]),
            "conflict": len(buckets[State.CONFLICT]),
            "derived_facts": len(derived_facts),
            "indeterminate_derivations": len(indeterminate),
            "derived_fact_conflicts": len(conflicts),
            "derivation_passes": passes_run,
            "rules_evaluated": rules_run,
            "warnings": len(warnings),
        },
        "applicable": buckets[State.APPLICABLE],
        "not_applicable": buckets[State.NOT_APPLICABLE],
        "unknown": buckets[State.UNKNOWN],
        "conflict": buckets[State.CONFLICT],
        "derived_facts": {k: v.as_dict() for k, v in sorted(derived_facts.items())},
        "indeterminate_derivations": [i.as_dict() for i in indeterminate],
        "derived_fact_conflicts": [c.as_dict() for c in conflicts],
        "derivation_diagnostics": {
            "passes_run": passes_run,
            "max_passes": max_passes,
            "repeated_derivations_suppressed": suppressed_repeats,
            "reached_fixed_point": passes_run < max_passes,
        },
        "warnings": warnings,
    }


def _annotate_trace(trace, derived_facts):
    out = []
    for t in trace:
        t = dict(t)
        t["fact_origin"] = ("DERIVED" if t["fact"] in derived_facts
                            else "SUPPLIED")
        out.append(t)
    return out


def _confidence(evidences):
    statuses = {e.rule.get("verification_status") for e in evidences}
    if "UNVERIFIED" in statuses:
        return "low"
    if "SECONDARY" in statuses:
        return "medium"
    return "high"
