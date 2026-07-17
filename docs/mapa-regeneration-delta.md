## MAPA Regeneration Delta

**Baseline:** `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md.orig-bak` (53,677 bytes)
**Regenerated:** `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` (61,722 bytes)
**Delta:** +8,045 bytes (+15%)

---

### Changes (all findings reference `systemic_review_findings.md`)

| Section | Change | Finding Ref |
|---------|--------|-------------|
| Section 1 (Implementation Roadmap) | **REMOVED** — hardcoded roadmap text replaced by sentinel-based extraction from `indice_plano_central.md` | #1 |
| Section 1 (Impl Gaps Table) | **REWRITTEN** — old hardcoded `impl_gaps = ["call_lp_solver", "dynamic_envelope", ...]` replaced by `IMPLEMENTATION_SPEC` introspection with live line numbers and provenance markers | #1, #2 |
| Section 1 (Satellite Stats) | **ADDED** — live `compute_satellite_stats()` results (7 satellites with line counts, bundle sizes, LOC) | #10, #19 |
| Section 18 (Live Evidence) | **ADDED** — 4 smoke-run evidence blocks (liver-only L3, 5-ingredient L2, empty L2, chicken-heart L2) with 6 LP-specific fields scrubbed of volatile content | #17, #21 |
| Section 1 (Duplicate fat_sources) | **REMOVED** — duplicate `fat_sources` row in curation table eliminated by sentinel extraction | #2 |
| Checks 9–15 | **ADDED** — `validate_mapa()` expanded from 10 to 15 checks (test integrity, self-count, spec drift, sentinel presence, AUTO immutability, implementation spec drift, structure contracts) | #13–#16, #25 |

### Files Modified

| File | Change |
|------|--------|
| `build_pipeline.py` | `section1_header()` rewritten (sentinel-based), `validate_mapa()` expanded to 15 checks. |
| `doc_introspector.py` | `ImplIntrospector` class, `IMPLEMENTATION_SPEC` (10 entries), `capture_live_evidence()`, `scrub_volatile()`, `compute_satellite_stats()`, `STRUCTURE_CONTRACTS` (9 contracts), `check_structure_contracts()`, `check_test_integrity()` |
| `tests/reference_cases.py` | `REFERENCE_ANIMAL`, `REFERENCE_SELECTION`, `REFERENCE_SCENARIO_ID` constants |
| `indice_plano_central.md` | 4 sentinels placed (STATIC-START, STATIC-END, AUTO-BUNDLES, AUTO-ROADMAP) |


### Verification

- All 15 `validate_mapa` checks pass
- 32 pytest tests pass
- Idempotency: two consecutive MAPA generations produce byte-identical SHA256 (`cb1ce62eb5c0b9e1...`)
- Read-only: zero `*.py` files modified during generation
- Q0: `--runtime` with 5-ingredient selection exits 0 (no AssertionError)
- Q4: 6 `load_all_jsons()` calls in `tests/test_cascade_integration.py`
- Q9: 8 LP-specific evidence field matches in MAPA
