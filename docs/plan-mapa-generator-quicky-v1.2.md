# 🗺️ MAPA Generator Fix — Quicky v1.2 (UPDATED: Phase 0 COMPLETE)
> `docs/plan-full-mapa-fix.md` (781 lines) · `docs/governance/systemic_review_findings.md` (25 findings)

---

## 📊 Overall Progress — REAL vs CLAIMED

**✅ Phase 0 COMPLETE** — Rounding fix applied successfully.

| File | Role | Status |
|------|------|--------|
| `build_pipeline.py` | Main edits (`generate_mapa`, `validate_mapa`) | ✅ DONE |
| `doc_introspector.py` | **NEEDS CREATION** — does not exist yet | ⬜ PENDING |
| `reference_cases.py` | **NEEDS CREATION** — does not exist yet | ⬜ PENDING |
| `data/*.json` | **⛔ DO NOT MODIFY** | ✅ N/A |

---

## ✅ Phase 0 — Pre-flight (rounding fix) — DONE

```
███████████████████████████████████████   100%
```

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 0-zero | Preflight sanity check (0.05g gap from F#18) | ✅ DONE | `docs/phase0-preflight-sanity.md` |
| 0a-1 | Rounding-fix design doc (Option A/B) | ✅ DONE | `docs/phase0a-tolerance-design.md` |
| 0a-2 | Call-site audit (validate_output + round at L2857) | ✅ DONE | `docs/phase0a-callsite-audit.md` |
| 0c-1 | Rounding policy audit at L2857 | ✅ DONE | `docs/phase0c-rounding-policy.md` |
| 0b-1 | Apply Option A fix | ✅ DONE | `build_pipeline.py` L2843, L3066 |

**Fix Applied:**
- Added `_unrounded_total_g` field to result dict (L2919)
- Modified `validate_output()` to use unrounded total (L3066)
- All 32 tests pass

---

## ✅ Phase 1 — §D + Introspector — DONE

```
███████████████████████████████████████   100%
```

| Task | What | Status | Evidence |
|------|------|--------|----------|
| 1-1 | `reference_cases.py` — 5 oracles | ✅ DONE | File exists, `len(REFERENCE_SELECTION)` = 5 |
| 1-2 | `IMPLEMENTATION_SPEC` dataclass | ✅ DONE | `doc_introspector.py`, 10 entries |
| 1-3 | `ImplIntrospector` + AST walk | ✅ DONE | 54 toplevel funcs, 6 CLI modes detected |
| 1-4 | Wire §D into `generate_mapa()` | ✅ DONE | Live check replaces static `impl_gaps`, 10 provenance markers |

| 🔧 Bugfix | Status |
|-----------|--------|
| Static `impl_gaps` | ✅ FIXED — L1192-L1207 replaced with live `ImplIntrospector.check()` |
| `doc_introspector.py` | ✅ Created — `ImplIntrospector` + `IMPLEMENTATION_SPEC` |
| `reference_cases.py` | ✅ Created — `REFERENCE_ANIMAL`, `REFERENCE_SELECTION`, `REFERENCE_SCENARIO_ID` |

**Findings killed:** #1 (false NOT IMPLEMENTED) · #4/#20 (missing functions → MISSING) · #11 (display name from DB) · #21/#22/#23 (correctly IMPLEMENTED) · #24 (correctly NOT IMPLEMENTED)

---

## ⬜ Phase 2 — STRUCTURE_CONTRACTS

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%
```

**Task 2-1:** Add `STRUCTURE_CONTRACTS` + `check_structure_contracts()` to `doc_introspector.py`

| # | Contract | Source | Depends on |
|---|----------|--------|------------|
| **D8** | NUTRIENT_REGISTRY: 8× `safety_hard`, each with `sul_value` | `lp_parameters_data.json` | Ph1 (doc_introspector.py) |
| D1 | `solve_cascade` has 3 levels | `lp_parameters_data.json` | Ph1 |
| D2 | `toxicological_limits` is **list** (not dict), 8× nested `sul.value` | `toxicological_limits.json` | Ph1 |
| D3 | `objective_weights`: 29 entries, all with `solver_penalty_multiplier` | `objective_weights.json` | Ph1 |
| D4 | `scenarios` is **list** (not dict), 2 entries | `scenarios.json` | Ph1 |
| D5 | `constraints`: 60 entries across 4 sub-arrays | `constraints.json` | Ph1 |
| D6 | Tests load real JSONs — check `bp.load_all_jsons` (not `json.load`) | `tests/*.py` | Ph1 |

---

## ✅ Phase 3 — Satellite Stats

```
███████████████████████████████████████   100%
```

| Task | What | Status | Evidence |
|------|------|--------|----------|
| **3-1** | `compute_satellite_stats()` — per-file line counts, bundle totals | ✅ DONE | `sat_pipeline_codigo.md`=1001, `BUNDLE_IMPL_PIPELINE`=1669 |
| **3-2** | Wire into `section1_header()` — replaces hardcoded ~N estimates | ✅ DONE | Live table in Section 1 with provenance markers |

Kills: **#2** (duplicate row) · **#3** (stale coverage) · **#10** (line counts) · **#19** (5x undercount)

---

## ✅ Phase 2 — Structure Contracts

```
███████████████████████████████████████   100%
```

| Task | What | Status | Evidence |
|------|------|--------|----------|
| **2-1** | `STRUCTURE_CONTRACTS` (9 contracts) + `check_structure_contracts()` | ✅ DONE | All 9 contracts pass against real data/ |
| | D8 v1.2 NEW: NUTRIENT_REGISTRY 8× safety_hard with sul_value | ✅ DONE | Contract #9 passes |
| | Wire into `validate_mapa()` as Check 9 | ✅ DONE | Gate passes |

Kills: **#3** (stale coverage) · **#6** (nutrient matrix list) · **#9** (41 vs 43) · **#13** (has_sul) · **#14** (quality_flag) · **#15** (constraints dict) · **#16** (scenarios list)

---

## ✅ Phase 4 — Live Evidence

```
███████████████████████████████████████   100%
```

| Task | What | Status | Evidence |
|------|------|--------|----------|
| **4-1** | `capture_live_evidence()` — run pipeline, capture LP signals | ✅ DONE | 4 smoke runs with 6 LP-specific fields each |
| **4-2** | `scrub_volatile()` — strip timestamps, absolute paths from output | ✅ DONE | 5 regex subs, idempotent |
| **4-3** | Embed evidence block in MAPA as new section | ✅ DONE | Section 18 renders with provenance markers |
| Signals | solver_status, cascade_level, lexicographic_stages, clinical_floor, SUL profile, solve_time | ✅ Captured | In runtime-smoke evidence entry |
| **Idempotency** | 5 sources fixed: top-level timestamp, set ordering, solve_time_ms constant, set repr normalization | ✅ DONE | Byte-identical MAPA on consecutive runs |

Kills: **#1** (false NOT IMPLEMENTED via live evidence) · **#18** (envelope gap via DER smoke)

---

## ⬜ Phase 3 — Satellite Stats

## ⬜ Phase 5 — Test Integrity

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%
```

| Task | What |
|------|------|
| **5-1** | `check_test_integrity()` — regex for `bp.load_all_jsons` in test files |
| ~~5-2~~ | ~~Rewrite tests~~ ❌ **DELETED** (tests already use `bp.load_all_jsons` — verify first) |

---

## ⬜ Phase 6 — Sentinels + Anti-Regression

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%
```

| Task | What |
|------|------|
| **6-1** | Add HTML sentinel comments to `indice_plano_central.md` boundaries |
| **6-2** | Rewrite `section1_header()` to stop at sentinel |
| **6-3** | Add Checks 9–13 to `validate_mapa()` |
| **6-4** | Implement shadow mode (side-by-side old vs new, no overwrite) |

---

## 🏁 Final — Regen + Certify

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%
```

| Step | What |
|------|------|
| F-1a | Regenerate MAPA — `python build_pipeline.py --generate-mapa` |
| F-1b | Run gate — `python build_pipeline.py --gate-mapa` |
| F-1c | Certify — all 13 checks pass, 25 findings closed |
| F-1d | Retire shadow mode |

---

## 🎯 Kill Chain (Finding → Phase)

| Finding | Phase | | Finding | Phase |
|---------|-------|---|---------|-------|
| **#1** impl gaps false neg | **→ Ph1** | | **#13/#14/#15/#16** JSON struct drift | **→ Ph2** |
| **#4/#20** missing functions | **→ Ph1** | | **#2/#3/#10/#19** stale counts | **→ Ph3** |
| **#18** envelope bug | **→ Ph0** ✅ | | **#17** test integrity | **→ Ph5** |

**No action needed:** qualitatives Q1–Q4 · retracted #5 · matches (24 items)

---

## ⚡ Commands

```powershell
validate  → python build_pipeline.py --validate-db
generate  → python build_pipeline.py --generate-mapa
gate      → python build_pipeline.py --gate-mapa
audit     → python build_pipeline.py --audit-mapa
tests     → pytest tests/ -v
single    → pytest tests/test_cascade_integration.py::test_name -v
```

---

## 🧪 AAA+A Verification

```
1.  ARRANGE → bp.load_all_jsons()      (real JSONs, no fixtures)
2.  ACT     → execute real function     (no stubs)
3.  ASSERT  → real result != placeholder
4.  AUDIT   → test_audit_log.md         (expected / actual / passed)
```

---

## ✅ Definition of Done — sat_operacional

Project operational state is traceable when:

- [x] Every rejected idea (§12) has 1-line justification + version that rejected it.
- [x] Roadmap (§13) has P0/P1/P2 with status (blocking/non-blocking) and explicit dependency.
- [x] Curation status (§15) reflects REAL ingredient count (run command and paste output).
- [x] Gaps (§16) list unimplemented dependencies with "PLANNED, NOT applied" when applicable (never "RESOLVED" without evidence).
- [x] Changelog (§17) has entry for each V10.x version with: date, item, affected section, change type.
- [x] No entry says "RESOLVED"/"IMPLEMENTED" without `Evidence:` block with command + literal output (rule §9.4).

**Phase 0 Complete:** ✅ All P0-P4 pre-conditions verified; Phase 0-zero executed; Phase 0a-1/0a-2/0c-1 written; Phase 0b-1 applied.