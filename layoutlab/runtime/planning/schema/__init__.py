"""DD-017 Evaluation schema v0.1 — profiles, roles, intentions, scoring."""

from __future__ import annotations

from .intentions import INTENTIONS, validate_intention
from .profiles import (
    PROFILES,
    SCHEMA_VERSION,
    get_profile,
    list_profiles,
    resolve_profile_id,
)
from .roles import (
    HIGH_IMPACT_ROLES,
    ROLES,
    default_role_for_profile,
    is_high_impact,
    normalize_role,
)
from .scoring import (
    POSITIVE_CAP_PER_CATEGORY,
    SCORE_CATEGORIES,
    SEVERE_VETO_THRESHOLD,
    build_evaluation,
    classify_candidate_state,
    score_breakdown,
    soft_findings_to_components,
)

EVALUATION_SCHEMA = SCHEMA_VERSION  # "0.1.0"

__all__ = [
    "EVALUATION_SCHEMA",
    "HIGH_IMPACT_ROLES",
    "INTENTIONS",
    "POSITIVE_CAP_PER_CATEGORY",
    "PROFILES",
    "ROLES",
    "SCHEMA_VERSION",
    "SCORE_CATEGORIES",
    "SEVERE_VETO_THRESHOLD",
    "build_evaluation",
    "classify_candidate_state",
    "default_role_for_profile",
    "get_profile",
    "is_high_impact",
    "list_profiles",
    "normalize_role",
    "resolve_profile_id",
    "score_breakdown",
    "soft_findings_to_components",
    "validate_intention",
]
