import sys
from pathlib import Path

# Paths configuration
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
ENGINE_V3_DIR = PROJECT_ROOT / "engine-v3"
REGULATORY_DATA_DIR = ENGINE_V3_DIR / "regulatory"
PERSONAS_DIR = ENGINE_V3_DIR / "personas"

# Add engine-v3 to python path so its modules can be imported
if str(ENGINE_V3_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_V3_DIR))

from engine.derive import Registry, derive

# Singleton registry initialized once at startup
_registry_instance = None


def get_registry() -> Registry:
    """Returns the singleton Registry instance loaded from engine-v3/regulatory."""
    global _registry_instance
    if _registry_instance is None:
        if not REGULATORY_DATA_DIR.exists():
            raise FileNotFoundError(f"Regulatory data directory not found at: {REGULATORY_DATA_DIR}")
        _registry_instance = Registry(REGULATORY_DATA_DIR, validate=True, strict=True)
    return _registry_instance
