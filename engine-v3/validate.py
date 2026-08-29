import sys
from pathlib import Path
from engine.derive import Registry

reg = Registry(Path("regulatory"), validate=True, strict=False)
errs = [i for i in reg.issues if i.severity == "error"]
warns = [i for i in reg.issues if i.severity == "warning"]

print("=" * 70)
print("REGULATORY DATA VALIDATION")
print("=" * 70)
print(f"  requirements {len(reg.catalogue)}   rules {len(reg.rules)}   "
      f"sources {len(reg.sources)}")
print(f"  errors {len(errs)}   warnings {len(warns)}\n")
for i in errs:
    print(f"  {i}")
if errs and warns: print()
for i in warns:
    print(f"  {i}")
sys.exit(1 if errs else 0)
