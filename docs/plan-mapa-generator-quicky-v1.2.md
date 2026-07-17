# MAPA Generator Fix — Quicky v1.2 (ALL PHASES COMPLETE)
> `docs/plan-full-mapa-fix.md` (781 lines) · `docs/governance/systemic_review_findings.md` (25 findings — 21 killed, 4 qualitative/no-action)

---

## Overall Progress — ALL PHASES COMPLETE

```
████████████████████████████████████████   100%
```

| File | Role | Status |
|------|------|--------|
| `build_pipeline.py` | Main edits (`generate_mapa`, `validate_mapa`, sentinel extraction, live evidence, shadow retired) | DONE |
| `doc_introspector.py` | `ImplIntrospector`, `IMPLEMENTATION_SPEC` (10), `STRUCTURE_CONTRACTS` (9), `check_test_integrity()` | DONE |
| `tests/reference_cases.py` | `REFERENCE_ANIMAL`, `REFERENCE_SELECTION`, `REFERENCE_SCENARIO_ID` | DONE |
| `indice_plano_central.md` | 4 sentinels (STATIC-START/END, AUTO-BUNDLES, AUTO-ROADMAP) | DONE |
| `docs/migration-log.md` | Shadow mode results + retirement sign-off | DONE |
| `docs/mapa-regeneration-delta.md` | MAPA diff vs `.orig-bak` (+8,045 bytes) | DONE |
| `data/*.json` | **DO NOT MODIFY** | N/A |

---

## Phase 0 — Pre-flight (rounding fix) — DONE

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 0-zero | Preflight sanity check (0.05g gap from F#18) | DONE | `docs/phase0-preflight-sanity.md` |
| 0a-1 | Rounding-fix design doc (Option A/B) | DONE | `docs/phase0a-tolerance-design.md` |
| 0a-2 | Call-site audit (validate_output + round at L2857) | DONE | `docs/phase0a-callsite-audit.md` |
| 0c-1 | Rounding policy audit at L2857 | DONE | `docs/phase0c-rounding-policy.md` |
| 0b-1 | Apply Option A fix | DONE | `build_pipeline.py` `_unrounded_total_g` at L2919, `validate_output()` at L3066 |

---

## Phase 1 — Introspector + Live impl_gaps — DONE

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 1-1 | `reference_cases.py` — 5 oracles | DONE | File exists, `len(REFERENCE_SELECTION)` = 5 |
| 1-2 | `IMPLEMENTATION_SPEC` dataclass | DONE | `doc_introspector.py`, 10 entries |
| 1-3 | `ImplIntrospector` + AST walk | DONE | 55 toplevel funcs, 6 CLI modes, 10 IMPLEMENTATION_SPEC entries |
| 1-4 | Wire into `generate_mapa()` | DONE | Live check replaces static `impl_gaps`, 10 provenance markers |

**Findings killed:** #1 (false NOT IMPLEMENTED) · #4/#20 (missing functions) · #21/#22/#23 (correctly IMPLEMENTED) · #24 (correctly NOT IMPLEMENTED)

---

## Phase 2 — STRUCTURE_CONTRACTS — DONE

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 2-1 | `STRUCTURE_CONTRACTS` (9 contracts) + `check_structure_contracts()` | DONE | All 9 contracts pass against real data |
| | D8 v1.2: NUTRIENT_REGISTRY 8x safety_hard with sul_value | DONE | Contract #9 passes |
| | Wired into `validate_mapa()` as Check 9 | DONE | Gate passes |

**Findings killed:** #3 · #6 · #9 · #13 · #14 · #15 · #16

---

## Phase 3 — Satellite Stats — DONE

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 3-1 | `compute_satellite_stats()` — per-file line counts, bundle totals | DONE | `sat_pipeline_codigo.md`=1001, `BUNDLE_IMPL_PIPELINE`=1669 |
| 3-2 | Wire into `section1_header()` — replaces hardcoded ~N estimates | DONE | Live table in Section 1 with provenance markers |

**Findings killed:** #2 (duplicate row) · #10 (line counts) · #19 (5x undercount)

---

## Phase 4 — Live Evidence — DONE

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 4-1 | `capture_live_evidence()` — 4 smoke runs, 6 LP fields each | DONE | Section 18 embedded |
| 4-2 | `scrub_volatile()` — 5 regex + set repr, idempotent | DONE | Byte-identical MAPA on consecutive runs |
| 4-3 | `--no-live-evidence` flag for CI | DONE | Flag works |

**Findings killed:** #18 (envelope bug via DER smoke)

---

## Phase 5 — Test Integrity — DONE

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 5-1 | `check_test_integrity()` — D6 v1.2 regex (AST walking for `@pytest.mark.integration`) | DONE | Check 10 in `validate_mapa()`, `loads_real_data=True` for both test files |
| ~~5-2~~ | ~~Rewrite tests~~ | DELETED | Tests already use `bp.load_all_jsons()` — D1 correct |

**Finding killed:** #17 (tests use fixtures)

---

## Phase 6 — Sentinels + Anti-Regression — DONE

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 6-1 | HTML sentinels in `indice_plano_central.md` | DONE | L1, L196, L197, L218 |
| 6-2 | `section1_header()` sentinel-based extraction | DONE | Replaces broken regex. Finding #2 (hardcoded `fat_sources`) killed |
| 6-3 | Checks 9-13 in `validate_mapa()` | DONE | 15 checks total, all pass |
| 6-4 | Shadow mode (added then retired per F-1) | DONE | `_SHADOW_MODE` + `_OLD_IMPL_GAPS_REFERENCE` + `run_shadow_comparison()` + `write_migration_log()` + `--shadow-mode` flag all removed |

---

## Final Phase — Regen + Certify — DONE

| Step | What | Status | Evidence |
|------|------|--------|----------|
| F-1a | Regenerate MAPA | DONE | 61,722 bytes, 15 checks pass |
| F-1b | Validate gate | DONE | ALL CHECKS PASSED |
| F-1c | Certify — all findings addressed, all Q0-Q9 hold | DONE | 32 tests pass, MAPA deterministic, read-only verified |
| F-1d | Retire shadow mode | DONE | ~65 lines dead code removed, migration-log signed off |

---

## Kill Chain (Finding -> Phase)

| Finding | Phase | | Finding | Phase |
|---------|-------|---|---------|-------|
| #1 impl gaps false neg | Ph1 + Ph4 | | #13/#14/#15/#16 JSON struct drift | Ph2 |
| #4/#20 missing functions | Ph1 | | #2/#3/#10/#19 stale counts | Ph3 |
| #18 envelope bug | Ph0 + Ph4 | | #17 test integrity | Ph5 |
| #2 hardcoded fat_sources duplicate | Ph6 | | #15/#16 structure contracts | Ph2 |

**No action needed:** qualitatives Q1-Q4, retracted #5, matches (24 items)

---

## Commands

```powershell
validate  -> python build_pipeline.py --validate-db
generate  -> python build_pipeline.py --generate-mapa
gate      -> python build_pipeline.py --gate-mapa
audit     -> python build_pipeline.py --audit-mapa
tests     -> pytest tests/ -v
single    -> pytest tests/test_cascade_integration.py::test_name -v
```

---

## Definition of Done

- [x] All 25 findings addressed (21 killed, 4 qualitative/no-action)
- [x] 15 checks in `validate_mapa()` all pass
- [x] All postconditions Q0-Q9 hold
- [x] MAPA deterministic (SHA256 stable across consecutive runs)
- [x] Read-only (zero source files modified during generation)
- [x] 32 tests pass
- [x] Shadow mode retired (migration-log signed off)
- [x] Delta documented (`docs/mapa-regeneration-delta.md`)
