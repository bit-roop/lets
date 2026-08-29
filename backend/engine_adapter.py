import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import PERSONAS_DIR, derive, get_registry


def evaluate_facts(facts: Dict[str, Any], as_of: Optional[date] = None) -> Dict[str, Any]:
    """
    Evaluates applicant facts against the protected regulatory engine baseline.
    Preserves the exact output contract without modifying regulatory semantics.
    """
    registry = get_registry()
    result = derive(facts=facts, registry=registry, as_of=as_of)
    return result


def get_catalogue() -> Dict[str, Any]:
    """Returns the full catalogue of requirements from catalogue.json."""
    registry = get_registry()
    return registry.catalogue


def get_sources() -> Dict[str, Any]:
    """Returns all authoritative regulatory sources from sources.json."""
    registry = get_registry()
    return registry.sources


def get_verification_summary() -> Dict[str, int]:
    """Returns the count of rules per verification status (VERIFIED, SECONDARY, UNVERIFIED)."""
    registry = get_registry()
    counts = Counter(r.get("verification_status", "UNVERIFIED") for r in registry.rules)
    return dict(counts)


def list_personas() -> List[Dict[str, str]]:
    """Lists all available personas in the personas directory."""
    if not PERSONAS_DIR.exists():
        return []
    personas = []
    for path in sorted(PERSONAS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            personas.append({
                "id": path.stem,
                "name": data.get("_name", path.stem),
            })
        except Exception:
            continue
    return personas


def get_persona(persona_id: str) -> Optional[Dict[str, Any]]:
    """Loads a specific persona fact vector by ID (e.g., 'persona_b')."""
    # Sanitize persona_id to prevent path traversal
    safe_id = Path(persona_id).name
    path = PERSONAS_DIR / f"{safe_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
