# Mini-Repo Feature (easy)

Add feature support to `generate_plan` in `src/service.py`.

Input format: `name|owner|status|points`

New requirements:
- Respect `include_deferred` end-to-end.
- Support optional `include_status_breakdown=True` and include a `status_breakdown` map.
- Keep deterministic ordering by points desc then name asc.
- Keep existing behavior for callers that do not use new feature flags.
