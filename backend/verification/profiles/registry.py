"""Profile registry: document_id -> VerificationProfile."""

from pathlib import Path
from typing import Dict, List, Optional

from .. import m4_gateway
from .loader import PROFILE_ROOT, ProfileError, VerificationProfile, load_all


class ProfileRegistry:
    def __init__(self, root: Path = PROFILE_ROOT):
        self.root = Path(root)
        known = set(m4_gateway.document_ids())
        unsupported = {
            r.document_id for r in m4_gateway.all_requirements()
            if r.verification_status == "UNSUPPORTED"
        }
        self.profiles: Dict[str, VerificationProfile] = load_all(
            self.root, known, m4_gateway.spec, unsupported)

    def get(self, document_id: str) -> Optional[VerificationProfile]:
        return self.profiles.get(document_id)

    def all(self) -> List[VerificationProfile]:
        return [self.profiles[k] for k in sorted(self.profiles)]

    def profiled_document_ids(self) -> List[str]:
        return sorted(self.profiles)

    def unprofiled_upload_document_ids(self) -> List[str]:
        """Upload documents M4 requires that M5 has not been taught to read."""
        out = []
        for document_id in sorted(set(m4_gateway.document_ids())):
            if document_id in self.profiles:
                continue
            spec = m4_gateway.spec(document_id)
            if spec.item_kind == "UPLOAD_DOCUMENT":
                out.append(document_id)
        return out


_registry: Optional[ProfileRegistry] = None


def get_profile_registry() -> ProfileRegistry:
    global _registry
    if _registry is None:
        _registry = ProfileRegistry()
    return _registry


def reset_profile_registry():
    """Test hook only."""
    global _registry
    _registry = None
