import json, sys
from datetime import date
from pathlib import Path
from engine.derive import Registry, derive

reg = Registry(Path("regulatory"), validate=True)
persona = json.loads(Path(sys.argv[1]).read_text())
as_of = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2026,8,29)
facts = {k:v for k,v in persona.items() if not k.startswith("_")}
r = derive(facts, reg, as_of)

print("=" * 72)
print(f"  {persona['_name']}")
print(f"  as of {r['as_of']}")
print("=" * 72)
s = r["summary"]
print(f"  APPLICABLE {s['applicable']}  NOT_APPLICABLE {s['not_applicable']}  "
      f"UNKNOWN {s['unknown']}  CONFLICT {s['conflict']}")
print(f"  rules run {s['rules_evaluated']}   warnings {s['warnings']}")
print(f"  derived facts {s['derived_facts']}  indeterminate {s['indeterminate_derivations']}  "
      f"derived conflicts {s['derived_fact_conflicts']}  passes {s['derivation_passes']}\n")

if r["derived_facts"]:
    print("  --- DERIVED FACTS ---")
    for k, d in r["derived_facts"].items():
        print(f"  {k} = {d['value']!r}   via {d['rule_id']}@v{d['rule_version']} "
              f"[{d['verification_status']}] pass {d['derived_in_pass']}")
    print()
if r["indeterminate_derivations"]:
    print("  --- INDETERMINATE DERIVATIONS ---")
    for d in r["indeterminate_derivations"]:
        print(f"  {d['fact']}: missing {', '.join(d['missing_facts'])} ({d['rule_id']})")
    print()
if r["derived_fact_conflicts"]:
    print("  --- DERIVED FACT CONFLICTS ---")
    for c in r["derived_fact_conflicts"]:
        print(f"  {c['fact']}: {c['competing_values']} resolution={c['resolution']}")
    print()

for label, bucket in [("APPLICABLE","applicable"), ("CONFLICT","conflict"),
                      ("UNKNOWN","unknown"), ("NOT APPLICABLE","not_applicable")]:
    if not r[bucket]: continue
    print(f"  --- {label} ---")
    for i in r[bucket]:
        q = f"  x{i['quantity']['value']}" if i.get("quantity") and i["quantity"]["value"] else ""
        print(f"  {i['requirement_id']:7} {i['name']}{q}")
        print(f"          {i['requirement_type']:12} conf={i['confidence']}")
        if i.get("missing_facts"):
            print(f"          missing: {', '.join(i['missing_facts'])}")
        if bucket in ("not_applicable",):
            e = i["evidence"][0]
            print(f"          {e['evidence_kind']} via {e['rule_id']}")
    print()

if r["warnings"]:
    print("  --- WARNINGS ---")
    for w in r["warnings"]:
        print(f"  [{w['severity']}] {w['type']}: {w['message']}")
