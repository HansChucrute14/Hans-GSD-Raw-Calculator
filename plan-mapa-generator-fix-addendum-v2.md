---
plan_id: plan-mapa-generator-fix-addendum
version: 2.0.0
generated: 2026-07-16
supersedes: plan-mapa-generator-fix-addendum.md v1.0.0 — that version wrongly assumed Task F-1 was already certified and structured every fix as post-hoc Phase 7 patches. Actual state: Phase 5 is complete, Phase 6 has NOT started. This version amends the not-yet-executed Phase 6 task definitions in place (built correctly the first time, no rework) and ships two small patches to already-complete Phase 1 and Phase 4 code, since those phases are explicitly in scope for improvement per operator correction.
parent_plan: plan-mapa-generator-fix.md (v1.2.0) — Phases 0-zero, 0a, 0b, 0c, 1, 2, 3, 4, 5 complete; Phase 6 and Final (F-1) NOT yet executed
parent_document: systemic_review_findings.md (827 lines canonical, 25 findings, 1 retracted)
source_of_this_addendum: Code review of plan-mapa-generator-fix v1.2.0 against the live build_pipeline.py architecture (Claude Sonnet 5, 2026-07-16) — 5 gaps identified, 3 of which land inside not-yet-executed Phase 6 tasks and are fixed by amending those task definitions directly, 2 of which touch already-shipped Phase 1/4 code and are fixed via small isolated patches. v1.2.0's Task 6-4 (shadow mode) is dropped in this addendum, not amended — see Section 0.
repo_source: https://github.com/HansChucrute14/Hans-GSD-Raw-Calculator.git
target_repo: C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\
language: en-US
audience: LLM agent (stateless executor — Claude/GPT/local)
handoff_protocol: LLM-to-LLM with atomic tasks, depends_on DAG, AAA+A verification, rollback
estimated_effort: adds ~0.5 day to the parent plan's remaining Phase 6 + Final estimate; the two patches (1-P1, 4-P1) are ~30 min each and can run any time before Phase 6 starts
trigger_condition: Execute now. Phase 5 of the parent plan is complete; Phase 6 has not begun. Patches 1-P1 and 4-P1 can run immediately (their target code already exists). The Phase 6 amendments below REPLACE the corresponding task text in plan-mapa-generator-fix.md v1.2.0 — when you reach Phase 6, execute the amended versions here, not the original v1.2.0 wording for Tasks 6-2 and 6-3, execute the new Task 6-5, and skip v1.2.0's Task 6-4 entirely (dropped — see Section 0).
verification_pattern: AAA+A (Arrange real files, Act on real code, Assert on real output, Audit by literal command+output)
provenance_markers: HTML comments after every generated row, consistent with parent plan (e.g. <!-- SOURCE: ADDENDUM-1-P1 / doc_introspector.py:detect_spec_drift -->)
max_concurrent_tasks: 2 (Patches 1-P1 ‖ 4-P1 are independent and can run now, in parallel; the three Phase 6 amendments/additions (6-2, 6-3, 6-5) execute in the same order/dependency shape as v1.2.0's own DAG minus Task 6-4 — only their internal content changed, not their position)
forbidden:
  - Modifying any data/*.json content
  - Reopening Phases 0-zero, 0a, 0b, 0c, 2, 3, or 5 (out of scope — no gap identified in this review touches them)
  - Executing Phase 6 Tasks 6-2/6-3 using the original v1.2.0 task text once this addendum exists — use the amended versions in Section 4 below instead, to avoid building the known-flawed version and then patching it a second time
  - Executing v1.2.0's Task 6-4 at all — it is dropped, not amended
  - Adding Jinja2 or any template engine dependency
---

# Addendum v2.0.0: MAPA Generator Fix — Pre-Phase-6 Corrections

## Section 0 — Context Boundary (READ FIRST)

**May assume:**

- Phases 0-zero, 0a, 0b, 0c, 1, 2, 3, 4, and 5 of `plan-mapa-generator-fix.md` v1.2.0 are complete and passing their own acceptance criteria: `IMPLEMENTATION_SPEC`, `ImplIntrospector`, `STRUCTURE_CONTRACTS`, `compute_satellite_stats()`, `capture_live_evidence()`, `scrub_volatile()`, and `check_test_integrity()` all exist in `doc_introspector.py` and are wired into `build_pipeline.py` per Tasks 1-1 through 5-2.
- `tests/reference_cases.py` exists (Task 1-1) and both `REFERENCE_ANIMAL` and `REFERENCE_SELECTION` are importable from it.
- Phase 6 (Tasks 6-1, 6-2, 6-3) and the Final Phase (Task F-1) have **not** been executed. `section1_header()` still uses the original "copy until `## 3.`" heuristic (never fires, per Finding #28) — the sentinel rewrite has not happened yet. `validate_mapa()` still has 9 checks (0-8), not 13. `indice_plano_central.md` has no `MAPA:*` sentinel comments yet.
- The parent plan's Section 11 Glossary terms apply unchanged.
- **v1.2.0's Task 6-4 (shadow mode) is dropped by this addendum, not amended.** Its comparison target (the old hardcoded `impl_gaps` path) was already deleted by Task 1-4, so the task as originally written has nothing left to compare. Do not execute it, in any form. The regression-safety purpose it was reaching for is already covered by the Final Phase's own delta-diff against `.orig-bak` (Task F-1, unchanged from v1.2.0) — no replacement mechanism is needed.

**Must NOT assume:**

- That amending a not-yet-executed task's text is the same as "reopening" a phase. Tasks 6-2 and 6-3 below are still first-time implementations — they've just been corrected before being written, which is strictly cheaper than writing them wrong and patching afterward. This is not scope creep on Phase 6; it's Phase 6 done right the first time.
- That Patches 1-P1 and 4-P1 require touching anything else in Phase 1 or Phase 4. Both are additive functions in already-existing files — `IMPLEMENTATION_SPEC`, `ImplIntrospector`, `capture_live_evidence()`'s core four smoke runs, and `scrub_volatile()` are all untouched.
- That the original v1.2.0 wording for Tasks 6-2/6-3 is still valid. It is superseded by Section 4 below for those two task IDs specifically. Task 6-1 (add sentinels) is unaffected and should be executed exactly as v1.2.0 specifies it.

**Forbidden actions (violations abort this addendum):**

- Modifying any `data/*.json` content.
- Touching Phase 0-zero/0a/0b/0c/2/3/5 code.
- Building Task 6-2 or 6-3 from the original v1.2.0 text after this addendum exists.
- Executing v1.2.0's Task 6-4 in any form.

---

## Section 1 — Gaps → Disposition Mapping

| Gap | Where it actually lands | Disposition |
|---|---|---|
| G1 — `**Generated:** {datetime.now().isoformat()}` at `section1_header()` L440 breaks byte-identical regeneration (parent plan's Q7) | Inside `section1_header()`, which Task 6-2 rewrites for the first time (sentinel-aware extraction) | **Fold into amended Task 6-2** — fix it while writing the function's replacement, not as a follow-up patch to a function that's about to be rewritten anyway |
| G3 — Check 13 (AUTO immutability), as specified, only recognizes `IMPLEMENTATION_SPEC` files as legitimate change sources, will false-fail on ordinary `data/*.json` / satellite `.md` / `tests/*.py` changes | Check 13 is written for the first time in Task 6-3 | **Fold into amended Task 6-3** — write the correct predicate from the start instead of shipping a narrow one and widening it later |
| G4 — Nothing makes `--generate-mapa --validate` run automatically; the gate only protects the repo if a human remembers to invoke it | Genuinely new work, not covered by any existing v1.2.0 task | **New Task 6-5** |
| G5 — R10's mitigation ("require PR review") has no automated backstop for solo-repo use | Extends `doc_introspector.py`'s `detect_spec_drift()` (Task 1-3, already shipped) and `STRUCTURE_CONTRACTS`' `StructureContract` dataclass (Task 2-1, already shipped) | **Patch 1-P1 + Patch 2-P1** — small additive functions on top of already-complete Phase 1/2 code |
| G6 — `--no-live-evidence` degradation flag has no check confirming it isn't the *permanent* runtime state | Extends the evidence section generator built in Task 4-3 (already shipped) | **Patch 4-P1** — additive, doesn't touch the four core smoke runs |

---

## Section 2 — Preconditions

**AP0 — Correct starting point**
- `rg "MAPA:STATIC-START" docs/architecture/indice_plano_central.md` returns **zero** matches — confirms Phase 6 genuinely hasn't started (if this is non-empty, this addendum's premise is wrong; re-check which phase you're actually at before proceeding)
- `rg "def check_test_integrity" doc_introspector.py` returns a match — confirms Phase 5 is genuinely complete
- `python build_pipeline.py --generate-mapa --validate` currently reports checking against **9** checks (Check 0-8), not 13 — a quick sanity read of the CLI output confirms Phase 6 hasn't landed

**AP1 — Clean tree**
- `git status --porcelain` returns empty

---

## Section 3 — Task Graph (DAG)

```
AP0, AP1
   │
   ├── Patch 1-P1 (extend detect_spec_drift with coverage-drift) ──┐
   ├── Patch 2-P1 (add `covers` field to StructureContract)         │  (parallel, independent
   └── Patch 4-P1 (live-evidence degradation monitor)                │   of Phase 6 entirely —
                                                                      │   run these whenever)
                                                                      ▼
   [ existing Task 6-1 — add sentinels — UNCHANGED, run exactly as v1.2.0 specifies ]
                     │
   Amended Task 6-2 (rewrite section1_header — now includes G1 state-hash fix)
                     │
   Amended Task 6-3 (add Checks 9-15 — Check 13 now correctly scoped from the start)
                     │
   New Task 6-5 (pre-commit / CI trigger)
                     │
   Final Task F-1 (unchanged from v1.2.0, but Q7's verification now checks the
                    state-hash line instead of a timestamp — see Section 5, AQ0)
```

Patch 1-P1, 2-P1, 4-P1 have no dependency relationship to the Phase 6 chain — run them at any point, including right now, before Phase 6 even begins.

---

## Section 4 — Patches (to already-shipped Phase 1/4 code) and Amended Phase 6 Tasks

### Patch 1-P1 — Extend `detect_spec_drift()` with coverage-drift detection (closes G5, part 1)

- **task_id**: `1-P1`
- **depends_on**: `[AP0, AP1]`
- **files_touched**: `doc_introspector.py` (append `detect_coverage_drift()`, does not modify `detect_spec_drift()`'s existing logic)
- **description**: Add `detect_coverage_drift(data: dict, contracts: list) -> list[str]` alongside the existing `detect_spec_drift()` from Task 1-3. For each JSON file that has at least one `STRUCTURE_CONTRACTS` entry, compare its live top-level keys (or, for `NUTRIENT_REGISTRY`-shaped nested dicts, the union of per-entry field names) against the `covers` set declared on each applicable contract (see Patch 2-P1 — this patch depends on that field existing). Return any key present in live data but absent from every contract's `covers` set for that file. This is deliberately **non-blocking** — deciding whether a new key deserves a formal contract is a judgment call the tool shouldn't make unilaterally. It's an early-warning list, not a 14th hard gate check; wire its rendering into the MAPA in the amended Task 6-3 below (Check 14, informational) rather than here — this patch only implements the detection function.
- **acceptance_criteria**:
  - `detect_coverage_drift()` returns `[]` against current `data/` (all 9+ contracts from Task 2-1 already cover what they check)
  - Manually adding a throwaway key to an in-memory copy of `scenarios.json`'s data causes it to appear in the returned list
- **verification**: `python -c "from doc_introspector import detect_coverage_drift, STRUCTURE_CONTRACTS; import json; from build_pipeline import JSON_FILES; data={f: json.load(open(f'data/{f}')) for f in JSON_FILES}; print(detect_coverage_drift(data, STRUCTURE_CONTRACTS))"` prints `[]`
- **rollback**: `git checkout doc_introspector.py`

### Patch 2-P1 — Add `covers` field to `StructureContract` (closes G5, part 2)

- **task_id**: `2-P1`
- **depends_on**: `[AP0, AP1]` (independent of 1-P1, but 1-P1's verification will fail until this lands, since it reads the field)
- **files_touched**: `doc_introspector.py` (modify `StructureContract` dataclass definition, add `covers` to each of the 9+ existing entries)
- **description**: Add `covers: set[str] = field(default_factory=set)` to the `StructureContract` dataclass from Task 2-1. Backfill it on every existing entry — e.g. the `scenarios.json` contract's `covers = {"scenario_id", "status", "targets"}` (whatever fields its predicate actually inspects), the `NUTRIENT_REGISTRY` safety_hard=8 contract's `covers = {"constraint_tier", "sul_value"}`, etc. This is a mechanical, low-risk addition — it doesn't change any predicate's pass/fail behavior, only documents what each one is *about*, which is exactly what Patch 1-P1 needs to compute coverage drift without re-deriving it from lambda introspection (fragile) or JSON-Schema parsing (only works for the schema-based contracts, not the hand-rolled ones).
- **acceptance_criteria**:
  - All 9+ `STRUCTURE_CONTRACTS` entries have a non-empty `covers` field
  - Existing Task 2-1 verification (`check_structure_contracts()` against real data, all `holds=True`) still passes unchanged — this patch must not alter contract semantics
- **verification**: `python -c "from doc_introspector import STRUCTURE_CONTRACTS; print([c.covers for c in STRUCTURE_CONTRACTS])"` shows no empty sets; `python -c "from doc_introspector import check_structure_contracts; import json; from build_pipeline import JSON_FILES; data={f: json.load(open(f'data/{f}')) for f in JSON_FILES}; print([r for r in check_structure_contracts(data) if not r['holds']])"` returns `[]`
- **rollback**: `git checkout doc_introspector.py`

### Patch 4-P1 — Live-evidence degradation monitor (closes G6)

- **task_id**: `4-P1`
- **depends_on**: `[AP0, AP1]` (independent of 1-P1/2-P1)
- **files_touched**: `doc_introspector.py` (append `check_evidence_freshness()`)
- **description**: Task 4-3's `--no-live-evidence` flag is a legitimate escape hatch for environments missing LP solver deps, but it can silently become permanent if nobody notices the evidence section has read `> Live evidence skipped` for months. Add `check_evidence_freshness(worklog_path: Path, git_log_fallback: bool = True) -> dict` that scans the last 10 MAPA-regeneration entries (from `worklog.md` if the convention was kept, else fall back to `git log --oneline -- MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md`) for whether `--no-live-evidence` was used. Return `{"consecutive_degraded": N, "warn": N >= 10}`. This patch only implements the detection function — wiring its output into the MAPA as a warning banner happens in the amended Task 6-3 below (Check 15, informational), consistent with keeping detection and rendering separate the same way Patch 1-P1 does.
- **acceptance_criteria**:
  - Function returns `consecutive_degraded=0, warn=False` against current git history (live evidence has been used normally through Phase 4/5)
  - Simulating 10 consecutive `--no-live-evidence` log entries causes `warn=True`
- **verification**: `python -c "from doc_introspector import check_evidence_freshness; from pathlib import Path; print(check_evidence_freshness(Path('worklog.md')))"`
- **rollback**: `git checkout doc_introspector.py`

---

### Amended Task 6-2 — Rewrite `section1_header()` to honor sentinels (supersedes v1.2.0 Task 6-2)

- **task_id**: `6-2`
- **depends_on**: `[6-1, 3-1]` (unchanged from v1.2.0)
- **files_touched**: `build_pipeline.py` (modify `section1_header` at L421-434), `doc_introspector.py` (append `compute_state_marker()`)
- **description**: Everything in v1.2.0's original Task 6-2 (sentinel-aware extraction between `MAPA:STATIC-START/END`, `MAPA:AUTO-ROADMAP`/`MAPA:AUTO-BUNDLES` insertion, deleting the duplicate `fat_sources` block at L1104-1122) **plus** the following, added while the function is already being rewritten: implement `compute_state_marker(base_dir: Path, json_files: list[str], satellite_bundles: dict) -> str` in `doc_introspector.py` — SHA-256 every file `generate_mapa()` reads (11 JSONs, `build_pipeline.py` itself, all 8 satellite `.md` files, every `tests/test_*.py`), sorted by filename, concatenate, hash, take first 16 hex chars. Replace the line `lines.append(f"**Generated:** {datetime.now().isoformat()}")` with:
  ```python
  lines.append(f"**State Hash:** {compute_state_marker(BASE_DIR, JSON_FILES, SATELLITE_BUNDLES)}")
  lines.append(f"**Last regenerated (date, informational only):** {datetime.now().date().isoformat()}")
  ```
  Date-only (no time-of-day) keeps same-day regenerations byte-identical in practice; if that's still too strict, exclude that one line from the Final Phase's idempotency byte-compare explicitly rather than dropping it. **Audit sub-step:** `rg -n "datetime\.now\(\)|time\.time\(\)|os\.getpid\(\)|random\." build_pipeline.py doc_introspector.py` — confirm every match is either inside `capture_live_evidence()`'s already-`scrub_volatile()`-covered scope, or the new date-only line above. Fix any other match the same way before closing this task.
- **acceptance_criteria** (v1.2.0's four criteria, plus):
  - `python build_pipeline.py --generate-mapa --out a.md && python build_pipeline.py --generate-mapa --out b.md && fc /b a.md b.md` reports **no differences** (this was never true under the original v1.2.0 wording — it's a new, correct requirement)
  - `compute_state_marker()` changes when any covered file changes, stays constant otherwise
- **verification**: v1.2.0's verification commands, plus the idempotency `fc /b` check above
- **rollback**: `git checkout build_pipeline.py doc_introspector.py`

### Amended Task 6-3 — Add Checks 9-15 to `validate_mapa()` (supersedes v1.2.0 Task 6-3, which specified only Checks 9-13)

- **task_id**: `6-3`
- **depends_on**: `[5-2, 6-2]` (unchanged from v1.2.0)
- **files_touched**: `build_pipeline.py` (modify `validate_mapa` at L1331+)
- **description**: Checks 9, 10, 11, 12 exactly as v1.2.0 specified. **Check 13 (AUTO immutability) — corrected predicate:** instead of "AUTO block changed AND no source file in `IMPLEMENTATION_SPEC` was modified → fail," use "AUTO block changed AND the current `compute_state_marker()` output equals the state hash recorded in the previously committed MAPA's `**State Hash:**` line → fail." This reuses Task 6-2's state-hash function as the single definition of "legitimate reason to change," instead of maintaining a second, narrower file-list that only covers `IMPLEMENTATION_SPEC` entries and would false-fail on ordinary `data/*.json`, satellite `.md`, or `tests/*.py` changes. **Check 14 (NEW, informational, non-blocking):** render `detect_coverage_drift()`'s output (Patch 1-P1) as a "Coverage Watch" subsection in the MAPA; does not affect `--gate-mapa` exit code. **Check 15 (NEW, informational, non-blocking):** render `check_evidence_freshness()`'s output (Patch 4-P1) as a warning banner if `warn=True`; does not affect exit code. Update the docstring at L8 to say "15 checks (13 blocking, 2 informational)" — Check 10's self-count consistency check enforces this stays accurate going forward.
- **acceptance_criteria**:
  - `python build_pipeline.py --generate-mapa --validate` runs all 15 checks, 13 of which gate the exit code
  - Regression test: touching `docs/governance/sat_operacional.md` or `data/scenarios.json` and regenerating does **not** trip Check 13 (this is the bug G3 described — verified fixed on first build, not patched afterward)
  - Regression test: hand-editing an AUTO block with no source file changed **does** trip Check 13
  - Coverage Watch and evidence-freshness warning appear in the MAPA body without affecting exit code
- **verification**: the two regression tests above, plus `rg "15 checks" build_pipeline.py`
- **rollback**: `git checkout build_pipeline.py`

### New Task 6-5 — Automated trigger: pre-commit hook + optional CI (closes G4)

- **task_id**: `6-5`
- **depends_on**: `[6-3]` (needs the corrected, non-false-positive gate before it's safe to make blocking)
- **files_touched**: `.git/hooks/pre-commit` (new, or `.pre-commit-config.yaml` if that framework is already in use — check first), `.github/workflows/mapa-gate.yml` (new, optional, only if pushed to GitHub with Actions enabled)
- **description**: `Test-Path .pre-commit-config.yaml` first — use the existing framework if present, otherwise write a plain `.git/hooks/pre-commit` that runs `python build_pipeline.py --generate-mapa --validate`, blocking the commit on non-zero exit, and `git add`-ing the regenerated `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` on success so the doc and the code that produced it are never separated by a commit boundary. If the repo has GitHub Actions available, add `.github/workflows/mapa-gate.yml` running the same gate on push/PR as the backstop for fresh clones where the local hook isn't installed (git hooks aren't versioned by git itself). Document the one-line local install step in `README.md`/`CONTRIBUTING.md`.
- **acceptance_criteria**:
  - A commit that breaks any blocking check (0-13) is rejected locally
  - If CI is wired, the same broken commit pushed with `--no-verify` is caught there too
  - A normal, gate-passing commit isn't meaningfully slower (the four Phase 4 smoke runs must stay fast — if not, log a new finding rather than skip the hook)
- **verification**: deliberately break a check, attempt commit, confirm rejection with visible gate output; revert, confirm commit succeeds and the MAPA is included automatically
- **rollback**: delete `.git/hooks/pre-commit` (or the added framework entry) and/or `.github/workflows/mapa-gate.yml`

---

## Section 5 — Postconditions

- **AQ0** — Two consecutive `--generate-mapa` runs against unchanged inputs are byte-identical (this is the parent plan's Q7, now actually achievable — v1.2.0's own wording of Q7 would have failed under the unamended Task 6-2)
- **AQ1** — Ordinary changes to `data/*.json`, satellite `.md` files, or `tests/*.py` never trip Check 13; hand-edited AUTO blocks with no source change always do
- **AQ2** — A gate-breaking commit is rejected before landing, locally and/or in CI
- **AQ3** — Coverage Watch (Check 14) and evidence-freshness warning (Check 15) render correctly and never affect `--gate-mapa`'s exit code
- **AQ4** — All of the parent plan's own Q0-Q6, Q8, Q9 still hold unchanged (this addendum only touches Q7's mechanism, not its meaning)

---

## Section 6 — Risk Register (residual)

| Risk ID | Description | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| AR1 | `compute_state_marker()` insensitive to a real change (false idempotency) | LOW | MEDIUM | Task 6-2's two-part acceptance criteria (same-input→same-hash, changed-input→different-hash) as a permanent regression test |
| AR2 | Pre-commit hook bypassed via `--no-verify`, no CI wired | MEDIUM | MEDIUM | Accept as documented residual risk of a local-only workflow if CI genuinely isn't available |
| AR3 | `covers` field (Patch 2-P1) drifts from what a predicate actually checks | LOW | LOW | Non-blocking by design — worst case is a missed informational note, never a false pass on something safety-critical |
| AR4 | Check 15's "10 consecutive" threshold is arbitrary | LOW | LOW | Tune after observing real regeneration cadence; not worth over-designing pre-data |

---

## Section 7 — Anti-Regression Properties (final count: 13 blocking + 2 informational)

Checks 0-12 as in parent plan v1.2.0. Check 13 built correctly from the start per Amended Task 6-3 (no separate "Check 14 fixes Check 13" needed — this is the entire point of correcting the task before it's executed rather than after). Check 14 (Coverage Watch) and Check 15 (evidence freshness) are informational, non-blocking, added by Patches 1-P1/4-P1 + Amended Task 6-3's rendering.

---

## Section 8 — Acceptance Criteria (Holistic)

1. Patches 1-P1, 2-P1, 4-P1 land with their own acceptance criteria met, independent of Phase 6's timing.
2. Phase 6 is executed using this document's Amended Task 6-2/6-3 and New Task 6-5 — never the original v1.2.0 text for those task IDs — and v1.2.0's Task 6-4 is skipped entirely, not executed in any form.
3. AQ0-AQ4 all hold simultaneously.
4. The parent plan's Section 8 holistic criteria hold, minus any criterion specifically about shadow-mode migration status — that concept is dropped by this addendum, and its regression-safety purpose is already covered by Task F-1's own delta-diff against `.orig-bak`.

---

## Section 9 — Explicit Non-Goals

- **NO** reopening Phase 0-zero, 0a, 0b, 0c, 2, 3, or 5.
- **NO** making live-evidence capture mandatory (Check 15 monitors `--no-live-evidence`, doesn't remove it).
- **NO** turning Check 14 (coverage watch) into a blocking check — that's a future human decision, not this addendum's call.

---

## Section 10 — Handoff Notes for Executing Agent

1. **Run Patches 1-P1, 2-P1, 4-P1 whenever convenient** — they have zero dependency on Phase 6 and can land today.
2. **When you reach Phase 6, use Section 4 of this document instead of v1.2.0's original Task 6-2/6-3 text.** Task 6-1 is unchanged — execute it exactly as v1.2.0 specifies.
3. **Do not build Task 6-3's Check 13 narrow, then widen it.** Amended Task 6-3 already specifies the correct predicate — building it "the easy way" first and fixing it after defeats the entire purpose of catching this before implementation.
4. **Skip v1.2.0's Task 6-4 outright when you reach it.** It is not amended, not deferred, not replaced by a like-for-like mechanism — its regression-safety goal is already met by Task F-1's delta-diff against `.orig-bak`, unchanged from v1.2.0.
