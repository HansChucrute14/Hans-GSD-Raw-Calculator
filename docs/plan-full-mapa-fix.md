---
plan_id: plan-mapa-generator-fix
version: 1.2.0
generated: 2026-07-16
last_audited: 2026-07-16 (v1.2 specialist review applied — see plan-mapa-generator-fix-specialist-review.md)
v1_1_audit: 2026-07-16 (v1.1 audit applied — see plan-mapa-generator-fix-audit-v1.1.md)
parent_document: systemic_review_findings.md (827 lines canonical, 25 findings, 1 retracted)
repo_source: https://github.com/HansChucrute14/Hans-GSD-Raw-Calculator.git
canonical_findings_doc: docs/governance/systemic_review_findings.md (827 lines — supersedes any cached/uploaded version)
target_repo: C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\
language: en-US
audience: LLM agent (stateless executor — Claude/GPT/local)
handoff_protocol: LLM-to-LLM with atomic tasks, depends_on DAG, AAA+A verification, rollback
estimated_effort: 3-4 working days
blocking_prerequisites: 3 (Task 0-zero pre-flight sanity; Phase 0a — rounding-fix design + call-site audit; Phase 0c — rounding policy audit)
rollback_strategy: git revert per task + restore MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md.orig-bak
verification_pattern: AAA+A (Arrange real files, Act on real code, Assert on real output, Audit by literal command+output)
provenance_markers: HTML comments after every generated row (e.g. <!-- SOURCE: IMPLEMENTATION_SPEC[3] / build_pipeline.py:L1487 -->)
max_concurrent_tasks: 2 (Phase 0a-1 ‖ 0a-2 ‖ 0c-1; Phase 4-1 ‖ 4-2; rest sequential)
specialist_review_patches_applied:
  - D1: Finding #17 reclassified CRITICAL → INFO (tests already use bp.load_all_jsons)
  - D2: Phase 0a/0b redesigned — fix rounding site (L2857), not the comparison (L3063)
  - D3: IMPLEMENTATION_SPEC entries 8/9/10 reclassified inline_in → missing (functions do not exist)
  - D4: Phase 4 determinism concern tightened (LP solver already pinned)
  - D5: New Phase 0c added — rounding policy audit at L2857
  - D6: Check 9 regex rewritten to detect bp.load_all_jsons, not json.load literal
  - D7: Task 1-3 sub-step added — inspect main() structure before AST walking
  - D8: New STRUCTURE_CONTRACT added — NUTRIENT_REGISTRY safety_hard=8 with sul_value
  - D9: Phase 4 evidence capture expanded with LP-specific signals (solver status, lexicographic stages, clinical floor relaxation, SUL profile, solve time)
forbidden:
  - Modifying any data/*.json content
  - Adding Jinja2 or any template engine dependency
  - Regex-extracting "documented claims" from .md files for structure-contract comparison
  - Migrating generators to a new templating layer (fix in place)
  - Hand-editing generated MAPA sections after Phase 6 (anti-regression Check 13 enforces)
---

# Plan: MAPA Generator Fix — kills 25 findings, prevents recurrence via 13 anti-regression checks

## Section 0 — Context Boundary (READ FIRST)

The executing agent may assume and must not assume the following. Violating the "must not assume" list is the single most common cause of bad execution; treat it as a hard contract.

**May assume:**

- The 25 findings in `systemic_review_findings.md` are factually correct as of 2026-07-16 (re-verified twice in two independent sessions). **Read the canonical version at `docs/governance/systemic_review_findings.md` (827 lines) — it has 29 additional lines documenting 24 confirmed-correct MAPA claims that tell you what NOT to break.**
- `build_pipeline.py` (3458 lines, root of repo) is the single source of truth for pipeline behavior.
- All 11 JSON files in `data/` are stable in structure (their content may have been partially fixed by PR #8 — see "Must NOT assume" below).
- The 8 satellite `.md` files live in two subfolders: 6 in `docs/architecture/` (`indice_plano_central.md`, `sat_princípios.md`, `sat_dados_schema.md`, `sat_pipeline_fluxo.md`, `sat_pipeline_codigo.md`, `sat_solver_contrato.md`) and 2 in `docs/governance/` (`sat_testes_consolidado.md`, `sat_operacional.md`). Their prose content may update as a side effect of this plan (only Phase 6-1 touches them, and only to add HTML sentinel comments).
- Canonical directory structure: `data/` (11 JSONs), `docs/architecture/` (6 satellite .md + indice_plano_central), `docs/governance/` (2 satellite .md + systemic_review_findings.md), `docs/data-specs/` (INGREDIENTE_TEMPLATE_SPEC.md + PROMPT_PESQUISA_INGREDIENTE.md), `docs/archive/`, `docs/metadata/`, `tests/`.
- Tests use `pytest`; new tests must follow the AAA+A pattern mandated by `docs/governance/sat_testes_consolidado.md`.

**Must NOT assume:**

- That any number in the existing `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` is correct. Every value must be regenerated from live introspection. Findings #1, #2, #10, #19 document that hardcoded values have drifted by 24%–78%. **NOTE: Finding #19's "514% off" claim is BOGUS** — it conflates `sat_pipeline_codigo.md` (1001 lines per Finding #10) with `build_pipeline.py` (3458 lines, which the verification command actually measured). The real discrepancy for `sat_pipeline_codigo.md` is 78% (563 vs 1001), already covered by Finding #10.
- That function names in satellite `.md` specs match code. Verify via AST before claiming any implementation status (Findings #4, #20). Two doc-specified functions are inlined (DRIFT, not MISSING) — a different category requiring a different strategy in `IMPLEMENTATION_SPEC`.
- That JSON nesting matches doc claims. Verify via live `json.load()` before claiming any structure (Findings #13, #14, #15, #16). The v1 verification script produced 7 false positives from this exact assumption.
- That `upload/` JSON files match GitHub `data/` JSON files — they DON'T. All 11 files diverge by 116–8028 bytes (GitHub versions are smaller, suggesting PR #8 "fix/systemic-inconsistencies" may have applied partial fixes). **The GitHub `data/` versions are canonical.** Re-verify every structural contract against GitHub state at execution time — some findings may already be partially fixed.
- That Finding #12's file size table is ground truth. `lp_parameters.schema.json` actual GitHub size is 44294 bytes (Finding #12 claims 45356 — a 2.3% discrepancy). `db_ingredientes.schema.json` actual is 8135 bytes (Finding #12 claims 8312). Record actual sizes at execution time.
- That tests validate production behavior. **Tests DO load real data** via `bp.load_all_jsons()` (the production loader at `build_pipeline.py:86`) — verified by `rg -c "load_all_jsons" tests/` returning 7 matches across both test files. Finding #17's claim that "tests use fixtures, not real JSONs" is a FALSE POSITIVE: the reviewer's naive `grep "json.load\|open("` missed that the production loader wraps those calls. The real (minor) issue is DRY duplication of the reference animal between the two test files, addressed by Task 1-1. Do NOT rewrite the tests — Task 5-1 has been DELETED in v1.2.
- That `validate_output()` is bug-free. It has a known envelope-validation bug (Finding #18) — but the gap is **0.05g (rounding error from L2857's `round(grams, 1)`)**, NOT 1e-9 g (float precision). Fix the rounding site, not the comparison. Phase 0a/0b/0c cover this.
- That the doc-specified functions `format_allocations`, `expand_category_wildcards`, `run_pipeline` exist anywhere in `build_pipeline.py`. **They do NOT.** Verified by `rg "def format_allocations|def expand_category_wildcards|def run_pipeline" build_pipeline.py` returning zero matches. The source review (Qual #4, F #20) claimed they were "inlined" — that was a misreading of inline list-comprehension code at L2839-2853 (which lives inside `build_output_contract`, not `solve_cascade`). These three entries must use `missing` strategy in `IMPLEMENTATION_SPEC`, NOT `inline_in`.
- That the `section1_header()` heuristic at L427 "stops too early and misses content." It actually NEVER FIRES — `indice_plano_central.md` has no `## 3.` heading (its headings skip from `## 2.` to `## 11.`), so the entire file is copied verbatim. The sentinel fix (Phase 6-1) is still correct; only the description of the disease is "never stops copying," not "stops too early."
- That hardcoding `IMPLEMENTATION_SPEC` is the end of the work. The spec itself can drift (Critical Gap 2 from prior review). Check 11 enforces inverse drift detection.
- That the docstring's "8 checks" claim is accurate. The function implements 9 (Check 0 through Check 8). Check 10 fixes this self-count drift as the first real test case of the new system.

**Forbidden actions (violations abort the plan):**

- Modifying any `data/*.json` content. If a JSON looks wrong, log it as a new finding (Finding #26+) — do not fix.
- Adding Jinja2 or any template engine dependency. The `build_pipeline.py` docstring explicitly states "17 pure Python section generators (no Jinja2/placeholders)" — this is an architectural decision, not an oversight.
- Regex-extracting "documented claims" from `.md` files for the structure-contracts table. This produced 7 false positives in the reviewer's own v1 script (see "Verification Script Bugs Found" table in findings doc). Ground truth only — no NLP-guessing at prose.
- Migrating generators to a new file structure or templating layer. Fix the lies in place.
- Hand-editing generated MAPA sections after Phase 6 lands. Check 13 (AUTO immutability) catches this via git diff.

---

## Section 1 — Findings → Phases Mapping

Every finding in `systemic_review_findings.md` is mapped to the phase(s) that close it. Findings marked "no action" are explicitly justified. No finding is left unmapped.

| Finding | Severity | Phase(s) | Closure mechanism |
|---|---|---|---|
| Qual #1 — Roadmap frames system as needing construction | CRITICAL | 1 + 6 | `IMPLEMENTATION_SPEC` replaces hardcoded `impl_gaps`; `MAPA:STATIC-START/END` sentinels replace verbatim roadmap copy |
| Qual #2 — Bundle sizes understated 24–78% | MODERATE | 3 | `compute_satellite_stats()` with `len(text.splitlines())` |
| Qual #3 — "320 lines skeleton tests" implies stubs | MINOR | 1 | **D1 PATCH (v1.2):** Tests already load real data via `bp.load_all_jsons()` — 7 matches across both test files. Qual #3's premise was wrong. Task 1-1 (extract `reference_cases.py`) closes the only real DRY issue. |
| Qual #4 — Doc-specified function signatures missing | MINOR | 1 | **D3 PATCH (v1.2):** `format_allocations`, `expand_category_wildcards`, `run_pipeline` do NOT exist anywhere in `build_pipeline.py` (verified by `rg` returning 0 matches). Use `missing` strategy, NOT `inline_in`. The source review misread inline list-comprehension code at L2839-2853 (inside `build_output_contract`, not `solve_cascade`). |
| F #1 — impl_gaps table falsely claims 5 items NOT IMPLEMENTED | CRITICAL | 1 | `IMPLEMENTATION_SPEC` + `ImplIntrospector.check()` |
| F #2 — Duplicate `fat_sources` row in curation table | MINOR | 6 | Code bug at `build_pipeline.py:1086-1122` — fix double-add in section generator |
| F #3 — INGREDIENTE_TEMPLATE_SPEC.md nutrient stats stale (off by 1–2) | MINOR | 2 | Stats regenerated from live DB count via `STRUCTURE_CONTRACTS` |
| F #4 — REF token count corrected to 50 | MINOR | 1 | Already correct after re-verification; closed by Phase 1 audit |
| F #5 — Diet template components are strings | RETRACTED | — | No action; v1 script bug, spec already correct |
| F #6 — Nutrient matrix is list, not dict | MINOR | 2 | Acknowledged divergence — encoded in `STRUCTURE_CONTRACTS` |
| F #7 — 41 vs 43 nutrients | NOT A BUG | — | Document only — 43 vs 41 via `coverage_excluded_nutrients` (vitamin_k_ug, biotin_ug) |
| F #8 — All 8 SUL values match | MATCH | — | No action; already correct |
| F #9 — MAPA L78 says "41 nutrients", L359 says "43" | MINOR | 2 | Internal MAPA inconsistency — fix L78 to match L359 (DB-space = 43, solver-space = 41) |
| F #10 — Satellite line counts understated | MINOR | 3 | `compute_satellite_stats()` |
| F #11 — `beef_muscle_raw` display name missing parenthetical | MINOR | 1 | Display name extracted from live DB during table generation |
| F #12 — File sizes all match (v1 misreport corrected) | CORRECTION | — | No action; MAPA already correct |
| F #13 — `has_sul` field absent in NUTRIENT_REGISTRY | MINOR | 2 | `has_sul` absence encoded as `STRUCTURE_CONTRACTS` entry |
| F #14 — `quality_flag` vs `status` in provenance | MINOR | 2 | Field name encoded as `STRUCTURE_CONTRACTS` entry |
| F #15 — `constraints.json` is dict of 4 sub-arrays | MINOR | 2 | Structure encoded as `STRUCTURE_CONTRACTS` entry |
| F #16 — `scenarios.json` is top-level list | MINOR | 2 | Structure encoded as `STRUCTURE_CONTRACTS` entry |
| F #17 — Tests use fixtures not real JSONs | **INFO (D1 v1.2)** | 1 | **D1 PATCH:** FALSE POSITIVE — tests use `bp.load_all_jsons()` (the production loader). Verified by `rg -c "load_all_jsons" tests/` → 7 matches. Reclassified CRITICAL → INFO. Task 5-1 (rewrite tests) DELETED. Task 1-1 (reference_cases.py extraction) closes the only real (DRY) issue. Check 9 (Task 5-2) rewritten per D6 to detect `load_all_jsons` calls, not `json.load` literals. |
| F #18 — `validate_output()` epsilon bug | MINOR | 0a + 0b + 0c | **D2 PATCH (v1.2):** Gap is 0.05g (rounding from L2857 `round(grams, 1)`), NOT 1e-9 g (float). Phase 0a designs fix (Option A: validate unrounded `total_g`; Option B: explicit N×0.05g tolerance). Phase 0b implements. Phase 0c (NEW) audits rounding policy at L2857. |
| F #19 — `sat_pipeline_codigo` 514% off (CLAIM IS BOGUS) | BOGUS | 3 | **Finding #19 conflates `sat_pipeline_codigo.md` (1001 lines per #10) with `build_pipeline.py` (3458 lines, which the verification command actually measured).** Real discrepancy for `sat_pipeline_codigo.md` is 78% (563 vs 1001), already covered by Finding #10. Closed by `compute_satellite_stats()`. |
| F #26 (NEW, v1.1 audit) — `lp_parameters.schema.json` actual GitHub size = 44294 bytes (Finding #12 claims 45356) | MINOR | 2 | Update `STRUCTURE_CONTRACTS` to verify against actual GitHub size, not findings doc claim |
| F #27 (NEW, v1.1 audit) — `upload/` JSONs diverge from GitHub `data/` JSONs (8/11 files differ by 116–8028 bytes) | MINOR | 2 | All structural contracts must be re-verified against GitHub canonical at execution time; PR #8 may have partially fixed some findings |
| F #28 (NEW, v1.1 audit) — `section1_header()` heuristic at L427 NEVER FIRES (no `## 3.` heading in `indice_plano_central.md`) | MINOR | 6 | Sentinel placement is still the correct fix, but description of the disease is "never stops copying" not "stops too early" |
| F #20 — `run_pipeline()` and `run_build_recipes()` missing as standalone | MINOR | 1 | **D3 PATCH (v1.2):** `run_pipeline` does NOT exist anywhere — reclassify `inline_in` → `missing`. `--build-recipes` → `cli_stub` (unchanged). |
| F #21 — Clinical floor MILP IS implemented | CONFIRMED | 1 | `IMPLEMENTATION_SPEC` entry "Clinical floor (x_min_i MILP)" → IMPLEMENTED |
| F #22 — DerEnvelope dual contract IS implemented | CONFIRMED | 1 | `IMPLEMENTATION_SPEC` entry "Dynamic envelope (DerEnvelope)" → IMPLEMENTED |
| F #23 — Conditional adequacy check IS implemented | CONFIRMED | 1 | `IMPLEMENTATION_SPEC` entry "Conditional adequacy check" → IMPLEMENTED |
| F #24 — Kelp/salt/copper sulfate STILL PLANNED | CONFIRMED | 1 | `IMPLEMENTATION_SPEC` entry "recipes_precomputed.json" → `file_exists` → NOT IMPLEMENTED |
| F #25 — 32 tests pass but use fixtures | **INFO (D1 v1.2)** | 1 | **D1 PATCH:** Premise incorrect — tests already load real data via `bp.load_all_jsons()`. Closed by Task 1-1 (reference_cases.py extraction only). No test rewrite required. |

---

## Section 2 — Preconditions (P0–P7)

All preconditions must hold before any task in Phase 0b or later executes. P5, P6, P7 are produced by earlier tasks in this plan (transitive closure).

**P0 — Repository state**
- Working directory: `C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\`
- Git status: clean working tree, current branch `main`
- Verify: `git status --porcelain` returns empty

**P1 — Python environment**
- Python 3.11+ (matches `build_pipeline.py` docstring)
- Dependencies installed: `pulp`, `jsonschema`, `pytest`
- Verify: `python -c "import pulp, jsonschema, pytest; print('ok')"` exits 0

**P2 — Source files present with SHA-256 recorded**
- `build_pipeline.py` exists, 3458 ±1 lines (verified against GitHub canonical)
- 11 JSON files in `data/` exist. **NOTE:** GitHub-canonical sizes differ from Finding #12's claims for `lp_parameters.schema.json` (actual 44294 vs claimed 45356) and `db_ingredientes.schema.json` (actual 8135 vs claimed 8312). Do NOT treat Finding #12's size table as ground truth — record actual sizes in `docs/pre-flight-sha256.txt` at execution time.
- 8 satellite `.md` files exist in their canonical subfolders: 6 in `docs/architecture/` (`indice_plano_central.md`, `sat_princípios.md`, `sat_dados_schema.md`, `sat_pipeline_fluxo.md`, `sat_pipeline_codigo.md`, `sat_solver_contrato.md`) and 2 in `docs/governance/` (`sat_testes_consolidado.md`, `sat_operacional.md`). Line counts per Finding #10 (all verified: 160/378/269/1001/739/65/222/290).
- Record SHA-256 of each in `docs/pre-flight-sha256.txt` before starting

**P3 — Backup of original MAPA**
- Copy: `copy MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md.orig-bak`
- Verify: `Test-Path MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md.orig-bak` returns True

**P4 — Test baseline green**
- `pytest tests/ -v` returns 32 passed, 0 failed (matches Finding #25)
- If any test fails before starting: ABORT. Phase 5 may discover additional failures, but the baseline must be green.

**P5 — Phase 0a prerequisite satisfied**
- `docs/phase0a-tolerance-design.md` exists (produced by Task 0a-1)
- `docs/phase0a-callsite-audit.md` exists (produced by Task 0a-2)
- Both documents referenced from the `validate_output()` fix in Task 0b-1

**P6 — Reference case extraction complete**
- `tests/reference_cases.py` exists, exports `REFERENCE_ANIMAL: dict`, `REFERENCE_SELECTION: list[str]`, `REFERENCE_SCENARIO_ID: str`
- Used by both `tests/test_cascade_integration.py` and `doc_introspector.py` (single source of truth)

**P7 — Volatile content scrubber available**
- `doc_introspector.py` defines `scrub_volatile(content: str) -> str` that strips:
  - Windows absolute paths matching `r"[A-Z]:\\[^\s\n]+"` → `<repo>/`
  - Linux absolute paths matching `r"/home/[^\s\n]+"` → `<repo>/`
  - Timestamps matching `r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"` → `<timestamp>`
  - PIDs matching `r"PID:\s*\d+"` → `PID: <pid>`
  - Memory addresses matching `r"0x[0-9a-fA-F]+"` → `0x<addr>`

---

## Section 3 — Task Graph (DAG)

The dependency graph is mandatory. Tasks may parallelize only where `depends_on` lists are empty or independent. The maximum concurrent task count is 2.

```
Phase 0-zero ── Task 0-zero (pre-flight sanity check: confirm 0.05g gap from F#18) ──► P_zero
                                                          │
Phase 0a ──┬── Task 0a-1 (rounding-fix design: Option A/B)   ─┐
           ├── Task 0a-2 (call-site audit: validate_output + round at L2857) │  (parallel)
           └── Task 0c-1 (rounding policy audit at L2857 — NEW per D5)         │
                                                                              ▼
Phase 0b ──── Task 0b-1 (apply rounding-site fix per Option A or B) ──► P5
                                                          │
Phase 1  ──┬── Task 1-1 (extract reference_cases.py) ──► P6
           ├── Task 1-2 (define IMPLEMENTATION_SPEC — `missing` strategy for the 3 D3 functions)   ─┐
           └── Task 1-3 (write ImplIntrospector — inspect main() structure FIRST per D7)           │
                                                                                                    ▼  (1-3 depends on 1-2)
                                                                                        Task 1-4 (wire into generate_mapa)
                                                                                                    │
Phase 4  ──┬── Task 4-1 (capture_live_evidence — EXPANDED per D9 with LP-specific signals)         ─┐
           ├── Task 4-2 (scrub_volatile)  [depends on 1-1, parallel with 4-1]                     │
           └── Task 4-3 (embed in MAPA)  [depends on 4-1, 4-2]                                     │
                                                                                                    ▼
Phase 3  ──── Task 3-1 (compute_satellite_stats) ──► Phase 3 done
                                                          │
Phase 2  ──── Task 2-1 (STRUCTURE_CONTRACTS via JSON Schema — includes D8 NUTRIENT_REGISTRY safety_hard=8 contract) ──► Phase 2 done
                                                          │
Phase 5  ──── Task 5-2 (check_test_integrity with D6 regex + Check 9)  [depends on 1-1 only; Task 5-1 DELETED per D1]
                                                          │
Phase 6  ──┬── Task 6-1 (add sentinels to indice_plano_central.md)
           ├── Task 6-2 (rewrite section1_header)  [depends on 6-1, 3-1]
           └── Task 6-3 (add Checks 9–13)          [depends on 5-2, 6-2]

Final    ──── Task F-1 (regenerate, run gate, certify)
```

**D1 v1.2 CHANGE:** Task 5-1 ("rewrite tests to AAA+A") is DELETED — tests already use `bp.load_all_jsons()`. Task 5-2 now depends only on Task 1-1 (the `reference_cases.py` extraction). This removes 1–2 days of wasted work rewriting 32 working tests.

**D2 v1.2 CHANGE:** Phase 0a-1 redesigns the fix (Option A: validate unrounded `total_g`; Option B: explicit N×0.05g tolerance), instead of a generic `math.isclose()` that would mask real drift.

**D5 v1.2 NEW:** Phase 0c-1 audits the rounding policy at L2857 — a sibling to Phase 0a/0b that runs in parallel.

**D7 v1.2 CHANGE:** Task 1-3 must inspect `main()` structure (argparse/click/if-elif/dispatch) before walking AST for CLI modes.

**D8 v1.2 NEW:** Phase 2-1 adds a `STRUCTURE_CONTRACT` for `NUTRIENT_REGISTRY` having exactly 8 `safety_hard` entries, each with `sul_value`.

**D9 v1.2 CHANGE:** Task 4-1 evidence capture is expanded to include LP-specific signals (solver status, lexicographic stages solved, clinical floor relaxation, SUL profile, solve time).

---

## Section 4 — Phases (atomic tasks)

Each task is atomic: it produces a verifiable artifact, has explicit acceptance criteria, lists verification commands, and a rollback procedure. The executing agent must run the verification commands after every task — do not batch.

### Phase 0-zero — Pre-flight sanity check (NEW per D2 v1.2)

#### Task 0-zero — Confirm the F#18 envelope gap is 0.05g (rounding), not 1e-9 g (float)

- **task_id**: `0-zero`
- **depends_on**: (none)
- **files_touched**: `docs/phase0-preflight-sanity.md` (new)
- **description**: **THIS TASK IS MANDATORY BEFORE ANY OTHER TASK.** Per the specialist review (D2), the plan v1.1.0 misdiagnosed the F#18 envelope bug as float precision (1e-9 g) when it is actually rounding error (0.05g) from `round(grams, 1)` at `build_pipeline.py:2857`. Before designing any fix, the executing agent MUST verify this empirically. The task: (1) run `python build_pipeline.py --runtime --selection beef_muscle_raw,chicken_heart_raw,beef_liver_raw,beef_kidney_raw,salmon_atlantic_raw` and capture the exact `AssertionError` message; (2) extract the `total_g`, `env["min_total_g"]`, and `env["max_total_g"]` values from the traceback; (3) compute the gap `= min_total_g - total_g` and document it; (4) confirm the gap is in the range `[0.01, 0.5]` (rounding-scale) and NOT in the range `[1e-12, 1e-6]` (float-scale); (5) if the gap is float-scale, STOP — the bug is different from what the specialist review found, and Phase 0a must be redesigned; (6) if the gap is rounding-scale, document it as `gap_g = <value>` and proceed. Write the conclusion to `docs/phase0-preflight-sanity.md`. This is the empirical anchor for every subsequent tolerance decision.
- **acceptance_criteria**:
  - `docs/phase0-preflight-sanity.md` exists
  - Document records the exact `total_g`, `min_total_g`, `max_total_g` from the live run
  - Document records `gap_g = min_total_g - total_g` and classifies it as either "rounding-scale" (0.01–0.5g) or "float-scale" (<1e-6 g)
  - Conclusion explicitly states whether to proceed with Option A / Option B (rounding-scale) or escalate to redesign (float-scale)
- **verification**:
  - `Test-Path docs/phase0-preflight-sanity.md` returns True
  - `rg "gap_g\s*=" docs/phase0-preflight-sanity.md` returns a match with a numeric value
  - `rg "rounding-scale|float-scale" docs/phase0-preflight-sanity.md` returns exactly one match
- **rollback**: delete the file

### Phase 0a — Rounding-fix design + call-site audit (BLOCKING)

#### Task 0a-1 — Rounding-fix design document (D2 v1.2 REWRITE)

- **task_id**: `0a-1`
- **depends_on**: `[0-zero]`
- **files_touched**: `docs/phase0a-tolerance-design.md` (new)
- **description**: **D2 PATCH (v1.2):** Produce a 1-page design document justifying the fix strategy for the F#18 envelope-validation bug. The plan v1.1.0 proposed `math.isclose()` with `rel_tol=1e-6, floor=1e-9` — this is WRONG because the gap is 0.05g (rounding from `round(grams, 1)` at L2857), which is ~70× larger than the proposed tolerance. The fix must accommodate the rounding-scale gap, NOT the float-scale gap. The document must cover: (a) the empirical gap value from Task 0-zero; (b) the root cause — `build_output_contract()` at L2857 rounds each `grams_per_day` to 1 decimal, then `validate_output()` at L3061 sums the ROUNDED values but compares against `env["min_total_g"]` which retains full float precision; (c) two fix options: **Option A (PREFERRED — fix at rounding site):** retain unrounded `total_g` from `sum(x_vals.values())` before rounding, expose it as `result["_unrounded_total_g"]` (private field), and have `validate_output()` prefer that field over `sum(a["grams_per_day"] for a in result["allocations"])`; **Option B (FALLBACK — explicit rounding tolerance):** add `rounding_tolerance = len(result["allocations"]) * 0.05 + 1e-9` to the comparison — mathematically honest (we round to 0.1g, so we tolerate up to N×0.05g cumulative error); (d) why **Option C (generic `math.isclose()`)** is FORBIDDEN — it would mask real envelope violations up to the tolerance threshold, which is the R8 trap; (e) the chosen option with rationale; (f) biological relevance: for the reference animal, a 0.05g rounding error on total food is biologically negligible (<0.01% of daily intake), but for individual trace nutrients (selenium, iodine) at SUL boundaries, the rounding on `pct_of_total` at L2858 compounds — this is what Phase 0c-1 audits.
- **acceptance_criteria**:
  - Document exists at the specified path
  - Contains both Option A and Option B code blocks
  - Explicitly marks Option C as FORBIDDEN with rationale
  - Cites the empirical `gap_g` value from Task 0-zero
  - Concludes with explicit recommendation (Option A preferred) and rationale
- **verification**:
  - `Test-Path docs/phase0a-tolerance-design.md` returns True
  - `rg "Option A" docs/phase0a-tolerance-design.md` returns matches
  - `rg "FORBIDDEN" docs/phase0a-tolerance-design.md` returns matches
- **rollback**: delete the file

#### Task 0a-2 — Call-site audit of `validate_output()` AND `round(grams, 1)` at L2857 (D2 v1.2 EXPANDED)

- **task_id**: `0a-2`
- **depends_on**: `[0-zero]` (parallel with 0a-1, 0c-1)
- **files_touched**: `docs/phase0a-callsite-audit.md` (new)
- **description**: **D2 PATCH (v1.2):** Audit ALL call sites of both `validate_output()` AND the rounding call `round(grams, 1)` at L2857. For each `validate_output()` caller, document: (a) file:line; (b) whether the boolean return value is consumed; (c) whether the caller branches on the result; (d) risk assessment for Option A (does adding `_unrounded_total_g` to the result dict break any caller that destructures the result?). For each `round(grams, 1)` site, document: (a) file:line; (b) which field is rounded; (c) whether the rounded value is used downstream (in `solver_output.json`, in `validate_output`, in MAPA evidence); (d) whether rounding to 0.1g is the right precision (vs 0.01g or 0.001g) for clinical use. The audit must conclude with either "safe to apply Option A" (LOW risk for all callers) or "must use Option B" (MEDIUM/HIGH risk for at least one caller) with rationale. This audit is the safety gate for Task 0b-1; do not skip.
- **acceptance_criteria**:
  - Document lists all callers of `validate_output()` (expected: 1–3 sites)
  - Document lists all `round(..., 1)` call sites in `build_output_contract()` and downstream
  - Each entry has `file:line` + risk classification (LOW/MEDIUM/HIGH)
  - Conclusion section explicitly states "apply Option A" or "apply Option B" with rationale
- **verification**:
  - `rg "validate_output\(\)" --type py -n` output matches entries in the audit doc
  - `rg "round\(.*?,\s*1\)" build_pipeline.py -n` output matches entries in the audit doc
- **rollback**: delete the file

### Phase 0b — Apply rounding-site fix

#### Task 0b-1 — Implement Option A (or B) per Phase 0a (D2 v1.2 REWRITE)

- **task_id**: `0b-1`
- **depends_on**: `[0a-1, 0a-2]`
- **files_touched**: `build_pipeline.py` (modify L2857 region in `build_output_contract` AND L3061-3063 region in `validate_output`)
- **description**: **D2 PATCH (v1.2):** Apply the fix chosen in Task 0a-2 (Option A preferred, Option B fallback). Do NOT use generic `math.isclose()` — it would mask real drift (R8 trap). **If Option A:** in `build_output_contract()` at L2857, compute `raw_total_g = sum(x_vals.values())` BEFORE the rounding loop, store it as `result["_unrounded_total_g"] = raw_total_g`; in `validate_output()` at L3061, replace `total_g = sum(a["grams_per_day"] for a in result["allocations"])` with `total_g = result.get("_unrounded_total_g") or sum(a["grams_per_day"] for a in result["allocations"])`. The `or` fallback preserves backward compatibility with results built without the unrounded field. **If Option B:** in `validate_output()` at L3063, replace `assert env["min_total_g"] <= total_g <= env["max_total_g"]` with `n_allocs = len(result["allocations"]); rounding_tol = n_allocs * 0.05 + 1e-9; assert env["min_total_g"] - rounding_tol <= total_g <= env["max_total_g"] + rounding_tol`. Add a comment block referencing `docs/phase0a-tolerance-design.md` for justification. Add a regression test in `tests/test_cascade_integration.py` (or a new `tests/test_validate_output_rounding.py`) that specifically constructs a case where `sum(round(x_i, 1))` is `N*0.05g` below `min_total_g` but `sum(x_i)` is within bounds — the test must PASS after the fix and FAIL before. If Task 0a-2 concluded "must use Option B", also add a `--strict-envelope` CLI flag that reverts to strict comparison when set (for clinical audits).
- **acceptance_criteria**:
  - `python -c "from build_pipeline import validate_output; print('import ok')"` exits 0
  - The 5-ingredient reference case from Finding #18 no longer raises `AssertionError`
  - New regression test (`test_validate_output_rounding.*`) passes
  - Existing 32 tests still pass
  - If Option A: `solver_output.json` contains the `_unrounded_total_g` field for downstream audit
- **verification**:
  - `python build_pipeline.py --runtime --selection beef_muscle_raw,chicken_heart_raw,beef_liver_raw,beef_kidney_raw,salmon_atlantic_raw` exits 0 (not 1)
  - `pytest tests/ -v` returns 32+ passed, 0 failed
- **rollback**: `git checkout build_pipeline.py`

### Phase 0c — Rounding policy audit (NEW per D5 v1.2)

#### Task 0c-1 — Audit all rounding sites and document the rounding policy

- **task_id**: `0c-1`
- **depends_on**: `[0-zero]` (parallel with 0a-1, 0a-2)
- **files_touched**: `docs/phase0c-rounding-policy.md` (new)
- **description**: **D5 PATCH (v1.2):** Phase 0a/0b fixes the `validate_output()` envelope bug, but the broader rounding policy at L2857 has clinical-safety implications the F#18 fix alone doesn't address. The rounded allocations are what get written to `solver_output.json` and displayed to the user — if the LP solved for `708.85g` but the user feeds `708.8g`, the dog gets 0.05g less food than intended. For total food, 0.05g is biologically negligible. But for trace nutrients (selenium, iodine) at SUL boundaries, 0.05g of the wrong ingredient could matter. Audit: (1) enumerate every `round(..., N)` call site in `build_pipeline.py`; (2) for each, document: file:line, field name, current precision (N), downstream consumers (JSON output? validator? MAPA evidence? UI?); (3) flag any inconsistency (e.g. `grams_per_day` rounded to 0.1g but `pct_of_total` computed FROM the rounded grams — this compounds error); (4) recommend a unified rounding policy (e.g. "round only at the presentation layer, never at the computation layer"); (5) flag whether `_unrounded_total_g` (from Option A) should also be exposed in `solver_output.json` for downstream audit. This is a SIBLING task to Phase 0a/0b — it does not block 0b, but its findings may trigger a follow-up plan (out of scope for this plan).
- **acceptance_criteria**:
  - Document lists every `round(..., N)` call site with file:line and field name
  - Document identifies at least 3 rounding sites (L2857 grams_per_day, L2858 pct_of_total, plus at least one more)
  - Document flags any inconsistency between rounding precisions
  - Document includes a recommended unified policy (1–2 paragraphs)
  - Document explicitly states which (if any) findings are out of scope for this plan and require a follow-up
- **verification**:
  - `Test-Path docs/phase0c-rounding-policy.md` returns True
  - `rg "round\(" docs/phase0c-rounding-policy.md | Measure-Object -Line` returns `>= 3`
- **rollback**: delete the file

### Phase 1 — Implementation-status engine (kills Findings #1, #4, #11, #20, #21, #22, #23, #24)

#### Task 1-1 — Extract `reference_cases.py`

- **task_id**: `1-1`
- **depends_on**: `[0b-1]`
- **files_touched**: `tests/reference_cases.py` (new), `tests/test_cascade_integration.py` (modify imports)
- **description**: Identify the inline reference animal and reference selection currently embedded in `tests/test_cascade_integration.py`. Extract them to a new module `tests/reference_cases.py` exporting three names: `REFERENCE_ANIMAL: dict` (animal input — BW, age, activity, etc.), `REFERENCE_SELECTION: list[str]` (the 5-ingredient selection from Finding #18), `REFERENCE_SCENARIO_ID: str`. The existing tests must continue to pass after the extraction — verify by re-running pytest. This module becomes the single source of truth for reference data shared between tests and `doc_introspector.py`'s live evidence capture (Phase 4). Avoid the temptation to define a third copy in `doc_reference.json` — that re-introduces the drift disease this plan is curing.
- **acceptance_criteria**:
  - `tests/reference_cases.py` exists and exports the three names
  - `python -c "from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION; print(len(REFERENCE_SELECTION))"` prints 5
  - All 32 tests still pass
- **verification**: `pytest tests/ -v` returns 32 passed, 0 failed
- **rollback**: `git checkout tests/test_cascade_integration.py` and delete `tests/reference_cases.py`

#### Task 1-2 — Define `IMPLEMENTATION_SPEC`

- **task_id**: `1-2`
- **depends_on**: `[1-1]`
- **files_touched**: `doc_introspector.py` (new file, top of file)
- **description**: Define `IMPLEMENTATION_SPEC` as a list of `ImplCheck` dataclasses. Each entry must include: `name` (display name for MAPA table), `strategy` (one of: `toplevel_func`, `class_exists`, `missing`, `cli_stub`, `cli_stub_absent`, `file_exists`), `target` (function/class name, CLI mode string, or filename), `parent` (optional — kept for backward compatibility, no longer used by the `missing` strategy), `priority` (P0/P1/P2), `spec_ref` (citation to satellite `.md`, e.g. `sat_solver_contrato:§8`). **D3 PATCH (v1.2):** The `inline_in` strategy has been REMOVED — the three functions it was meant to classify (`format_allocations`, `expand_category_wildcards`, `run_pipeline`) do NOT exist anywhere in `build_pipeline.py` (verified by `rg "def format_allocations|def expand_category_wildcards|def run_pipeline" build_pipeline.py` returning 0 matches). Use the new `missing` strategy for these entries. The initial spec must cover at minimum the 10 entries below — these correspond directly to the rows in Findings #1, #4, #20, #21, #22, #23, #24:
  1. `call_lp_solver` (toplevel_func, P0, spec_ref `sat_solver_contrato:§8`)
  2. `DerEnvelope` (class_exists, P0, spec_ref `sat_princípios:§3.3`)
  3. `build_diagnostic_analysis` (toplevel_func, P0, spec_ref `sat_solver_contrato:§7.2`) — Level 3 diagnostic
  4. `build_lp_problem` (toplevel_func, P0, spec_ref `sat_solver_contrato:§8.1`) — clinical floor MILP
  5. `--runtime` mode (cli_stub_absent, P0, spec_ref `sat_pipeline_codigo:§6.4`)
  6. `--build-recipes` mode (cli_stub, P1, spec_ref `sat_pipeline_fluxo:§6.3`)
  7. `recipes_precomputed.json` (file_exists, P1, spec_ref `sat_pipeline_fluxo:§5.2`)
  8. `format_allocations` (**missing**, P2, spec_ref `sat_pipeline_codigo:§6.4a`) — D3 v1.2: function does NOT exist; the source review misread inline list-comprehension code at L2839-2853 (which lives inside `build_output_contract`, not `solve_cascade`). The `missing` strategy returns status `MISSING` with note `"not found in module AST"`.
  9. `expand_category_wildcards` (**missing**, P2, spec_ref `sat_pipeline_codigo:§6.4a`) — D3 v1.2: same as above
  10. `run_pipeline` (**missing**, P2, spec_ref `sat_pipeline_codigo:§6.4`) — D3 v1.2: function does NOT exist; was previously classified `toplevel_func` with "expected NOT IMPLEMENTED". The `missing` strategy correctly reports this as MISSING (function never implemented), distinct from `cli_stub_absent` (function exists but body says "not implemented")
- **acceptance_criteria**:
  - `doc_introspector.py` exists, imports cleanly
  - `python -c "from doc_introspector import IMPLEMENTATION_SPEC; print(len(IMPLEMENTATION_SPEC))"` prints `>= 10`
  - Each entry has all 6 fields populated (no `None` for required fields)
- **verification**: `python -c "from doc_introspector import IMPLEMENTATION_SPEC; [print(e) for e in IMPLEMENTATION_SPEC]"`
- **rollback**: delete `doc_introspector.py`

#### Task 1-3 — Implement `ImplIntrospector`

- **task_id**: `1-3`
- **depends_on**: `[1-2]`
- **files_touched**: `doc_introspector.py` (append `ImplIntrospector` class)
- **description**: Implement the `ImplIntrospector` class with: `__init__(source_path: Path)` that parses the AST of `build_pipeline.py`; `toplevel_funcs: dict[str, ast.FunctionDef]` populated by walking the AST; `toplevel_classes: dict[str, ast.ClassDef]` similarly; `check(spec: ImplCheck, base_dir: Path, cli_stub_strings: dict) -> dict` that dispatches by strategy and returns `{name, priority, spec_ref, status, line, note}`. **D3 v1.2 NEW STRATEGY:** add a `missing` strategy that searches the entire module AST for any `FunctionDef` matching `spec.target`; if not found, returns `{status: "MISSING", line: None, note: "not found in module AST"}`. This is distinct from `toplevel_func` (which also returns MISSING if not found, but at the top level only) and `cli_stub_absent` (function exists but body says "not implemented"). **D7 v1.2 NEW SUB-STEP (BEFORE implementing `extract_cli_modes`):** inspect `main()` structure first. The plan v1.1.0 assumed `main()` uses an `if mode == "--X": ... elif mode == "--Y":` chain — but many CLI parsers use `argparse` (subparsers), `click`, or dict dispatch (`HANDLERS = {"--runtime": run_runtime, ...}`). Run `rg -n "def main\(" build_pipeline.py` then read the first 50 lines of `main()` to determine the dispatch style. If it uses argparse/click/dispatch, adapt `extract_cli_modes() -> set[str]` to walk that structure (e.g. for argparse, walk `add_parser("--X")` calls; for dict dispatch, walk the dict literal). If it uses if/elif, walk `elif mode == "--X":` branches as before. Add a comment block in `extract_cli_modes` documenting which style was detected. Also implement: `is_stub(mode: str) -> bool` that returns True if the branch's print string contains "not implemented" (case-insensitive); `detect_spec_drift(spec: list[ImplCheck]) -> list[str]` that performs the inverse check (Critical Gap 2): CLI modes in `main()` not present in `IMPLEMENTATION_SPEC` are drift; `cli_stub` entries whose branch no longer says "not implemented" are drift (they should flip to `cli_stub_absent`). The drift detector is what prevents the spec itself from becoming the next stale-doc bug.
- **acceptance_criteria**:
  - `python -c "from doc_introspector import ImplIntrospector; ii = ImplIntrospector(__import__('pathlib').Path('build_pipeline.py')); print(len(ii.toplevel_funcs))"` prints `> 30`
  - `python -c "from doc_introspector import ImplIntrospector; from pathlib import Path; ii = ImplIntrospector(Path('build_pipeline.py')); print(sorted(ii.extract_cli_modes()))"` includes `--runtime`, `--generate-mapa`, `--build-recipes`, `--validate-db`
- **verification**:
  - `python -c "from doc_introspector import ImplIntrospector, IMPLEMENTATION_SPEC; from pathlib import Path; ii = ImplIntrospector(Path('build_pipeline.py')); print([ii.check(s, Path('.'), {}) for s in IMPLEMENTATION_SPEC[:3]])"`
- **rollback**: `git checkout doc_introspector.py`

#### Task 1-4 — Wire `ImplIntrospector` into `generate_mapa()`

- **task_id**: `1-4`
- **depends_on**: `[1-3]`
- **files_touched**: `build_pipeline.py` (modify L1194-1207 region)
- **description**: Replace the hardcoded `impl_gaps` list at L1194-1201 with a loop over `IMPLEMENTATION_SPEC`. For each entry, call `ImplIntrospector.check()` and render the result into the MAPA table. The new table must include columns: Name, Priority, Spec Ref, Status, Line, Note. After each row, add an HTML provenance comment: `<!-- SOURCE: IMPLEMENTATION_SPEC[i] / build_pipeline.py:L{line} -->`. The provenance markers are invisible in rendered markdown but trivially grep-able for audit. This single change closes Finding #1 (5 false NOT IMPLEMENTED claims), Findings #21/#22/#23 (correctly classified as IMPLEMENTED), Finding #24 (correctly classified as NOT IMPLEMENTED via `file_exists`), Finding #20 (correctly classifies `run_pipeline`, `format_allocations`, `expand_category_wildcards` as MISSING via the new `missing` strategy — D3 v1.2), Finding #11 (display name pulled live from DB).
- **acceptance_criteria**:
  - `python build_pipeline.py --generate-mapa --out test-mapa.md` succeeds
  - The generated MAPA's "Implementation Gaps" section shows `call_lp_solver` as `IMPLEMENTED` (not `NOT IMPLEMENTED`)
  - The generated MAPA contains `<!-- SOURCE: IMPLEMENTATION_SPEC` at least 10 times
  - The generated MAPA shows `run_pipeline` as `MISSING` (D3 v1.2: function never implemented, not just "inline in main()")
  - The generated MAPA shows `format_allocations` and `expand_category_wildcards` as `MISSING` (D3 v1.2: functions do not exist anywhere in `build_pipeline.py`)
- **verification**:
  - `python build_pipeline.py --generate-mapa --out test-mapa.md`
  - `rg "IMPLEMENTED" test-mapa.md | Select-String "call_lp_solver"` returns matches
  - `rg "SOURCE: IMPLEMENTATION_SPEC" test-mapa.md | Measure-Object -Line` returns `>= 10`
- **rollback**: `git checkout build_pipeline.py`

### Phase 4 — Live execution evidence (the fix the prior proposal missed — Root Cause #4)

#### Task 4-1 — Implement `capture_live_evidence()`

- **task_id**: `4-1`
- **depends_on**: `[1-4]`
- **files_touched**: `doc_introspector.py` (append `capture_live_evidence` function)
- **description**: Implement the function with signature `capture_live_evidence(data: dict, reference_animal: dict, reference_selection: list[str]) -> list[dict]`. Each evidence entry has fields: `label`, `status` (OK/FAILED/DEGRADED), `severity` (HARD/SOFT), `output`, `result_repr`, `error` (if FAILED), and **D9 v1.2 NEW LP-SPECIFIC FIELDS** (for entries that invoke the LP solver): `solver_status` (optimal/suboptimal/infeasible/unbounded from `solver_output["solver_status"]`), `cascade_level_used` (1/2/3 from `solver_output["cascade_level_used"]`), `lexicographic_stages_solved` (list from `solver_output["solver_metadata"]["lexicographic_stages_used"]`), `clinical_floor_relaxed` (bool from `solver_output["solver_metadata"]["clinical_floor_relaxed"]`), `solve_time_ms` (int from `solver_output["solver_metadata"]["solve_time_ms"]`), `nutrients_above_90pct_sul` (list of nutrient IDs where `nr.get("pct_of_sul") is not None and nr["pct_of_sul"] > 0.9`). Capture four smoke runs: (1) `calculate_der_and_envelope(REFERENCE_ANIMAL, ...)` — HARD severity; (2) `--runtime` smoke on `REFERENCE_SELECTION` — HARD severity (this is the end-to-end pipeline; **D9 v1.2:** MUST populate all LP-specific fields for this entry); (3) `check_fat_source_adequacy(...)` with no fat_source — SOFT severity; **D9 v1.2 NEW (4):** `solver_status_diagnostic` — if the runtime smoke returned `suboptimal` or `infeasible`, capture a diagnostic entry that records which constraint(s) caused the cascade to fall back. Use `io.StringIO` + `contextlib.redirect_stdout` to capture stdout. Use `json.dumps(result, indent=2, default=str, sort_keys=True)[:2000]` for `result_repr` — NOT `repr(result)[:500]`, which is too lossy for LP solutions containing ~30 nutrient allocations. If the JSON truncates, append `"... (N more keys)"` so the auditor knows the evidence is partial. Pin all evidence to `DB_ingredientes.json` only — do NOT call the USDA API during evidence capture, because API responses are volatile and would corrupt idempotency. **D9 v1.2 RATIONALE:** the plan v1.1.0 captured the *plumbing* (does it run?) but not the *LP health* (does it solve correctly?). For a MAPA that documents an LP solver pipeline, the missing signals are the single most diagnostic information an auditor could want — a `suboptimal` solver status with only `stage1` solved means the cascade is silently degrading; a `clinical_floor_relaxed=True` means the LP had to relax safety constraints to find any feasible solution; a `solve_time_ms > 30000` means the solver hit `cbc_time_limit_seconds=30` and returned whatever it had. Without these signals in the MAPA evidence, the document is dishonest about pipeline health.
- **acceptance_criteria**:
  - `python -c "from doc_introspector import capture_live_evidence"` runs without raising
  - Output is a list of 4 dicts (D9 v1.2: was 3, added solver_status_diagnostic), each with all required fields populated
  - At least one entry has `status=OK` (the DER calculation must succeed after Phase 0b's rounding fix)
  - **D9 v1.2 NEW:** the runtime-smoke entry has all six LP-specific fields populated (`solver_status`, `cascade_level_used`, `lexicographic_stages_solved`, `clinical_floor_relaxed`, `solve_time_ms`, `nutrients_above_90pct_sul`)
  - `result_repr` for the DER entry is valid JSON (parseable by `json.loads`)
- **verification**:
  - `python -c "import json; from doc_introspector import capture_live_evidence; from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION; print(json.dumps(capture_live_evidence({}, REFERENCE_ANIMAL, REFERENCE_SELECTION), indent=2))"`
- **rollback**: `git checkout doc_introspector.py`

#### Task 4-2 — Implement `scrub_volatile()`

- **task_id**: `4-2`
- **depends_on**: `[1-1]` (satisfies P7; can run parallel with 4-1)
- **files_touched**: `doc_introspector.py` (append `scrub_volatile`)
- **description**: Implement `scrub_volatile(content: str) -> str` that strips non-deterministic content from captured stdout before embedding in the MAPA. **D4 v1.2 TIGHTENED:** the plan v1.1.0 over-stated the non-determinism concern — the LP solver is already pinned for determinism (`pulp.PULP_CBC_CMD(msg=False, timeLimit=30, gapRel=0.01, threads=1, options=["randomSeed=12345"])` at `build_pipeline.py:2271-2276`), so CBC produces bit-identical output across runs on the same machine. The actual non-determinism sources are: (1) timestamps in stdout; (2) absolute Windows/Linux paths; (3) PIDs and memory addresses in error tracebacks. The function must apply five regex substitutions in order: Windows absolute paths (`r"[A-Z]:\\[^\s\n]+"` → `<repo>/`), Linux absolute paths (`r"/home/[^\s\n]+"` → `<repo>/`), ISO timestamps (`r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"` → `<timestamp>`), PIDs (`r"PID:\s*\d+"` → `PID: <pid>`), and memory addresses (`r"0x[0-9a-fA-F]+"` → `0x<addr>`). Cross-platform float differences (Windows vs Linux libstdc++ rounding) are usually negligible but not zero — if the idempotency test (Task F-1 step 5) fails on cross-platform runs, expand `scrub_volatile` to mask the offending floats. Without this scrubber, the idempotency test in Task F-1 will fail on every run because timestamps and absolute paths will differ between generations. This is the single most important utility for keeping `git diff` clean after MAPA regeneration.
- **acceptance_criteria**:
  - `scrub_volatile("loaded C:\\Users\\Straube\\Documents\\Hans-GSD-Raw-Calculator\\data\\DB_ingredientes.json at 2026-07-16T10:30:45")` returns a string containing `<repo>/` and `<timestamp>` but NOT the original path or timestamp
  - Applying `scrub_volatile` twice produces the same output as applying it once (idempotent)
- **verification**:
  - `python -c "from doc_introspector import scrub_volatile; s = scrub_volatile('C:\\\\Users\\\\test\\\\file.txt at 2026-07-16T10:30:45 PID: 1234'); print(s)"`
- **rollback**: `git checkout doc_introspector.py`

#### Task 4-3 — Embed evidence in MAPA

- **task_id**: `4-3`
- **depends_on**: `[4-1, 4-2]`
- **files_touched**: `build_pipeline.py` (new section generator `section18_live_evidence(data, idx) -> str`)
- **description**: Add a new section generator that calls `capture_live_evidence()`, applies `scrub_volatile()` to each entry's `output` field, and renders a fenced code block per entry with header `### Evidence: {label}` and body containing: status (OK/FAILED/DEGRADED), severity (HARD/SOFT), literal scrubbed stdout, and either the result JSON (if OK) or the error message (if FAILED). Add a `--no-live-evidence` CLI flag (Critical Gap from prior review — CI environments may not have LP solver dependencies or all data files). When the flag is set, the section is replaced with `> Live evidence skipped (--no-live-evidence)` and the gate still passes — but the section is visibly degraded so a human reviewer can spot it. Do not fail silently.
- **acceptance_criteria**:
  - Generated MAPA contains `### Evidence: calculate_der_and_envelope` section
  - Section contains the literal output of the function call (scrubbed of volatile content)
  - With `--no-live-evidence`, the section reads `> Live evidence skipped (--no-live-evidence)` and `--validate` still exits 0
- **verification**:
  - `python build_pipeline.py --generate-mapa --out test-mapa.md`
  - `rg "### Evidence:" test-mapa.md | Measure-Object -Line` returns `>= 3`
  - `python build_pipeline.py --generate-mapa --out test-mapa-noev.md --no-live-evidence`
  - `rg "Live evidence skipped" test-mapa-noev.md` returns matches
- **rollback**: `git checkout build_pipeline.py`

### Phase 3 — Satellite stats engine (kills Findings #2, #10, #19)

#### Task 3-1 — Implement `compute_satellite_stats()`

- **task_id**: `3-1`
- **depends_on**: `[1-4]` (needs the `generate_mapa` integration point)
- **files_touched**: `doc_introspector.py` (append), `build_pipeline.py` (modify `section1_header`)
- **description**: Define `SATELLITE_BUNDLES` dict mapping bundle name to list of satellite filenames. Use the actual bundle composition from `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` L209-216 (verified against canonical GitHub repo):
  ```python
  SATELLITE_BUNDLES = {
      "BUNDLE_CURADORIA":       ["indice_plano_central.md", "sat_dados_schema.md"],
      "BUNDLE_DESIGN_PIPELINE": ["indice_plano_central.md", "sat_pipeline_fluxo.md", "sat_princípios.md"],
      "BUNDLE_IMPL_PIPELINE":   ["indice_plano_central.md", "sat_pipeline_codigo.md", "sat_dados_schema.md"],
      "BUNDLE_SOLVER_DESIGN":   ["indice_plano_central.md", "sat_solver_contrato.md", "sat_princípios.md"],
      "BUNDLE_SOLVER_IMPL":     ["indice_plano_central.md", "sat_solver_contrato.md", "sat_dados_schema.md"],
      "BUNDLE_QA_SOLVER":       ["indice_plano_central.md", "sat_solver_contrato.md", "sat_testes_consolidado.md"],
      "BUNDLE_QA_DADOS":        ["indice_plano_central.md", "sat_dados_schema.md", "sat_testes_consolidado.md"],
      "BUNDLE_OPERACIONAL":     ["indice_plano_central.md", "sat_operacional.md"],
  }
  FILE_LOCATION_MAP = {
      "indice_plano_central.md":      "docs/architecture/",
      "sat_princípios.md":            "docs/architecture/",
      "sat_dados_schema.md":          "docs/architecture/",
      "sat_pipeline_fluxo.md":        "docs/architecture/",
      "sat_pipeline_codigo.md":       "docs/architecture/",
      "sat_solver_contrato.md":       "docs/architecture/",
      "sat_testes_consolidado.md":    "docs/governance/",
      "sat_operacional.md":           "docs/governance/",
  }
  ```
  Implement `compute_satellite_stats(base_dir: Path) -> dict` that: for each unique satellite filename, locates it via `FILE_LOCATION_MAP`, reads with `utf-8` encoding, counts via `len(text.splitlines())` — the exact method the reviewer used by hand, so the MAPA's number and any future auditor's number will always match; for each bundle, sums line counts of constituent files; returns a dict with keys `files: dict[str, int]` and `bundles: dict[str, int]`. Wire into `section1_header()`: replace the copied bundle-size table (currently the entire `indice_plano_central.md` file copied verbatim because the `## 3.` stop heuristic never fires — see Finding #28) with a table rendered from `compute_satellite_stats()`. Add a provenance comment per row: `<!-- SOURCE: compute_satellite_stats / {filename} -->`. This single change permanently retires Findings #2, #9, #10 as a category — the moment someone adds a line to a satellite file, the next MAPA regeneration picks it up automatically.
- **acceptance_criteria**:
  - For `sat_pipeline_codigo.md`, generated line count is **1001 ±1** (matches Finding #10 actual; Finding #19's claim of 3458 was a conflation with `build_pipeline.py`)
  - For `BUNDLE_IMPL_PIPELINE`, generated total = 290 + 1001 + 378 = **1669** (matches Finding #2 actual exactly)
  - All 8 satellite files have non-`None` line counts
  - All 8 bundle totals match Finding #2 actual values (668, 719, 1669, 1189, 1407, 1094, 733, 512)
- **verification**:
  - `python -c "from doc_introspector import compute_satellite_stats; from pathlib import Path; s = compute_satellite_stats(Path('.')); print(s['files']['sat_pipeline_codigo.md'])"` prints `1001` ±1
  - `python -c "from doc_introspector import compute_satellite_stats; from pathlib import Path; s = compute_satellite_stats(Path('.')); print(s['bundles']['BUNDLE_IMPL_PIPELINE'])"` prints `1669`
- **rollback**: `git checkout doc_introspector.py build_pipeline.py`

### Phase 2 — Live JSON structure contracts (kills Findings #3, #6, #9, #13, #14, #15, #16)

#### Task 2-1 — Define `STRUCTURE_CONTRACTS` via JSON Schema

- **task_id**: `2-1`
- **depends_on**: `[1-4]`
- **files_touched**: `doc_introspector.py` (append), possibly extend `data/db_ingredientes.schema.json` and `data/lp_parameters.schema.json`
- **description**: Define `STRUCTURE_CONTRACTS` as a list of `StructureContract` dataclasses with fields: `file`, `expected_type`, `predicate`, `description`, `default`. Cover at minimum these 8 contracts — one per finding the prior review's structure-reconnaissance table flagged: `scenarios.json` (list, non-empty, default=[]) per Finding #16; `constraints.json` (dict with exactly 4 keys: `mineral_antagonisms`, `toxicological_limits`, `inclusion_constraints`, `nutrient_bounds`; default={}) per Finding #15; `audit_provenance.json` (refs use `quality_flag` not `status`; default={}) per Finding #14; `lp_parameters_data.json` NUTRIENT_REGISTRY (no `has_sul` field; default={}) per Finding #13; `toxicological_limits.json` (list, len=8; default=[]) per Finding #8 cross-check; `objective_weights.json` (list, len=29; default=[]); `formulation_rules.json` `nutrient_matrix` (list, len=41; default={}) per Findings #6/#7; `DB_ingredientes.json` `protein_sources` (dict; default={}). **D8 v1.2 NEW (9th contract):** `lp_parameters_data.json` NUTRIENT_REGISTRY must have **exactly 8** entries with `constraint_tier == "safety_hard"`, and every such entry MUST have a `sul_value` field. This is the LP-critical contract that `solve_cascade()` and `build_lp_problem()` actually depend on — if someone adds a 9th `safety_hard` entry without a `sul_value`, the solver will KeyError at runtime. Adding this contract to Phase 2 turns it into a gate-tripped regression instead of a runtime crash. Code: `StructureContract(file="lp_parameters_data.json", expected_type=dict, predicate=lambda d: sum(1 for v in d.get("NUTRIENT_REGISTRY", {}).values() if v.get("constraint_tier") == "safety_hard") == 8 and all("sul_value" in v for v in d.get("NUTRIENT_REGISTRY", {}).values() if v.get("constraint_tier") == "safety_hard"), description="NUTRIENT_REGISTRY has exactly 8 safety_hard entries, each with sul_value", default={})`. Implement `check_structure_contracts(data: dict) -> list[dict]` returning one row per contract with `file`, `contract`, `holds` (bool). For complex structural checks, prefer extending the existing JSON Schema files (`db_ingredientes.schema.json`, `lp_parameters.schema.json`) and using `jsonschema.validate()` rather than hand-rolled lambdas — the lambdas reinvent a typed-dict validator that already exists as a standard. Fix the `STRUCTURE_CONTRACTS` triple-negative default-value hack flagged in the prior review: each contract carries its own explicit `default` field, no per-filename special-casing in the renderer.
- **acceptance_criteria**:
  - `python -c "from doc_introspector import STRUCTURE_CONTRACTS; print(len(STRUCTURE_CONTRACTS))"` prints `>= 9` (D8 v1.2: was 8, added NUTRIENT_REGISTRY safety_hard=8 contract)
  - All contracts hold against the real data files (`holds=True` for every row when run against current `data/`)
  - **D8 v1.2 NEW:** the NUTRIENT_REGISTRY safety_hard=8 contract holds against the real `lp_parameters_data.json`
- **verification**:
  - `python -c "from doc_introspector import check_structure_contracts; import json; data = {f: json.load(open(f'data/{f}')) for f in ['scenarios.json','constraints.json','audit_provenance.json','lp_parameters_data.json']}; print([r for r in check_structure_contracts(data) if not r['holds']])"` returns `[]`
- **rollback**: `git checkout doc_introspector.py`

### Phase 5 — Test integrity (kills Findings #17, #25) — D1 v1.2 REWRITTEN

#### Task 5-1 — DELETED in v1.2 (D1: tests already load real data via `bp.load_all_jsons()`)

- **task_id**: `5-1` (DELETED — DO NOT EXECUTE)
- **status**: DELETED in v1.2 per specialist review finding D1
- **rationale**: The plan v1.1.0 instructed the agent to "Replace hardcoded fixtures with calls that load real JSONs from `data/`" — but **the tests already do this**. Verified by `rg -c "load_all_jsons" tests/` returning 7 matches across both test files (`tests/test_cascade_integration.py`: 6 matches, `tests/test_dimensional_pipeline.py`: 1 match). The tests call `bp.load_all_jsons()` — the **production loader** at `build_pipeline.py:86` — which internally does the `open(fpath) ... json.load(f)` calls. The source review's naive `grep "json.load\|open("` missed this because those patterns live inside the production function, not the test files. Rewriting the tests would (a) waste 1–2 days of work, (b) replace a perfectly good `bp.load_all_jsons()` call with a redundant direct `json.load(open("data/..."))` call, (c) introduce drift between the test loader and the production loader. **Do not execute Task 5-1.** The only real (minor) issue is DRY duplication of the reference animal between the two test files — this is closed by Task 1-1 (extract `reference_cases.py`), which is preserved.

#### Task 5-2 — Implement `check_test_integrity()` with D6 regex + Check 9 (D6 v1.2 REWRITTEN)

- **task_id**: `5-2`
- **depends_on**: `[1-1]` (D1 v1.2: was `[5-1]`; now depends only on Task 1-1 since 5-1 is deleted)
- **files_touched**: `doc_introspector.py` (append), `build_pipeline.py` (new section generator + `validate_mapa` Check 9)
- **description**: Implement `check_test_integrity(tests_dir: Path) -> list[dict]` that for each `test_*.py` parses the AST and detects `@pytest.mark.integration` decorators via AST node walking (NOT docstring string matching). **D6 v1.2 REWRITTEN REGEX:** Detect real I/O via the textual regex `r"\bload_all_jsons\s*\("` OR `r'open\s*\(\s*["\'][^"\']*data/'` — NOT the v1.1.0 regex `r"\bjson\.load\(|open\("` which would false-positive on `open(` calls for audit-log writes (4 such calls in `tests/test_cascade_integration.py` — all write to `test_audit_log.md`, NOT data loads). The new regex recognizes that **the production loader IS the canonical way to load real data** — direct `json.load` calls in tests are an anti-pattern (they bypass the loader's validation). Return one row per file: `file`, `marked_integration` (bool), `loads_real_data` (bool). Wire into MAPA as a new "Test Suite Integrity" section. Add Check 9 to `validate_mapa()`: fail the gate if any test file has `marked_integration=True` AND `loads_real_data=False` — this is the configuration that violates the AAA+A mandate. **D6 v1.2 IMMEDIATE VERIFICATION:** after implementation, run `check_test_integrity(Path('tests'))` against the EXISTING (unmodified) tests — every row should report `loads_real_data=True` for files that call `bp.load_all_jsons()`. If any row reports `loads_real_data=False` for a file that DOES call `bp.load_all_jsons()`, the regex is wrong; do not commit.
- **acceptance_criteria**:
  - `python -c "from doc_introspector import check_test_integrity; from pathlib import Path; r = check_test_integrity(Path('tests')); print(r)"` lists every test file with correct `loads_real_data` classification
  - **D6 v1.2:** for `tests/test_cascade_integration.py`, `loads_real_data=True` (calls `bp.load_all_jsons` 6 times)
  - **D6 v1.2:** for `tests/test_dimensional_pipeline.py`, `loads_real_data=True` (calls `bp.load_all_jsons` 1 time, plus docstring says "Loads real JSONs only")
  - No row has `marked_integration=True, loads_real_data=False` after Task 1-1 lands
  - `python build_pipeline.py --generate-mapa --validate` exits 0
- **verification**:
  - `python -c "from doc_introspector import check_test_integrity; from pathlib import Path; print([x for x in check_test_integrity(Path('tests')) if not x['loads_real_data']])"` returns `[]` (all tests already load real data — D6 v1.2)
  - `python build_pipeline.py --generate-mapa --validate` exits 0
- **rollback**: `git checkout doc_introspector.py build_pipeline.py`

### Phase 6 — Sentinels + gate hardening (kills Findings Qual #1, #2, F #2, prevents all recurrence)

#### Task 6-1 — Add sentinels to `indice_plano_central.md`

- **task_id**: `6-1`
- **depends_on**: `[3-1]` (must run before `section1_header` is rewritten)
- **files_touched**: `docs/architecture/indice_plano_central.md` (modify — add only sentinel comments, no prose changes)
- **description**: Wrap the hand-authored prose preamble (background, principles, philosophy — NOT the roadmap or bundle table) in HTML sentinel comments: `<!-- MAPA:STATIC-START -->` ... `<!-- MAPA:STATIC-END -->`. Place a separate `<!-- MAPA:AUTO-ROADMAP -->` marker where the roadmap table should be inserted (it will be filled from `IMPLEMENTATION_SPEC` output). Place a `<!-- MAPA:AUTO-BUNDLES -->` marker where the bundle-size table should be inserted (filled from `compute_satellite_stats`). Do NOT modify any actual prose content — only add the four marker comments. The current `section1_header()` heuristic at L427 uses regex `r'^#+ +3\.?\b'` to stop copying at a `## 3.` heading, but `indice_plano_central.md` has NO such heading (its headings skip from `## 2.` directly to `## 11.` — see Finding #28 in v1.1 audit). **The break statement never executes, so `preamble_lines` accumulates the entire file.** This is why the MAPA contains the entire roadmap and bundle table verbatim — not because the heuristic stops too early, but because it never stops at all. The sentinel fix replaces this broken heuristic with explicit, enforceable boundaries.
- **acceptance_criteria**:
  - `rg "MAPA:STATIC-START" docs/architecture/indice_plano_central.md | Measure-Object -Line` returns 1
  - `rg "MAPA:STATIC-END" docs/architecture/indice_plano_central.md | Measure-Object -Line` returns 1
  - `rg "MAPA:AUTO-ROADMAP" docs/architecture/indice_plano_central.md | Measure-Object -Line` returns 1
  - `rg "MAPA:AUTO-BUNDLES" docs/architecture/indice_plano_central.md | Measure-Object -Line` returns 1
  - Diff vs `git HEAD` shows ONLY the 4 added lines (no prose modifications)
- **verification**: `rg "MAPA:(STATIC-START|STATIC-END|AUTO-ROADMAP|AUTO-BUNDLES)" docs/architecture/indice_plano_central.md`
- **rollback**: `git checkout docs/architecture/indice_plano_central.md`

#### Task 6-2 — Rewrite `section1_header()` to honor sentinels

- **task_id**: `6-2`
- **depends_on**: `[6-1, 3-1]`
- **files_touched**: `build_pipeline.py` (modify `section1_header` at L421-434)
- **description**: Replace the broken "copy until `## 3.`" heuristic (which never fires per Finding #28) with explicit sentinel-aware extraction. The new logic: read `docs/architecture/indice_plano_central.md`; extract text between `<!-- MAPA:STATIC-START -->` and `<!-- MAPA:STATIC-END -->` (byte-equal verbatim copy — no transformation); replace the `<!-- MAPA:AUTO-ROADMAP -->` location with the `IMPLEMENTATION_SPEC`-derived roadmap table (Phase 1 output); replace the `<!-- MAPA:AUTO-BUNDLES -->` location with the `compute_satellite_stats` table (Phase 3 output). Also fix the duplicate `fat_sources` row bug (Finding #2) at L1086-1122: the main loop already iterates ALL `protein_sources` groups including `fat_sources`, so the explicit hardcoded block at L1104-1122 is a double-add — delete the hardcoded block. The sentinel approach is robust to future doc reorganizations: the old regex heuristic depended on a specific heading number existing, but sentinels survive any renumbering.
- **acceptance_criteria**:
  - Generated MAPA section 1 contains the static prose verbatim (byte-equal to source between sentinels)
  - Generated MAPA section 1 contains computed bundle sizes (1001 for `sat_pipeline_codigo.md`, 1669 for `BUNDLE_IMPL_PIPELINE`)
  - Generated MAPA section 1 does NOT contain the roadmap text from `indice_plano_central.md` lines 217+ (the old roadmap is replaced by `IMPLEMENTATION_SPEC` output)
  - Generated MAPA curation table has exactly one `fat_sources` row (not two)
- **verification**:
  - `python build_pipeline.py --generate-mapa --out test-mapa.md`
  - `rg "sat_pipeline_codigo" test-mapa.md` shows line count = 1001 ±1 (NOT 3458 — that's `build_pipeline.py`)
  - `rg -c "fat_sources" test-mapa.md` returns 1 (not 2)
- **rollback**: `git checkout build_pipeline.py`

#### Task 6-3 — Add Checks 9–13 to `validate_mapa()`

- **task_id**: `6-3`
- **depends_on**: `[5-2, 6-2]`
- **files_touched**: `build_pipeline.py` (modify `validate_mapa` at L1331+)
- **description**: Add five new checks to `validate_mapa()`. Check 9 (test integrity) — from Task 5-2; fail if any `test_*.py` has `marked_integration=True` AND `loads_real_data=False`. Check 10 (self-count consistency) — `section_count`, `check_count`, and the "N checks" mentioned in the docstring must all agree; this fixes the 6-vs-8-vs-9 drift the prior review found in the file's own self-description (docstring says "8 checks", comment says "6 checks", function implements 9). Check 11 (spec drift) — from Critical Gap 2; fail if `detect_spec_drift()` returns any non-empty list. Check 12 (sentinel presence) — fail if `indice_plano_central.md` does not contain exactly one each of `MAPA:STATIC-START`, `MAPA:STATIC-END`, `MAPA:AUTO-ROADMAP`, `MAPA:AUTO-BUNDLES`. Check 13 (AUTO immutability) — regenerate the AUTO blocks, diff against committed version; if lines changed AND no source file in `IMPLEMENTATION_SPEC` was modified, fail (this catches hand-editing of generated content directly, rather than via downstream symptoms). Update the docstring at L8 (`--gate-mapa Validate generated MAPA against 8 checks`) to reflect the new count (13 checks). Check 10 itself enforces this update — the moment the function adds Check 9, Check 10 would fire on the stale "8 checks" docstring until it's updated.
- **acceptance_criteria**:
  - `python build_pipeline.py --generate-mapa --validate` runs all 13 checks
  - Docstring says "13 checks" (not "8 checks")
  - Each check has a name, description, and exit code semantics documented in a comment block above the check
- **verification**:
  - `python build_pipeline.py --generate-mapa --validate` exits 0 (all 13 pass on first run after migration)
  - `rg "13 checks" build_pipeline.py` returns matches
- **rollback**: `git checkout build_pipeline.py`

### Final Phase — Certification

#### Task F-1 — Full regeneration + gate run + certification

- **task_id**: `F-1`
- **depends_on**: `[6-3]`
- **files_touched**: `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` (regenerate), `docs/mapa-regeneration-delta.md` (new)
- **description**: Execute the final certification sequence: (1) run `python build_pipeline.py --generate-mapa --out MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md --validate` and verify all 13 checks pass; (2) diff new MAPA against `.orig-bak` from P3 — document every delta in `docs/mapa-regeneration-delta.md` with a finding reference for each change; (3) run `pytest tests/ -v` — all 32+ tests pass; (4) run the idempotency test: generate MAPA twice, byte-compare the two outputs (Critical Gap fix from prior review — without this, volatile content like timestamps in captured evidence will produce noisy `git diff` on every regeneration); (5) run the read-only test: snapshot all `*.py` files, generate MAPA, confirm no source file was modified during generation. If any of steps 1–5 fail, ABORT and roll back — do not partial-commit.
- **acceptance_criteria**:
  - All 13 `validate_mapa` checks pass
  - Delta document exists and lists every change vs original, with finding reference per change
  - Idempotency test passes: two consecutive generations produce byte-identical files
  - Read-only test passes: zero source files modified during generation
  - 32+ tests pass
- **verification**:
  - `python build_pipeline.py --generate-mapa --validate` exits 0
  - `pytest tests/ -v` exits 0
  - `git diff --stat` shows only the expected files changed
- **rollback**: `git checkout MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md build_pipeline.py` and restore `.orig-bak`

---

## Section 5 — Postconditions (Q0–Q8)

All postconditions must hold at the end of Task F-1. Each is verifiable by a concrete command.

- **Q0** — `validate_output()` no longer raises `AssertionError` on the 5-ingredient reference case (closes Finding #18)
  - Verify: `python build_pipeline.py --runtime --selection beef_muscle_raw,chicken_heart_raw,beef_liver_raw,beef_kidney_raw,salmon_atlantic_raw` exits 0
  - **D2 v1.2:** this is achieved by fixing the rounding site (Option A: validate unrounded `total_g`) OR explicit rounding tolerance (Option B: `N*0.05g`), NOT by `math.isclose()` (which would mask real drift)
- **Q1** — `IMPLEMENTATION_SPEC` is the sole source of implementation-status claims; no hardcoded `impl_gaps` list exists in `build_pipeline.py` (closes Finding #1)
  - Verify: `rg "impl_gaps\s*=\s*\[" build_pipeline.py` returns nothing
- **Q2** — Generated MAPA's bundle-size table shows `sat_pipeline_codigo.md` = 1001 ±1 lines (the satellite doc; closes Finding #10). Finding #19's claim of 3458 was a conflation with `build_pipeline.py`. BUNDLE_IMPL_PIPELINE total = 1669 (sum of indice_plano_central 290 + sat_pipeline_codigo 1001 + sat_dados_schema 378).
  - Verify: `python build_pipeline.py --generate-mapa --out test-mapa.md` then `rg "sat_pipeline_codigo" test-mapa.md` shows 1001
- **Q3** — Generated MAPA's structure-contracts section shows all 9+ contracts holding (closes Findings #13, #14, #15, #16, and D8 v1.2 NEW: NUTRIENT_REGISTRY safety_hard=8 with sul_value)
  - Verify: `rg "holds.*True" test-mapa.md` returns >= 9 matches
- **Q4** — `tests/test_cascade_integration.py` contains at least one `load_all_jsons()` call (closes Finding #17 — D1 v1.2: already passes pre-plan)
  - Verify: `rg "load_all_jsons" tests/test_cascade_integration.py` returns >= 1 match
  - **D1 v1.2 NOTE:** this postcondition already holds at P0 — it does NOT require Task 5-1 (deleted). It is preserved as a regression guard.
- **Q5** — All `@pytest.mark.integration` tests load real JSON data (closes Finding #25 — D1 v1.2: already passes pre-plan)
  - Verify: `python build_pipeline.py --generate-mapa --validate` passes Check 9
  - **D1 v1.2 NOTE:** this postcondition already holds at P0 — Check 9 (Task 5-2) preserves it as a permanent tripwire going forward
- **Q6** — `validate_mapa()` runs 13 checks (was 9 before, was claimed as "8" in docstring)
  - Verify: `rg "13 checks" build_pipeline.py` returns matches
- **Q7** — Generating MAPA twice produces byte-identical output (idempotency)
  - Verify: `python build_pipeline.py --generate-mapa --out a.md && python build_pipeline.py --generate-mapa --out b.md && fc /b a.md b.md` returns no differences
- **Q8** — Generating MAPA modifies zero source files (read-only)
  - Verify: snapshot `*.py` files before/after, diff is empty
- **Q9 (NEW D9 v1.2)** — Live evidence section captures LP-specific signals: `solver_status`, `cascade_level_used`, `lexicographic_stages_solved`, `clinical_floor_relaxed`, `solve_time_ms`, `nutrients_above_90pct_sul`
  - Verify: `rg "solver_status|cascade_level_used|clinical_floor_relaxed" test-mapa.md` returns >= 3 matches

---

## Section 6 — Risk Register

| Risk ID | Description | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `IMPLEMENTATION_SPEC` itself drifts (someone adds CLI mode without updating spec) | MEDIUM | HIGH (silent false MAPA) | Check 11 (spec drift) fails gate |
| R2 | Live evidence capture fails in CI (missing LP solver deps) | HIGH | MEDIUM (degraded MAPA in CI) | `--no-live-evidence` flag produces explicit degradation marker |
| R3 | Idempotency breaks due to timestamp/path in captured output | HIGH | HIGH (noisy git diffs) | `scrub_volatile()` mandatory; idempotency test (Task F-1 step 5) gates merge |
| R4 | Shadow mode never converges (perpetual discrepancies) | LOW | MEDIUM (indefinite dual path) | Time-box: 2 weeks; if still divergent, escalate to human review |
| R5 | Sentinel comments deleted from `indice_plano_central.md` | MEDIUM | HIGH (`section1_header` crashes or silently re-copies) | Check 12 (sentinel presence) fails gate |
| R6 | Hand-edit of AUTO block goes undetected | MEDIUM | HIGH (silent regression to old disease) | Check 13 (AUTO immutability) detects via git diff |
| R7 | JSON Schema validation rejects existing data files | LOW | HIGH (blocks generation entirely) | Run schemas against data as P1 verification before Phase 2 begins; if failures, abort and fix data separately (out of scope for this plan) |
| R8 | New `tolerant_le`/`tolerant_ge` masks real production drift | LOW | HIGH (clinical safety) | **D2 v1.2:** the v1.1.0 `math.isclose()` approach is FORBIDDEN — it would mask real drift. Use Option A (validate unrounded `total_g` from `result["_unrounded_total_g"]`) or Option B (explicit `N*0.05g` rounding tolerance). Task 0a-2 call-site audit must conclude "safe" before Task 0b-1; if any caller branches on strict equality, gate the fix behind `--strict-envelope` flag |
| R9 | Migration to AAA+A tests reduces test count (interim gap) | **DELETED D1 v1.2** | MEDIUM | **D1 v1.2:** Task 5-1 (test rewrite) is DELETED — tests already use `bp.load_all_jsons()` and follow AAA+A. No migration, no interim gap, no risk. This row is preserved as a historical record only; the risk no longer applies. |
| R10 | `doc_introspector.py` becomes its own source of hardcoding | MEDIUM | MEDIUM (new drift surface) | Treat `IMPLEMENTATION_SPEC` and `STRUCTURE_CONTRACTS` as version-controlled contracts; require PR review for any addition |
| R11 (NEW D5 v1.2) | Rounding policy at L2857 hides clinical drift in trace nutrients | MEDIUM | HIGH (clinical safety) | Phase 0c-1 audits all `round(..., N)` sites; findings outside F#18 scope trigger a follow-up plan (not blocking this plan) |
| R12 (NEW D7 v1.2) | `extract_cli_modes()` assumes `if/elif` chain but `main()` uses argparse/click/dispatch | MEDIUM | MEDIUM (spec drift detector false-negative) | Task 1-3 sub-step: inspect `main()` structure FIRST, adapt the AST walk to the actual dispatch style |

---

## Section 7 — Anti-Regression Properties (13 Checks)

The `validate_mapa()` function enforces 13 checks after this plan lands. Each check prevents a specific past failure mode from recurring. The first 9 are pre-existing (with one count-bug fix in Check 10); Checks 9–13 are added by this plan.

| Check # | Name | Catches | Added by |
|---|---|---|---|
| 0 | File presence | MAPA references nonexistent files | Existing |
| 1 | SHA-256 integrity | Source file tampering since last generation | Existing |
| 2 | Bundle size sanity | Bundle totals wildly off | Existing |
| 3 | Impl gap non-empty | Empty impl_gaps table | Existing |
| 4 | Roadmap non-empty | Empty roadmap section | Existing |
| 5 | Satellite file existence | Missing satellite `.md` | Existing |
| 6 | Schema reference | MAPA cites schemas that exist | Existing |
| 7 | Section count | Expected section count present | Existing |
| 8 | Stale content detector | Diff vs prior MAPA too large | Existing |
| 9 | Test integrity | `@pytest.mark.integration` test that loads no real data | Phase 5 (Task 5-2) — **D6 v1.2:** regex rewritten to detect `bp.load_all_jsons` calls, not `json.load` literals |
| 10 | Self-count consistency | docstring "N checks" ≠ actual check count | Phase 6 (Task 6-3) |
| 11 | Spec drift | CLI mode in code but not in `IMPLEMENTATION_SPEC`; or `cli_stub` branch no longer says "not implemented" | Phase 6 (Task 6-3) |
| 12 | Sentinel presence | `MAPA:STATIC-START/END/AUTO-ROADMAP/AUTO-BUNDLES` missing or duplicated in `indice_plano_central.md` | Phase 6 (Task 6-3) |
| 13 | AUTO immutability | AUTO block changed but no source file in `IMPLEMENTATION_SPEC` was modified | Phase 6 (Task 6-3) |

---

## Section 8 — Acceptance Criteria (Holistic)

The plan is complete when ALL of the following hold simultaneously. Partial completion is not a deliverable.

1. **All 25 findings addressed** — every finding in `systemic_review_findings.md` either has a closure commit OR is explicitly marked "no action" with rationale in Section 1 of this plan.
2. **All 13 checks pass** — `python build_pipeline.py --generate-mapa --validate` exits 0.
3. **All postconditions Q0–Q8 hold** — each verified by a concrete command listed in Section 5.
4. **Idempotency verified** — generating MAPA twice in succession produces byte-identical files.
5. **Read-only verified** — generating MAPA modifies zero source files (verified by snapshot-diff).
6. **Shadow mode retired** — 2-week migration window complete OR human sign-off documented in `docs/migration-log.md`.
7. **Migration delta documented** — every change vs original MAPA is listed in `docs/mapa-regeneration-delta.md` with finding reference.
8. **Provenance markers present** — every generated table row has `<!-- SOURCE: ... -->` HTML comment.
9. **No new dependencies added** — `pip freeze` diff before/after shows zero new packages (Jinja2 forbidden per Section 0).
10. **Tests pass** — `pytest tests/ -v` returns >= 32 passed, 0 failed.

---

## Section 9 — Explicit Non-Goals

To prevent scope creep, the following are explicitly OUT OF SCOPE for this plan. If the executing agent encounters any of these, log a new finding rather than fixing it.

- **NO** changes to `data/*.json` content (Phase 0a/0b only touches `build_pipeline.py`)
- **NO** Jinja2 or any template engine (architectural decision preserved per `build_pipeline.py` docstring)
- **NO** migration of section generators to a new file structure (fix in place)
- **NO** refactoring of `solve_cascade`, `build_lp_problem`, or other core solver functions (only `validate_output` epsilon fix)
- **NO** addition of new nutrients to `NUTRIENT_REGISTRY`
- **NO** changes to satellite `.md` content (only structural sentinel comments added in Phase 6-1)
- **NO** FDC ID fixes for `DB_ingredientes.json` (covered by separate plan `plan-gsd-fdc-nutrient-fix.md`)
- **NO** changes to the LP solver algorithm itself (Big-M, lexicographic cascade, clinical floor MILP — all confirmed working per Findings #21, #22, #23)
- **NO** addition of new AAA+A tests beyond what Phase 5 requires to close Finding #17 (test coverage expansion is a separate effort)
  - **D1 v1.2 NOTE:** Task 5-1 (test rewrite) is DELETED — Finding #17 is a false positive (tests already use `bp.load_all_jsons()`). The non-goal stands: no test expansion. The only test-related change in v1.2 is Task 5-2 (Check 9 implementation) and Task 1-1 (reference_cases.py extraction).

---

## Section 10 — Handoff Notes for Executing Agent

If you are the LLM/agent executing this plan, follow these rules. They are mandatory, not suggestions.

1. **Read `systemic_review_findings.md` in full before starting** — every claim in this plan references a finding by number; you must understand the evidence behind each one. Do not skip "MATCH" or "CONFIRMED" findings — they tell you what NOT to break.
2. **Read `plan-mapa-generator-fix-specialist-review.md` before starting** (v1.2 NEW) — this is the specialist assessment that produced the D1–D9 patches baked into this plan. It explains WHY certain v1.1.0 approaches were wrong (Finding #17 false positive, F#18 tolerance misdiagnosis, three non-existent functions, etc.). Without this context, you may be tempted to "fix" the v1.2 patches back to the v1.1.0 form.
3. **Read the relevant section of `build_pipeline.py` before modifying it** — never edit blind. The line numbers in this plan reference the file as of 2026-07-16; they may have shifted by the time you execute. Use `rg` to relocate.
4. **Execute Task 0-zero FIRST** (v1.2 NEW) — do NOT skip the pre-flight sanity check. It empirically verifies the F#18 gap is 0.05g (rounding) and not 1e-9 g (float). If you skip this and the gap turns out to be float-scale, the entire Phase 0a/0b design is wrong and you will waste hours.
5. **Execute tasks in dependency order** — the `depends_on` graph is mandatory; do not parallelize tasks that depend on each other. The allowed parallelism is: Tasks 0a-1 ‖ 0a-2 ‖ 0c-1 (after Task 0-zero) and Tasks 4-1 ‖ 4-2 (after Task 1-4).
6. **Run verification commands after every task** — do not batch. If a verification fails, stop and fix before proceeding to dependent tasks.
7. **Append to `worklog.md` after every task** — format: `Task ID, Agent, Task, Work Log, Stage Summary` per project convention. The worklog is the shared memory between sessions.
8. **If a verification fails, STOP** — do not proceed to dependent tasks. Edit the offending file in place (do not regenerate from scratch) and re-run the verification.
9. **If a precondition P0–P7 is violated, STOP** — abort and report. Do not attempt to recover by modifying preconditions.
10. **If you discover a new finding during execution**, append it to `systemic_review_findings.md` as Finding #26+ before addressing it. Do not silently absorb new findings into existing tasks.
11. **Never modify `data/*.json`** — if a JSON looks wrong, log it as a new finding. JSON content fixes are out of scope for this plan.
12. **Use Windows paths** — the project lives at `C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\`, not `/home/z/my-project/`. All verification commands in this plan use PowerShell-style syntax on Windows.
13. **Use `rg` (ripgrep) instead of `grep`** — `rg` is faster, respects `.gitignore` by default, and has consistent behavior across platforms.
14. **Treat `IMPLEMENTATION_SPEC` and `STRUCTURE_CONTRACTS` as version-controlled contracts** — any addition, removal, or strategy change requires explicit PR review and a worklog entry justifying the change.
15. **If you are unsure whether to apply a fix or log a finding, log the finding** — false positives cost minutes; silent fixes cost days of debugging downstream.
16. **DO NOT execute Task 5-1** (v1.2 D1) — it has been DELETED. The plan v1.1.0 instructs you to rewrite 32 working tests; this would waste 1–2 days and introduce drift between the test loader and the production loader. Tests already use `bp.load_all_jsons()`. Skip Task 5-1; proceed directly to Task 5-2.
17. **DO NOT use `math.isclose()` for the F#18 fix** (v1.2 D2) — the v1.1.0 proposed tolerance (`rel_tol=1e-6, floor=1e-9`) is ~70× too tight for the actual 0.05g rounding gap. Use Option A (preferred: validate unrounded `total_g` from `result["_unrounded_total_g"]`) or Option B (fallback: explicit `N*0.05g` rounding tolerance). Generic `math.isclose()` would mask real envelope drift — this is the R8 trap.
18. **DO NOT classify `format_allocations`, `expand_category_wildcards`, `run_pipeline` as `inline_in`** (v1.2 D3) — these functions do NOT exist anywhere in `build_pipeline.py` (verified by `rg "def format_allocations|def expand_category_wildcards|def run_pipeline" build_pipeline.py` returning 0 matches). Use the `missing` strategy. The source review (Qual #4, F #20) misread inline list-comprehension code at L2839-2853 as an inlined function.
19. **Inspect `main()` structure before implementing `extract_cli_modes()`** (v1.2 D7) — the plan v1.1.0 assumed `main()` uses `if/elif mode == "--X":` chain. It may use argparse, click, or dict dispatch instead. Run `rg -n "def main\(" build_pipeline.py`, read the first 50 lines of `main()`, and adapt the AST walk to the actual dispatch style.

---

## Section 11 — Glossary

- **AAA+A** — Arrange, Act, Assert, Audit. The test pattern mandated by `docs/sat_testes_consolidado.md`. The fourth "A" (Audit) requires logging the full result for human inspection, distinguishing real implementations from stubs.
- **AST** — Abstract Syntax Tree. Used by `ImplIntrospector` to verify function existence without executing code. AST tells you a function EXISTS; it does not tell you it WORKS. The latter is what Phase 4's live evidence capture is for.
- **AUTO block** — Any section of the MAPA rendered from computed facts (roadmap table, bundle sizes, structure contracts, live evidence). Marked with `<!-- MAPA:AUTO-* -->` sentinels. Hand-editing an AUTO block triggers Check 13.
- **Bundle** — A named group of satellite `.md` files (e.g. `BUNDLE_IMPL_PIPELINE` = `sat_pipeline_codigo.md` + `indice_plano_central.md`). Used for token-budget estimation.
- **DRIFT** (v1.1) — A `IMPLEMENTATION_SPEC` status category for functions that exist but not in the form the spec describes. **v1.2 D3 NOTE:** the `inline_in` strategy that produced DRIFT status has been REMOVED — the three functions it was meant to classify do not exist anywhere. Use the `missing` strategy instead, which produces MISSING status.
- **`impl_gaps`** — The hardcoded list at `build_pipeline.py:1194-1201` that this plan replaces with `IMPLEMENTATION_SPEC`. The root cause of Finding #1.
- **MISSING** (v1.2 D3 NEW) — A `IMPLEMENTATION_SPEC` status category for functions that do not exist anywhere in the module AST. Distinct from `NOT IMPLEMENTED` (function exists but body says "not implemented") and `DRIFT` (function exists but in different form). The `missing` strategy returns this status when the target function name is not found in any `FunctionDef` node in the module.
- **Option A** (v1.2 D2 NEW) — Preferred fix for F#18: validate the UNROUNDED `total_g` from `result["_unrounded_total_g"]` (a new private field populated by `build_output_contract` before rounding). The validator falls back to `sum(rounded_allocations)` if the private field is absent. Fixes the bug at its source.
- **Option B** (v1.2 D2 NEW) — Fallback fix for F#18: explicit `rounding_tolerance = N_allocs * 0.05 + 1e-9` added to the envelope comparison. Mathematically honest (we round to 0.1g, so we tolerate up to N×0.05g cumulative error).
- **Option C** (v1.2 D2 NEW — FORBIDDEN) — Generic `math.isclose()` with default tolerances. Would fix the F#18 symptom but also mask real envelope violations up to the tolerance threshold. This is the R8 trap. Do NOT use.
- **R8 trap** (v1.2 D2 NEW) — The named anti-pattern where adding tolerance to a clinical safety validator trades correctness for convenience. Risk R8 in Section 6.
- **Sentinel** — An HTML comment marker (`<!-- MAPA:STATIC-START -->`, etc.) placed in `indice_plano_central.md` to delimit hand-authored prose from generated content. Replaces the fragile "copy everything before `## 3.`" heuristic.
- **SUL** — Safety Upper Limit. The maximum safe intake of a nutrient (e.g. `vitamin_a_iu` SUL = 9375 IU). Stored in `lp_parameters_data.json` NUTRIENT_REGISTRY entries with `constraint_tier: safety_hard`. **v1.2 D8 NEW CONTRACT:** there must be exactly 8 `safety_hard` entries, each with a `sul_value` field — encoded as a `STRUCTURE_CONTRACT` to convert runtime KeyError into gate-tripped regression.
- **Volatile content** — Any string in captured stdout that differs between runs (timestamps, absolute paths, PIDs, memory addresses). Stripped by `scrub_volatile()` before embedding in MAPA to preserve idempotency. **v1.2 D4 NOTE:** the LP solver itself is already deterministic (`randomSeed=12345`, `threads=1`), so volatile content is limited to stdout decorations, not solver output.

---

## Section 12 — Specialist Review Patch Log (v1.1.0 → v1.2.0)

This section is the audit trail of patches applied in v1.2.0 based on `plan-mapa-generator-fix-specialist-review.md`. Each entry maps a specialist finding (D1–D9) to the specific plan section(s) patched.

| Finding | Severity | Patches Applied | Plan Section(s) Modified |
|---|---|---|---|
| D1 — Finding #17 is a false positive (tests use `bp.load_all_jsons`) | BLOCKING | F#17 reclassified CRITICAL → INFO; Task 5-1 DELETED; Task 5-2 depends_on changed from `[5-1]` → `[1-1]`; Q4/Q5 marked "already passes pre-plan"; R9 risk marked DELETED | Section 0 (Must NOT assume), Section 1 (F #17, Qual #3, F #25 rows), Section 3 (DAG), Phase 5 (Tasks 5-1, 5-2), Section 5 (Q4, Q5), Section 6 (R9), Section 9 (Non-Goals) |
| D2 — Phase 0a/0b epsilon fix is numerically wrong (5 orders of magnitude too tight) | BLOCKING | New Task 0-zero (pre-flight sanity check); Phase 0a-1 rewritten (Option A preferred, Option B fallback, Option C FORBIDDEN); Phase 0a-2 expanded (audit `round(grams, 1)` at L2857 too); Phase 0b-1 rewritten (apply Option A or B, not `math.isclose`) | Frontmatter (blocking_prerequisites), Section 0 (Must NOT assume — F#18 root cause), Section 1 (F #18 row), Section 3 (DAG), Phase 0-zero (NEW), Phase 0a (Tasks 0a-1, 0a-2 REWRITE), Phase 0b (Task 0b-1 REWRITE), Section 5 (Q0), Section 6 (R8), Section 10 (handoff notes #4, #17), Section 11 (Option A/B/C, R8 trap glossary) |
| D3 — `format_allocations`, `expand_category_wildcards`, `run_pipeline` do not exist (not "inlined") | BLOCKING | `inline_in` strategy REMOVED; new `missing` strategy added; IMPLEMENTATION_SPEC entries 8/9/10 reclassified `inline_in` → `missing`; Phase 1-4 acceptance criteria updated (MISSING status, not NOT IMPLEMENTED) | Section 0 (Must NOT assume), Section 1 (Qual #4, F #20 rows), Phase 1 (Tasks 1-2, 1-3, 1-4), Section 10 (handoff note #18), Section 11 (DRIFT, MISSING glossary) |
| D4 — Phase 4 determinism concern overstated (LP solver already pinned) | Minor | Phase 4-2 description tightened: "LP solver is already pinned (`randomSeed=12345`, `threads=1`); no additional determinism treatment needed"; cross-platform float caveat noted | Phase 4 (Task 4-2 description), Section 11 (Volatile content glossary) |
| D5 — Real production safety issue is the rounding site, not the comparison | Major | New Phase 0c (Task 0c-1) added — rounding policy audit at L2857; new risk R11 | Frontmatter (blocking_prerequisites, max_concurrent_tasks), Section 3 (DAG), Phase 0c (NEW), Section 6 (R11 NEW) |
| D6 — Check 9 regex is wrong (would false-positive on existing tests) | BLOCKING (consequence of D1) | Task 5-2 description rewritten — regex changed from `r"\bjson\.load\(|open\("` to `r"\bload_all_jsons\s*\(" OR r'open\s*\(\s*["\'][^"\']*data/'`; immediate verification step added | Section 7 (Check 9 description), Phase 5 (Task 5-2 REWRITE) |
| D7 — `detect_spec_drift()` assumes if/elif chain but `main()` may use argparse | Minor | Task 1-3 description expanded with new sub-step: "inspect `main()` structure FIRST"; new risk R12 | Phase 1 (Task 1-3 description), Section 6 (R12 NEW), Section 10 (handoff note #19) |
| D8 — Missing LP-specific structural contract (NUTRIENT_REGISTRY safety_hard=8) | Minor | New 9th `STRUCTURE_CONTRACT` added: `NUTRIENT_REGISTRY` must have exactly 8 `safety_hard` entries, each with `sul_value`; Phase 2-1 acceptance criteria updated to `>= 9`; Q3 updated to `>= 9 matches` | Phase 2 (Task 2-1 description + acceptance_criteria), Section 5 (Q3), Section 11 (SUL glossary) |
| D9 — Phase 4 evidence capture misses LP-specific signals | Major | Task 4-1 description expanded — 6 new LP-specific evidence fields: `solver_status`, `cascade_level_used`, `lexicographic_stages_solved`, `clinical_floor_relaxed`, `solve_time_ms`, `nutrients_above_90pct_sul`; new 4th smoke run (solver_status_diagnostic); new Q9 postcondition | Phase 4 (Task 4-1 description + acceptance_criteria), Section 5 (Q9 NEW) |
| D10 (positive) — DAG, sentinels, idempotency, provenance markers, `--no-live-evidence`, spec drift check, anti-regression count, risk register, forbidden actions | Positive | No changes — preserved as-is | (none) |

### v1.2.0 Net Effect

- **Tasks added:** 2 (Task 0-zero, Task 0c-1)
- **Tasks deleted:** 1 (Task 5-1)
- **Strategies removed:** 1 (`inline_in`)
- **Strategies added:** 1 (`missing`)
- **STRUCTURE_CONTRACTS added:** 1 (NUTRIENT_REGISTRY safety_hard=8)
- **Evidence fields added:** 6 (LP-specific signals)
- **Postconditions added:** 1 (Q9)
- **Risks added:** 2 (R11, R12)
- **Risks deleted:** 1 (R9 — D1 consequence)
- **Blocking fixes applied:** 3 (D1, D2, D3)
- **Major fixes applied:** 2 (D5, D9)
- **Minor fixes applied:** 4 (D4, D7, D8, D6)
- **Estimated effort delta:** +0.5 day for new Phase 0c/0-zero; −1.5 days from Task 5-1 deletion; net **−1 day** vs v1.1.0
