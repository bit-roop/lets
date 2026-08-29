"""Explicit demonstrations of the four derived-fact behaviours. Run, don't assume."""
import copy, json
from datetime import date
from pathlib import Path
from engine.derive import Registry, derive, MAX_DERIVATION_PASSES

REG = Registry(Path("regulatory"))
TODAY = date(2026, 8, 29)

def synth(rid, cond_fact, cond_val, dfact, dval, vtype="boolean", **extra):
    d = {"fact": dfact, "operation": "constant", "value": dval, "value_type": vtype}
    d.update(extra)
    return {"rule_id": rid, "version": 1, "requirement_id": "TEST", "name": rid,
            "condition": {"all": [{"fact": cond_fact, "op": "==", "value": cond_val}]},
            "effect": {"derives": [d]},
            "source": {"statute": "synthetic demo rule", "effective_from": "2020-01-01",
                       "effective_to": None},
            "verification_status": "SECONDARY", "last_verified": "2026-08-29"}

def with_rules(extra):
    r = copy.deepcopy(REG); r.rules = list(REG.rules) + extra; return r

def hdr(t): print("\n" + "=" * 72); print(f"  {t}"); print("=" * 72)

# 1 — successful derivation
hdr("1. SUCCESSFUL DERIVATION (real rule, real source)")
out = derive({"investment_plant_machinery": 60_000_000,
              "annual_turnover": 80_000_000}, REG, TODAY)
df = out["derived_facts"]["msme_eligible"]
print(f"  msme_eligible = {df['value']}")
print(f"    derived by     {df['rule_id']}@v{df['rule_version']}  [{df['verification_status']}]")
print(f"    operation      {df['operation']} -> {df['value_type']}")
print(f"    source_id      {df['source']['source_id']}")
print(f"    instrument     {df['source']['instrument']}")
print(f"    effective_from {df['source']['effective_from']}")
print(f"    derived_at     {df['derived_at']}  (pass {df['derived_in_pass']})")
src = REG.sources[df['source']['source_id']]
print(f"    resolves to    {src['document_number']} dt. {src['document_date']} "
      f"[{src['verification_status']}]")
print(f"  Q: why does the system believe this?")
print(f"  A: rule {df['rule_id']} fired on investment_plant_machinery and "
      f"annual_turnover,\n     citing {src['document_number']}. No LLM involved.")

# 2 — missing input
hdr("2. MISSING INPUT (never false, never invented)")
out = derive({"investment_plant_machinery": 60_000_000}, REG, TODAY)
ind = [i for i in out["indeterminate_derivations"] if i["fact"] == "msme_eligible"][0]
print(f"  msme_eligible in derived_facts? {'msme_eligible' in out['derived_facts']}")
print(f"  indeterminate record:")
print(f"    fact           {ind['fact']}")
print(f"    missing_facts  {ind['missing_facts']}")
print(f"    rule_id        {ind['rule_id']}@v{ind['rule_version']}")
print(f"    reason         {ind['reason']}")
print(f"    value invented? {'value' in ind}")

# 3 — conflict
hdr("3. CONFLICTING DERIVATIONS (no silent selection)")
r = with_rules([
    synth("DEMO-CONF-A", "x", 1, "tier", "SMALL", "enum", enum_values=["SMALL","MEDIUM"]),
    synth("DEMO-CONF-B", "x", 1, "tier", "MEDIUM", "enum", enum_values=["SMALL","MEDIUM"]),
    {"rule_id": "DEMO-CONSUMER", "version": 1, "requirement_id": "E-05",
     "name": "consumer of tier",
     "condition": {"all": [{"fact": "tier", "op": "==", "value": "SMALL"}]},
     "effect": {"requires": ["E-05"]},
     "source": {"statute": "synthetic", "effective_from": "2020-01-01", "effective_to": None},
     "verification_status": "SECONDARY", "last_verified": "2026-08-29"}])
out = derive({"x": 1}, r, TODAY)
c = out["derived_fact_conflicts"][0]
print(f"  fact             {c['fact']}")
print(f"  competing_values {c['competing_values']}")
print(f"  resolution       {c['resolution']}")
for d in c["competing_derivations"]:
    print(f"    {d['rule_id']}@v{d['rule_version']} -> {d['value']!r}  [{d['verification_status']}]")
print(f"  merged into fact set? {'tier' in out['derived_facts']}")
item = [i for i in out["unknown"] if i["requirement_id"] == "E-05"]
if item:
    print(f"  downstream E-05 state: {item[0]['state']}")
    print(f"  missing_fact_origin:   {item[0]['missing_fact_origin']}")

# 4 — cycle protection
hdr("4. CYCLE PROTECTION (a -> b -> c -> a)")
r = with_rules([synth("DEMO-CY-1", "a", True, "b", True),
                synth("DEMO-CY-2", "b", True, "c", True),
                synth("DEMO-CY-3", "c", True, "a", True)])
out = derive({"a": True}, r, TODAY)
d = out["derivation_diagnostics"]
print(f"  passes_run                     {d['passes_run']} (bound {d['max_passes']})")
print(f"  reached_fixed_point            {d['reached_fixed_point']}")
print(f"  repeated_derivations_suppressed {d['repeated_derivations_suppressed']}")
print(f"  derived                        {sorted(out['derived_facts'])}")
for w in out["warnings"]:
    if w["type"] == "DERIVATION_SHADOWS_SUPPLIED_FACT":
        print(f"  warning: {w['type']} on '{w['fact']}'")
print("\n  static detection on the same shape:")
from engine.validate_data import _validate_inference_cycles
class F: rules = [synth("S1","a",True,"b",True), synth("S2","b",True,"c",True),
                  synth("S3","c",True,"a",True)]
for i in _validate_inference_cycles(F()):
    print(f"    {i}")

hdr("5. PASS-LIMIT ENFORCEMENT (bound deliberately set to 2)")
r = with_rules([synth("DEMO-L1","seed",1,"p",True), synth("DEMO-L2","p",True,"q",True),
                synth("DEMO-L3","q",True,"s",True)])
out = derive({"seed": 1}, r, TODAY, max_passes=2)
print(f"  passes_run          {out['summary']['derivation_passes']}")
print(f"  reached_fixed_point {out['derivation_diagnostics']['reached_fixed_point']}")
print(f"  derived             {sorted(out['derived_facts'])}")
for w in out["warnings"]:
    if w["type"] == "INFERENCE_LIMIT_EXCEEDED":
        print(f"  {w['type']}: {w['message']}")
