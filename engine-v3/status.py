"""Verification-status inventory. Run before any demo."""
from pathlib import Path
from collections import Counter
from engine.derive import Registry

reg = Registry(Path("regulatory"))
by = Counter(r["verification_status"] for r in reg.rules)
ids = lambda st: sorted({f"{r['rule_id']}@v{r['version']}"
                         for r in reg.rules if r["verification_status"] == st})

print("=" * 72)
print("  VERIFICATION STATUS INVENTORY")
print("=" * 72)
print(f"  rules {len(reg.rules)}   requirements {len(reg.catalogue)}   "
      f"sources {len(reg.sources)}\n")
for st, marker in [("VERIFIED", "OK  "), ("SECONDARY", "MED "), ("UNVERIFIED", "LOW ")]:
    print(f"  {st}  ({by[st]})")
    for i in ids(st):
        print(f"    {marker}{i}")
    print()
print("  DEMO RULE: only VERIFIED rules may be spoken as claims.")
print(f"  Currently safe to claim: {by['VERIFIED']} of {len(reg.rules)} rules "
      f"({by['VERIFIED']/len(reg.rules):.0%})")
