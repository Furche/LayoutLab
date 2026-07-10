# DD-008 — Constraints and Layout Analysis

**Status:** Placeholder (not started — depends on DD-007)  
**Date:** —  
**Version:** —

------------------------------------------------------------------------

This document is **intentionally empty** until [DD-007 — Clearance Zones](DD-007-clearance-zones.md) is accepted and the clearance API + export schema are implemented.

## Planned scope (for index only)

- Constraint types (`must_be_clear`, `minimum_free_width`, `must_not_overlap_geometry`, …)
- Relationship: Constraint Engine **reads** Clearance Zones + geometry; does not create zones
- `analyze_layout` JSON command — request/response contract
- Bed entry rules as **first product test case** (after wardrobe reference clearances)

**Do not implement analyze_layout before this DD is written and reviewed.**
