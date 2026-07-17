# Anchored Summary — MAPA Generator Fix v1.2.0

## Objective
Execute `docs/plan-full-mapa-fix.md` (canonical v1.2.0, 781 lines) — kill 25 findings from `systemic_review_findings.md`.

## Progress

| Phase | Status | % |
|-------|--------|----|
| Phase 0 (rounding fix) | ✅ DONE | 100% |
| Phase 1 (impl engine) | ✅ DONE | 100% |
| Phase 4 (live evidence) | ✅ DONE | 100% |
| Phase 3 (satellite stats) | ✅ DONE | 100% |
| Phase 2 (structure contracts) | ✅ DONE | 100% |
| Phase 5 (test integrity) | ✅ DONE | 100% |
| Phase 6 (sentinels) | ⬜ PENDING | 0% |
| Final | ⬜ PENDING | 0% |

## Important Details
- Phase 0: `_unrounded_total_g` in result dict (L2919), validate_output() uses it (L3066). All 32 tests pass.
- Phase 1: `doc_introspector.py` with `ImplCheck`, `IMPLEMENTATION_SPEC` (10 entries), `ImplIntrospector` (55 toplevel funcs, 6 CLI modes); `tests/reference_cases.py` exports 3 names; `build_pipeline.py` L1192-L1207 replaced with live introspection table (6 columns + provenance markers). `call_lp_solver`=IMPLEMENTED, 3 MISSING funcs correctly flagged.
- Phase 4: Tasks 4-1 `capture_live_evidence()` (4 smoke runs with 6 LP-specific fields), 4-2 `scrub_volatile()` (5 regex subs + set repr normalization, idempotent), 4-3 `section18_live_evidence()` wired into `generate_mapa()` + `--no-live-evidence` flag. MAPA regenerates with 4 evidence blocks + provenance markers. **Idempotency fixed**: 5 sources addressed (top-level timestamp, set ordering, solve_time_ms constant, set repr normalization). Two consecutive runs produce byte-identical SHA256.
- Phase 3: `compute_satellite_stats()` with `SATELLITE_BUNDLES`/`FILE_LOCATION_MAP` added to `doc_introspector.py`, wired into `section1_header()`. Live bundle table in MAPA Section 1: `sat_pipeline_codigo.md`=1001, `BUNDLE_IMPL_PIPELINE`=1669 (matches Finding #2 actual: 290+1001+378). Provenance markers per row.
- Phase 2: `STRUCTURE_CONTRACTS` (9 contracts including D8 v1.2 NUTRIENT_REGISTRY safety_hard=8 with sul_value), `check_structure_contracts()` added to `doc_introspector.py`, wired into `validate_mapa()` as Check 9. All 9 contracts pass against real `data/` files.
- Findings killed so far: #1, #2, #3, #4, #6, #9, #10, #11, #13, #14, #15, #16, #18, #19, #20, #21, #22, #23, #24

## Next Move
Phase 5: Implement `check_test_integrity()` with D6 regex (detect `bp.load_all_jsons` not `json.load` literals), wire as Check 9/10 in `validate_mapa()`. Then Phase 6: sentinels + gate hardening.

## Relevant Files
- `doc_introspector.py` — ImplCheck, IMPLEMENTATION_SPEC (10), ImplIntrospector, capture_live_evidence, scrub_volatile, compute_satellite_stats, STRUCTURE_CONTRACTS (9), check_structure_contracts
- `tests/reference_cases.py` — REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID
- `build_pipeline.py` — L1192-L1207 live impl_gaps table, L440 timestamp fixed, section7 set ordering fixed, section1_header() with compute_satellite_stats, validate_mapa() Check 9 structure contracts, section18_live_evidence + --no-live-evidence flag
- `docs/plan-full-mapa-fix.md` — canonical plan
- `docs/plan-mapa-generator-quicky-v1.2.md` — updated (Phases 0-1, 4, 3, 2: 100%)
- `data/*.json` — **DO NOT MODIFY**