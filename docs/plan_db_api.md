---
plan_id: plan-gsd-fdc-nutrient-fix
title: "GSD Raw Calculator — USDA FDC ID Correction + Resolution Pipeline Hardening"
version: 2.3.0
status: ready_for_execution
sequenced_after: plan-mapa-generator-fix v1.2.0 (MUST be complete and merged before Task-0)
path_convention: repo_root (NOT upload/ — see "Path Reconciliation" in Context Boundary)
v2_3_holistic_review: 15 findings across 4 specialist perspectives (SWE/DataAnalyst/DataScraper/AI-to-AI). 5 BLOCKING: S1 (missing requests), S2 (resolved DB never loaded), S3 (relative input path), DS2 (missing --probe step), A1 (Task-8 false premise — DB swap missing). See Section 13 for full findings matrix.
target_agent_profile:
  type: senior_swe_agent
  required_capabilities:
    - python_execution
    - json_editing
    - http_api_calls
    - git_operations
    - pytest_execution
  forbidden_actions:
    - modify files outside the listed paths
    - skip precondition checks
    - merge commits without verification
repo:
  root: $PROJECT_ROOT   # RESOLVED AT RUNTIME by Task-0 below — do not assume a
                        # literal value. v1.0.0 hardcoded /home/z/my-project,
                        # which does not exist on this machine (actual project
                        # is at C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\).
                        # v2.1.0 makes this self-detecting instead of guessing a
                        # second hardcoded value, because the execution
                        # environment (OpenCode Desktop on Windows) has a known,
                        # currently-open bug where the shell it spawns commands in
                        # — WSL bash, Git Bash, or PowerShell/cmd.exe — can vary
                        # between individual tool calls, not just once per machine
                        # (see Task-0 for details and citation).
  upload_dir: $PROJECT_ROOT/upload
  scripts_dir: $PROJECT_ROOT/scripts
  tests_dir: $PROJECT_ROOT/tests
  base_commit: 9cc61eb32cd3070e33badcb6598789fd68fafcfa
  working_branch: fix/usda-fdc-and-pipeline-hardening
total_tasks: 9   # was 7 in v1.0.0 — Task-0 (env/path resolution) and Task-1B
                 # (FDC integrity checkpoint) added
parallel_groups: 1   # only Phase-1 FDC lookup is parallelizable
created: 2026-07-16T08:31:44Z
updated: 2026-07-16T16:20:00Z
language: en   # v2.0.0: translated from pt-BR. Code identifiers, JSON keys, regex,
               # paths, commit messages, source_refs, and display_name fields were
               # NEVER in Portuguese to begin with in v1.0.0 and remain unchanged.
               # Only prose (objectives, step narration, rationale, risk register,
               # changelog) was translated. See "Translation Notes" at the end.
---

# Plan: GSD Raw Calculator — USDA FDC ID Correction + Pipeline Hardening

## Objective

Restore the integrity of the clinical raw-diet-formulation pipeline for GSD.
Concretely: (1) correct 20/23 incorrect FDC IDs in `DB_ingredientes.json`,
(2) fix 4 schema/semantic defects in `resolve_usda_nutrients.py` and
`build_pipeline.py`, (3) re-run USDA resolution over the corrected FDCs, and
(4) prove with tests that the pipeline is intact before a single commit goes
to `master`.

## Preconditions (plan-level — MUST hold before Task-1)

| ID | Condition | Verification command |
|---|---|---|
| P-PLAN-A | Plan A (MAPA generator fix v1.2.0) is complete and merged to `main` | `cd $PROJECT_ROOT && git log --oneline main \| head -20` shows Plan A's commits; `ls $PROJECT_ROOT/doc_introspector.py` exits 0; `ls $PROJECT_ROOT/tests/reference_cases.py` exits 0; `rg -c "SOURCE: IMPLEMENTATION_SPEC" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` returns `>= 10` |
| P0 | Clean working tree at repo root (NOT `upload/`) | `cd $PROJECT_ROOT && git status --short \| wc -l` → `0` |
| P1 | Working branch created from `main` (after Plan A merge) | `git rev-parse --abbrev-ref HEAD` → `fix/usda-fdc-and-pipeline-hardening` |
| P2 | USDA API key available as env var | `echo $USDA_API_KEY` → non-empty |
| P3 | `jsonschema`, `pytest`, `requests`, and `pulp` installed | `python -c "import jsonschema, pytest, requests, pulp; print('ok')"` → exit 0. **S1 FIX (v2.3):** `resolve_usda_nutrients.py` imports `requests` at L48, but `requirements.txt` only lists `jsonschema` and `pulp==3.3.2`. Task-S1 (new) adds `requests` to `requirements.txt` before any task that imports the resolver. |
| P4 | Backup of original DB exists | `ls $PROJECT_ROOT/download/DB_ingredientes.backup_pre_fix.json` → exit 0 |
| P5 | Python ≥ 3.10 | `python --version` → `3.10+` |
| P6 | `resolve_usda_nutrients.py` exists at repo root (or known location) | `ls $PROJECT_ROOT/resolve_usda_nutrients.py` exits 0 — **if this fails, see "resolve_usda_nutrients.py Location" in Context Boundary before proceeding** |
| P7 | Plan A's 32-test baseline still green (post-Plan-A merge) | `cd $PROJECT_ROOT && python -m pytest tests/ -q` → `32 passed` (or `33+` if Plan A added new tests) |

If any precondition fails, **STOP** and report the blocker — do not attempt to
auto-fix preconditions.

**P-PLAN-A is the gating precondition.** This plan (v2.2.0) is sequenced AFTER
`plan-mapa-generator-fix` v1.2.0. Plan A modifies `build_pipeline.py` at four
sites (L421-434, L1194-1207, L2857, L3061-3063) which shifts every line number
in this plan by +5 to +20 lines. **All line numbers in this plan are PRE-Plan-A
baselines from the v2.1.0 draft.** After Plan A lands, the executing agent MUST
re-locate every target by content (function name + signature), NOT by line
number. See "Line Number Caveat" in Context Boundary.

## Postconditions (plan-level — MUST hold after Task-8)

| ID | Condition | Verification command |
|---|---|---|
| Q0 | 23/23 FDC IDs validated against the USDA API return the expected description (species + tissue) | `python $PROJECT_ROOT/scripts/validar_fdc_rigoroso.py` → `MATCH total: 23/23` |
| Q0B | FDC IDs are byte-identical to Task-1's committed output (nothing reverted them in Tasks 2–6) | see Task-7 Step 0 below |
| Q1 | `jsonschema.validate` passes on the resolved DB | `python -c "import json, jsonschema; ..."` → exit 0 |
| Q2 | `pytest test_dimensional_pipeline.py` passes | `pytest -q tests/test_dimensional_pipeline.py` → exit 0 |
| Q3 | No USDA `source_ref` has a lowercase letter outside the pattern | `python scripts/check_source_refs.py` → `0 violations` |
| Q4 | `vitamin_a_iu` is `not_applicable` only where the ingredient's own `category` field says it should be (see Task-4 rewrite) | audit script returns `0 mismatches vs. category field` |
| Q5 | `coverage_excluded_nutrients` is not mutated by `resolve_usda_nutrients.py` | `rg "^[^#]*excluded_list\\.remove" $PROJECT_ROOT/resolve_usda_nutrients.py` → `0 matches` |
| Q6 | Clean git working tree after final commit | `git status --short` → empty |
| Q7 | MAPA regenerated with corrected nutrient data (closes stale-evidence gap from Task-7 DB regeneration) | `cd $PROJECT_ROOT && python build_pipeline.py --generate-mapa --out MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md && rg -c "SOURCE: IMPLEMENTATION_SPEC" MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` → `>= 10`; plus live-evidence shows `solver_status: optimal` against corrected FDCs — see Task-8 |

## Context Boundary

**The executing agent MAY read:**
- `$PROJECT_ROOT/data/DB_ingredientes.json`
- `$PROJECT_ROOT/data/db_ingredientes.schema.json`
- `$PROJECT_ROOT/resolve_usda_nutrients.py` (see "resolve_usda_nutrients.py Location" below)
- `$PROJECT_ROOT/build_pipeline.py` (post-Plan-A — already modified by Plan A v1.2.0)
- `$PROJECT_ROOT/tests/test_dimensional_pipeline.py`
- `$PROJECT_ROOT/tests/test_cascade_integration.py` (modified by Plan A — imports from `tests/reference_cases.py`)
- `$PROJECT_ROOT/tests/reference_cases.py` (created by Plan A — exports REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID)
- `$PROJECT_ROOT/doc_introspector.py` (created by Plan A — IMPLEMENTATION_SPEC, ImplIntrospector, capture_live_evidence, scrub_volatile)
- `$PROJECT_ROOT/data/lp_parameters_data.json`
- `$PROJECT_ROOT/data/toxicological_limits.json`
- `$PROJECT_ROOT/scripts/validacao_evidencia.py` (evidence already collected)
- `$PROJECT_ROOT/scripts/validar_fdc_rigoroso.py` (evidence already collected)

**The executing agent MAY NOT:**
- Modify files under `$PROJECT_ROOT/data/` except `DB_ingredientes.json` (Task-1)
  and `DB_ingredientes_RESOLVIDO.json` (Task-7, written to `scripts/`)
- Modify `$PROJECT_ROOT/doc_introspector.py` or `$PROJECT_ROOT/tests/reference_cases.py` (owned by Plan A)
- Skip ahead to a task whose `depends_on` is not yet `completed`
- Reuse the current `DB_ingredientes_RESOLVIDO.json` (it was generated against
  incorrect FDCs and MUST be regenerated after Task-1)
- Delete or overwrite `$PROJECT_ROOT/download/DB_ingredientes.backup_pre_fix.json`
- Run `git push --force` or `git rebase -i` over other tasks' commits
- Touch Plan A's provenance markers (`<!-- SOURCE: IMPLEMENTATION_SPEC ... -->`)
  in `build_pipeline.py` or `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` — Task-3 and
  Task-5 edit disjoint regions, but verify with `rg "SOURCE: IMPLEMENTATION_SPEC"
  build_pipeline.py` before and after each edit to confirm zero markers moved

### Path Reconciliation (v2.2.0 — CRITICAL)

**v2.1.0 used `upload/` paths throughout.** The `upload/` directory was a
snapshot uploaded for analysis — it is NOT the live repo. The live repo (per
GitHub canonical structure) uses:

| v2.1.0 path (WRONG) | v2.2.0 path (CORRECT) | Notes |
|---|---|---|
| `$PROJECT_ROOT/build_pipeline.py` | `$PROJECT_ROOT/build_pipeline.py` | Repo root |
| `$PROJECT_ROOT/data/DB_ingredientes.json` | `$PROJECT_ROOT/data/DB_ingredientes.json` | `data/` subdirectory |
| `$PROJECT_ROOT/data/db_ingredientes.schema.json` | `$PROJECT_ROOT/data/db_ingredientes.schema.json` | `data/` subdirectory |
| `$PROJECT_ROOT/resolve_usda_nutrients.py` | `$PROJECT_ROOT/resolve_usda_nutrients.py` | See note below — file may not exist in repo |
| `$PROJECT_ROOT/tests/test_dimensional_pipeline.py` | `$PROJECT_ROOT/tests/test_dimensional_pipeline.py` | `tests/` at repo root |
| `$PROJECT_ROOT/data/lp_parameters_data.json` | `$PROJECT_ROOT/data/lp_parameters_data.json` | `data/` subdirectory |
| `$PROJECT_ROOT/data/toxicological_limits.json` | `$PROJECT_ROOT/data/toxicological_limits.json` | `data/` subdirectory |
| `$PROJECT_ROOT/data/scenarios.json` | `$PROJECT_ROOT/data/scenarios.json` | `data/` subdirectory |
| `$PROJECT_ROOT/data/constraints.json` | `$PROJECT_ROOT/data/constraints.json` | `data/` subdirectory |

**Every path in every task below has been updated to the repo-root convention.**
If you find a stray `upload/` reference, treat it as a bug and substitute the
correct repo-root path from the table above.

### resolve_usda_nutrients.py Location (v2.2.0 — BLOCKING)

**`resolve_usda_nutrients.py` does NOT exist in the GitHub repo** (verified by
`find . -name "resolve_usda*"` against the clone returning zero matches). It
was uploaded as `upload/resolve_usda_nutrients (1).py` (note the space and
"(1)" suffix — a browser download artifact).

Before Task-2 can run, the executing agent MUST:
1. Confirm the file exists on the user's Windows machine at
   `C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\resolve_usda_nutrients.py`
2. If it does NOT exist there, copy it from the uploaded snapshot:
   ```bash
   cp "$PROJECT_ROOT/resolve_usda_nutrients.py" \
      "$PROJECT_ROOT/resolve_usda_nutrients.py"
   git add resolve_usda_nutrients.py
   git commit -m "chore: add resolve_usda_nutrients.py to repo (was missing from GitHub)"
   ```
3. If it DOES exist but under a different name (e.g. `resolve_usda_nutrients_v2.py`),
   use the actual filename and substitute throughout this plan.
4. **Do NOT proceed with Task-2/4/6 until this file is at a known repo-root path.**
   These three tasks modify it in place; a wrong path = silent no-op.

### Raw DB vs Resolved DB Clarification (v2.3.0 — D1 FIX)

**D1 FINDING:** The raw `data/DB_ingredientes.json` has ZERO instances of
`_MCGxIU` or `_MCGXIU` in its `source_ref` fields. The raw DB uses clean
`REF_USDA_FDC_<id>` tokens (23 unique FDC IDs). The `_MCGxIU`/`_MCGXIU` suffix
is ADDED by `resolve_usda_nutrients.py` during RAE→IU vitamin A conversion —
it only exists in the RESOLVED DB (output of the resolver).

**Consequence for Plan B:**
- Task-2 (fix `_MCGxIU` → `_MCGXIU`) modifies the RESOLVER CODE (`resolve_usda_nutrients.py` L383), NOT the raw DB. This is correct.
- Task-3 (add SourceRef regex validation in `validate_inputs`) — the regex `^REF_[A-Z0-9_]+$` would REJECT any `source_ref` containing `_MCGxIU` (lowercase x). But since the raw DB doesn't have this suffix, Task-3's check passes on the raw DB today. It only matters after Task-7B swaps in the resolved DB.
- Q3 ("0 source_ref violations") — this postcondition applies to the RESOLVED DB (after Task-7B swap), NOT the raw DB. The raw DB already passes Q3 trivially.
- **S4 FINDING (positive):** `--generate-mapa` calls `validate_mapa()` (Plan A's 13-check gate), NOT `validate_inputs()`. So Task-3's regex check does NOT affect MAPA generation. It only affects `--runtime` mode (L3363). This means Plan B Task-3 cannot break Plan A's MAPA pipeline — they're decoupled.

**DS1 FINDING (positive):** `resolve_usda_nutrients.py` already has rate limiting and retry logic built in:
- `THROTTLE_SECONDS = 0.2` (200ms between successful calls)
- `MAX_RETRIES = 4` (exponential backoff on 429/5xx)
- `BASE_BACKOFF = 1.5` (seconds, grows exponentially)
- `REQUEST_TIMEOUT = 15` (per-request timeout)

Plan B does NOT need to add rate limiting — the script is already hardened.
But the executing agent should expect ~5 seconds of total API time for 23
ingredients (23 × 0.2s throttle + actual request time).

### Line Number Caveat (v2.2.0 — CRITICAL)

**All line numbers in Tasks 3 and 5 are PRE-Plan-A baselines.** Plan A v1.2.0
modifies `build_pipeline.py` at four sites:

| Plan A site | Approximate line shift | Affected Plan B targets |
|---|---|---|
| L421-434 (`section1_header` sentinel fix) | +3 to +8 lines | Shifts everything below L434 |
| L1194-1207 (`impl_gaps` to `ImplIntrospector` loop) | +8 to +15 lines (loop is bigger than the 7-tuple literal) | Shifts everything below L1207, including Plan B's `validate_inputs` (L1434 to ~L1449) and `convert_as_fed_to_energy_normalized` (L1655 to ~L1670) |
| L2857 (`_unrounded_total_g` addition) | +1 to +3 lines | Shifts everything below L2857 (no Plan B targets below this) |
| L3061-3063 (`validate_output` envelope fix) | ±0 lines (in-place modification) | No shift |

**Net effect on Plan B targets (post-Plan-A):**

| Plan B target | v2.1.0 claimed line | Actual pre-Plan-A line | Estimated post-Plan-A line | How to find it |
|---|---|---|---|---|
| `validate_inputs` function (Task 3) | L1387 | L1434 | ~L1449-1454 | `rg -n "def validate_inputs" build_pipeline.py` |
| SourceRef orphan-check block (Task 3) | L1411-1419 | ~L1458-1466 | ~L1473-1481 | `rg -n "non-USDA source_refs resolve in audit_provenance" build_pipeline.py` |
| `convert_as_fed_to_energy_normalized` (Task 5) | L1629 | L1655 | ~L1670-1675 | `rg -n "def convert_as_fed_to_energy_normalized" build_pipeline.py` |
| AAFCO recompute block `met_val = ...` (Task 5) | L1652-1671 | L1700+ | ~L1715-1735 | `rg -n "met_val = get_measured_value" build_pipeline.py` |

**The executing agent MUST re-locate each target by content (function name /
signature / distinctive comment) using `rg`, NOT by line number.** The line
numbers in this plan are orientation aids only, not patch coordinates.

## Tasks

<!--
Graph convention:
  - depends_on: list of task_ids that MUST be in `completed` status
  - parallel_group: tasks in the same group may run concurrently IF their
    `files_mutated` are disjoint
  - Each task = exactly 1 commit
  - Commit message follows Conventional Commits: `fix(scope): description`
-->

---

### Task-S1: Add `requests` to requirements.txt (NEW in v2.3.0 — S1 FIX)

```yaml
task_id: task-s1
title: "Add missing 'requests' dependency to requirements.txt"
depends_on: []
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/requirements.txt
idempotent: true
estimated_loc: 1
commit_message: "fix(deps): add requests to requirements.txt (required by resolve_usda_nutrients.py)"
severity: blocker
```

**Rationale (S1 FIX — BLOCKING):** `resolve_usda_nutrients.py` imports `requests`
at L48, but `requirements.txt` only lists `jsonschema` and `pulp==3.3.2`. Without
this fix, Tasks 2, 4, 6, and 7 all fail with `ImportError: No module named 'requests'`
the moment they import the resolver. The package IS installed in the current
environment (verified: `requests==2.32.5`), but it's not declared in
`requirements.txt` — so a fresh clone would break.

**Preconditions:**
- P0–P7 satisfied (especially P-PLAN-A: Plan A merged)

**Steps:**

1. Open `$PROJECT_ROOT/requirements.txt`
2. Current content:
   ```
   jsonschema
   pulp==3.3.2
   ```
3. Add `requests` (pin to a reasonable minimum, e.g. `>=2.28` for the
   retry/timeout features `resolve_usda_nutrients.py` relies on):
   ```
   jsonschema
   pulp==3.3.2
   requests>=2.28
   ```
4. Verify the import works in a clean subprocess:
   ```bash
   python -c "import requests; print(f'requests {requests.__version__} OK')"
   ```
   Expected: `requests 2.28+ OK`

**State mutations:**

| File | Before | After |
|---|---|---|
| `requirements.txt` | 2 lines (`jsonschema`, `pulp==3.3.2`) | 3 lines (+ `requests>=2.28`) |

**Verification:**

```bash
# V1: requests is in requirements.txt
rg "^requests" $PROJECT_ROOT/requirements.txt
# expected: 1 match

# V2: import works
python -c "import requests; print('ok')"
# expected exit: 0
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/requirements.txt
```

---

### Task-0: Resolve execution environment and $PROJECT_ROOT (NEW in v2.1.0)

```yaml
task_id: task-0
title: "Detect shell/platform and resolve $PROJECT_ROOT before any other task runs"
depends_on: []
parallel_group: null
files_mutated: []   # detection only, no repo files touched
idempotent: true
estimated_loc: ~15
commit_message: null   # this task does not commit anything
severity: blocker
```

**Why this task exists:** the actual project lives at
`C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\` on Windows, not at any
Linux-style path. Separately, and more importantly: the execution environment
here is OpenCode Desktop on Windows, which has a documented, currently-open
issue where the shell it spawns commands in — WSL bash, Git Bash, or
PowerShell/cmd.exe — is selected per-command based on what's in `PATH` at
spawn time, **not fixed once per session** (OpenCode GitHub issue #8396:
*"Desktop app always uses SHELL (WSL) on Windows"*; issue #5557 confirms users
observe it flip between WSL and PowerShell mid-session unpredictably). This
means a path or command style that works in one step of this plan can silently
fail two steps later if the underlying shell changed. Do not assume the shell
identified now stays constant for the rest of the plan.

**Steps:**

1. **Recommend, before starting: pin the shell explicitly**, outside of this
   plan, by setting the `SHELL` environment variable for the OpenCode process
   (Git Bash is the safer pick over WSL here, since Git Bash sees the Windows
   filesystem directly rather than through WSL's `/mnt/c/` translation layer,
   and the current known bug specifically defaults to WSL when a Git-Bash-path
   override is set but ignored). This is a one-time fix outside the agent's
   control within this plan — if it wasn't done, proceed to step 2 regardless
   and re-check at the start of every subsequent task.

2. **Detect what shell is actually running right now:**
   ```bash
   # If this succeeds, we're in a POSIX-like shell (WSL bash or Git Bash)
   uname -s 2>/dev/null && echo "POSIX_SHELL_CONFIRMED"
   ```
   If this does NOT print `POSIX_SHELL_CONFIRMED`, the current shell is
   PowerShell or cmd.exe, not bash. **STOP.** This entire plan is authored in
   bash-style commands (`rg`, `cp`, `rm -f`, heredocs). Do not attempt to
   auto-translate individual commands to PowerShell/cmd.exe syntax as you go —
   that is a much larger, error-prone scope change. Report back to the user
   that the plan requires a bash-compatible shell (WSL or Git Bash) and ask
   them to switch OpenCode's configured shell before proceeding.

3. **If POSIX-confirmed, resolve `$PROJECT_ROOT` by trying both plausible
   forms of the known Windows path, in order, and using whichever exists:**
   ```bash
   _CANDIDATE_GITBASH="C:/Users/Straube/Documents/Hans-GSD-Raw-Calculator"
   _CANDIDATE_WSL="/mnt/c/Users/Straube/Documents/Hans-GSD-Raw-Calculator"

   if [ -d "$_CANDIDATE_GITBASH" ]; then
     export PROJECT_ROOT="$_CANDIDATE_GITBASH"
     echo "OK: resolved via Git Bash-style path: $PROJECT_ROOT"
   elif [ -d "$_CANDIDATE_WSL" ]; then
     export PROJECT_ROOT="$_CANDIDATE_WSL"
     echo "OK: resolved via WSL-mount-style path: $PROJECT_ROOT"
   else
     echo "ERROR: could not find the project at either candidate path. Stop and ask the user to confirm the exact path." >&2
     exit 1
   fi
   ```

4. **Re-run this exact detection snippet (steps 2–3) at the START of every
   subsequent task in this plan, before running that task's own commands** —
   do not assume a `PROJECT_ROOT` exported in one tool call persists into the
   next, given the shell can change between calls per the cited bug. This is
   cheap (a few lines, sub-second) and removes an entire class of "works here,
   fails two steps later" failure.

5. Once `PROJECT_ROOT` is resolved for the current task, every path elsewhere
   in this plan written as `$PROJECT_ROOT/...` should be read literally as
   that shell variable — substitute it exactly as the detection snippet set
   it, do not re-derive a different path style mid-task.

**Verification:**

```bash
# V1: PROJECT_ROOT is set and points at a real directory
[ -n "$PROJECT_ROOT" ] && [ -d "$PROJECT_ROOT" ] && echo "OK: $PROJECT_ROOT"
# expected: prints OK and a real path, exit 0

# V2: the expected data/ and scripts/ subdirectories exist under it
[ -d "$PROJECT_ROOT/data" ] && [ -d "$PROJECT_ROOT/tests" ] && [ -d "$PROJECT_ROOT/scripts" ] && echo "OK: expected subdirs present"
# expected exit: 0 — if this fails, PROJECT_ROOT resolved to the wrong
# directory even though it exists; stop and report rather than continuing
```

**Rollback:** none needed — this task makes no repo changes.

---

### Task-1: Correct 20 incorrect FDC IDs in DB_ingredientes.json

```yaml
task_id: task-1
title: "Correct 20 misaligned FDC IDs in DB_ingredientes.json"
depends_on: []
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/data/DB_ingredientes.json
  - $PROJECT_ROOT/scripts/corrigir_fdc_ids.py   # new
  - $PROJECT_ROOT/scripts/validar_fdc_rigoroso.py   # reused
idempotent: false   # re-running without a revert only produces duplicate log entries
estimated_loc: ~260   # +10 vs v1.0.0 for the tie-break rule and sanity cross-check
commit_message: "fix(db): correct 20 misaligned USDA FDC IDs across protein sources"
severity: blocker
```

**Preconditions (in addition to plan-level):**
- P0–P5 satisfied
- Backup `DB_ingredientes.backup_pre_fix.json` already created

**Steps:**

1. **Create `$PROJECT_ROOT/scripts/corrigir_fdc_ids.py`** with the
   following logic:
   - For each ingredient in `protein_sources.{bovinos,aves,suinos,peixes,fat_sources}.ingredients`:
     - Read `metadata.usda_fdc_id`, `ingredient_id`, and `display_name`
     - Call `GET https://api.nal.usda.gov/fdc/v1/foods/search?api_key=$USDA_API_KEY&query=<search_term>&dataType=Foundation,SR%20Legacy&pageSize=10`
     - `search_term` derived from `ingredient_id`: replace `_` with a space,
       e.g. `beef_muscle_raw` → `beef muscle raw`, `chicken_foot_tendon_raw` →
       `chicken foot raw`
     - For each of the top-10 results, compute a similarity score:
       - +2 if the expected species appears in `description` (beef/chicken/pork/salmon)
       - +2 if the expected tissue appears (muscle/lung/heart/liver/kidney/spleen/
         tongue/blood/tripe/tail/foot/fat)
       - +1 if "raw" appears (we prefer raw data)
       - +1 if `dataType == "Foundation"` (Foundation preferred over SR Legacy)
       - −5 if the description contains "cooked", "cured", "cereal", "bacon",
         "luncheon", or "mechanically separated"
     - Rank the candidates.
     - **Tie-break rule (NEW in v2.0.0 — was unspecified in v1.0.0):** if two or
       more top-ranked candidates share the identical score, do NOT auto-select
       either, even in `--auto-approve` mode. Force manual review for that
       ingredient specifically, and log it distinctly in
       `fdc_id_migration.log` as `TIE_REQUIRES_REVIEW: <ingredient_id>` with all
       tied candidates listed. Rationale: a coarse integer scoring scheme
       (7 possible outcomes) over 10 candidates makes ties a real, not
       theoretical, occurrence — silently picking "the first one returned by
       the API" is an unspecified decision an agent should never make on your
       behalf for a food-safety-relevant lookup.
     - Present the top-3 to the operator (or accept the top-1 in
       `--auto-approve` mode, subject to the tie-break rule above and the
       sanity cross-check below)
     - Update `metadata.usda_fdc_id` in the in-memory DB
   - **Sanity cross-check before accepting any swap (NEW in v2.0.0):** after
     selecting a candidate FDC ID, fetch its full nutrient panel and compare
     `protein_g` and `fat_g` against the ingredient's EXISTING (pre-fix)
     measured values in `DB_ingredientes.json`. If either differs by more than
     ±30%, do NOT auto-accept — flag as
     `SANITY_CHECK_FAILED: <ingredient_id> (existing protein=X, candidate=Y)`
     in the migration log and require manual confirmation regardless of the
     text-similarity score. Rationale: a keyword-based text match can still
     select the wrong species/cut/preparation (e.g. veal mislabeled generically
     as "beef" in some USDA descriptions); an independent numeric sanity check
     against data already trusted in the DB catches this class of error that
     text matching alone cannot.
   - Save the modified DB to `data/DB_ingredientes.json` (overwrite)
   - Write a change log to `download/fdc_id_migration.log`

2. **Back up before mutating:**
   ```bash
   cp $PROJECT_ROOT/data/DB_ingredientes.json \
      $PROJECT_ROOT/download/DB_ingredientes.backup_pre_fix.json
   ```

3. **Run the script in interactive mode:**
   ```bash
   python $PROJECT_ROOT/scripts/corrigir_fdc_ids.py --mode interactive
   ```
   For each of the 20 incorrect ingredients (per evidence:
   `pork_liver_raw`, `salmon_atlantic_raw`, `pork_muscle_raw`,
   `chicken_muscle_raw`, `chicken_heart_raw`, `chicken_kidney_raw`,
   `chicken_foot_tendon_raw`, `chicken_blood_raw`, `chicken_liver_raw`,
   `beef_muscle_raw`, `beef_lung_raw`, `beef_foot_tendon_raw`,
   `beef_tail_raw`, `beef_tongue_raw`, `beef_blood_raw`, `beef_heart_raw`,
   `beef_green_tripe_raw`, `beef_liver_raw`, `beef_kidney_raw`,
   `beef_spleen_raw`), manually confirm the top-1 or select from top-2/3.

4. **Do NOT touch the 3 correct fat_sources** (FDC 170193, 171468, 167813).

5. **Re-run rigorous validation:**
   ```bash
   python $PROJECT_ROOT/scripts/validar_fdc_rigoroso.py
   ```
   Expected output: `MATCH total: 23/23`. If ≠ 23/23, **DO NOT commit** —
   go back to step 3 and refine the search.

**State mutations:**

| File | Before | After |
|---|---|---|
| `data/DB_ingredientes.json` | 20 incorrect FDC IDs in `metadata.usda_fdc_id` | 23/23 correct FDC IDs |
| `scripts/corrigir_fdc_ids.py` | does not exist | ~260 LOC |
| `download/fdc_id_migration.log` | does not exist | auditable log of every change, including ties and sanity-check failures |

**Verification (deterministic):**

```bash
# V1: 23/23 API matches
python $PROJECT_ROOT/scripts/validar_fdc_rigoroso.py 2>&1 | grep "MATCH total" | grep "23/23"
# expected exit: 0

# V2: JSON is still valid
python -c "import json; json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json'))"
# expected exit: 0

# V3: schema still passes (before re-resolution)
python -c "import json, jsonschema; db=json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json')); schema=json.load(open('$PROJECT_ROOT/data/db_ingredientes.schema.json')); jsonschema.validate(db, schema)"
# expected exit: 0

# V4: all 23 ingredients still present
python -c "import json; db=json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json')); n=sum(len(s.get('ingredients',[])) for s in db['protein_sources'].values() if isinstance(s,dict)); assert n==23, n; print('OK', n)"
# expected exit: 0

# V5 (NEW): zero unresolved ties or sanity-check failures remain in the log
grep -E "TIE_REQUIRES_REVIEW|SANITY_CHECK_FAILED" $PROJECT_ROOT/download/fdc_id_migration.log
# expected exit: 1 (no matches) — every flagged case from step 1 must be
# manually resolved and re-logged as RESOLVED before this task can be committed
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/data/DB_ingredientes.json
# or, if already committed:
git revert <task-1-commit-sha>
```

**Anti-patterns to avoid in this task:**
- Do NOT use `--auto-approve` without human review on the first 3 ingredients
  (risk of selecting the wrong FDC by textual coincidence)
- Do NOT rely on the Portuguese `display_name` to build `search_term` — always
  use the English `ingredient_id`
- Do NOT update the FDCs of the 3 fat_sources (170193, 171468, 167813) — they
  are already correct and any change risks a regression
- Do NOT silently resolve a tie or a failed sanity check by picking the
  higher-ranked candidate anyway — both require an explicit human decision
  logged in `fdc_id_migration.log`

---

### Task-1B: FDC integrity checkpoint (NEW in v2.0.0)

```yaml
task_id: task-1b
title: "Snapshot Task-1's corrected FDC IDs as an integrity baseline"
depends_on:
  - task-1
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/download/fdc_ids_post_task1.snapshot.json   # new, read-only after creation
idempotent: true
estimated_loc: ~10
commit_message: "chore(audit): snapshot corrected FDC IDs as integrity baseline for Task-7"
severity: medium
```

**Rationale:** in v1.0.0, FDC-ID correctness was only re-verified at the very
end (post Task-7, via Q0). If any of Tasks 2–6 accidentally reverted or
corrupted an FDC ID (e.g. via an unrelated `git checkout` of the wrong file,
or a bad merge), that failure would surface only after Task-7's expensive
USDA re-resolution — expensive to bisect. This task creates a cheap baseline
snapshot immediately after Task-1, so Task-7 can do a fast byte-identical
diff before doing anything else.

**Steps:**

1. After Task-1 is committed, extract just the FDC IDs:
   ```python
   import json
   db = json.load(open("$PROJECT_ROOT/data/DB_ingredientes.json"))
   snapshot = {}
   for cat_name, cat_data in db["protein_sources"].items():
       for ing in cat_data.get("ingredients", []):
           snapshot[ing["ingredient_id"]] = ing["metadata"]["usda_fdc_id"]
   json.dump(snapshot, open("$PROJECT_ROOT/download/fdc_ids_post_task1.snapshot.json", "w"), indent=2, sort_keys=True)
   ```

**Verification:**

```bash
# V1: snapshot has exactly 23 entries
python -c "import json; s=json.load(open('$PROJECT_ROOT/download/fdc_ids_post_task1.snapshot.json')); assert len(s)==23, len(s); print('OK', len(s))"
```

**Rollback:**

```bash
rm $PROJECT_ROOT/download/fdc_ids_post_task1.snapshot.json
git revert <task-1b-commit-sha>
```

---

### Task-2: Fix source_ref suffix `_MCGxIU` → `_MCGXIU`

```yaml
task_id: task-2
title: "Fix source_ref suffix _MCGxIU -> _MCGXIU (schema compliance)"
depends_on: []
parallel_group: phase-2-quick-fixes
files_mutated:
  - $PROJECT_ROOT/resolve_usda_nutrients.py
idempotent: true
estimated_loc: 1
commit_message: "fix(resolve_usda): uppercase X in _MCGXIU suffix to comply with SourceRef pattern"
severity: medium
```

**Preconditions:**
- P0–P5 satisfied
- Task-1 is NOT a prerequisite (disjoint files)

**Steps:**

1. Open `$PROJECT_ROOT/resolve_usda_nutrients.py`
2. Locate line 383 (may vary by ±2 lines). Current content:
   ```python
   source_suffix = source_suffix or "_MCGxIU"
   ```
3. Replace with:
   ```python
   source_suffix = source_suffix or "_MCGXIU"
   ```
4. Search the whole file for other occurrences of the literal `_MCGxIU` to
   confirm the change is complete:
   ```bash
   rg "_MCGxIU" "$PROJECT_ROOT/resolve_usda_nutrients.py"
   ```
   Must return **0 occurrences** after the edit.

**State mutations:**

| File | Before | After |
|---|---|---|
| `resolve_usda_nutrients (1).py` L383 | `"_MCGxIU"` | `"_MCGXIU"` |

**Verification:**

```bash
# V1: lowercase 'x' literal is gone
rg "_MCGxIU" "$PROJECT_ROOT/resolve_usda_nutrients.py"
# expected: exit code 1 (no matches)

# V2: uppercase 'X' literal present
rg "_MCGXIU" "$PROJECT_ROOT/resolve_usda_nutrients.py"
# expected: 1 match, on the source_suffix line
```

**Rollback:**

```bash
git checkout -- "$PROJECT_ROOT/resolve_usda_nutrients.py"
```

---

### Task-3: Add SourceRef pattern validation in `validate_inputs`

```yaml
task_id: task-3
title: "Add SourceRef pattern validation in build_pipeline.validate_inputs"
depends_on: []
parallel_group: phase-2-quick-fixes
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: ~15
commit_message: "feat(build_pipeline): enforce SourceRef regex pattern in validate_inputs"
severity: medium
```

**Preconditions:**
- P0–P5 satisfied
- Task-1 is NOT a prerequisite (disjoint file)

**Steps:**

1. Open `$PROJECT_ROOT/build_pipeline.py`, locate the `validate_inputs` function
   by content: `rg -n "def validate_inputs" build_pipeline.py`. **Do NOT rely
   on the line numbers below — they are PRE-Plan-A baselines and have shifted
   by +10 to +20 lines after Plan A v1.2.0 landed.** (v2.1.0 said L1387; actual
   pre-Plan-A was L1434; post-Plan-A is ~L1449-1454.)
2. Locate the existing block that checks source_ref orphaning
   by content: `rg -n "non-USDA source_refs resolve in audit_provenance" build_pipeline.py`
   (v2.1.0 said L1411–L1419; actual pre-Plan-A ~L1458; post-Plan-A ~L1473):
   ```python
   # b) non-USDA source_refs resolve in audit_provenance
   ...
   for ... in ...:
       sr = v.get("source_ref", "")
       if not sr.startswith("REF_USDA"):
           assert sr in known_refs, ...
   ```
3. **Immediately after** this block, insert a new block `c)`:
   ```python
   # c) USDA source_refs must match the SourceRef regex pattern
   #    (closes a gap: validate_inputs did not check the pattern, only
   #    jsonschema.validate --validate-db did)
   import re
   _SOURCE_REF_PATTERN = re.compile(r"^REF_[A-Z0-9_]+$")
   for cat_name, cat_data in db.items():
       if cat_name.startswith("_"):
           continue
       if not isinstance(cat_data, dict):
           continue
       for sub_name, sub_data in cat_data.items():
           if sub_name.startswith("_") or not isinstance(sub_data, dict):
               continue
           for ing in sub_data.get("ingredients", []):
               iid = ing.get("ingredient_id", "<unknown>")
               nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
               for nkey, ndata in nuts.items():
                   if not isinstance(ndata, dict):
                       continue
                   sr = ndata.get("source_ref", "")
                   if not sr:
                       continue
                   if not _SOURCE_REF_PATTERN.match(sr):
                       raise ValueError(
                           f"{iid}.{nkey}: source_ref '{sr}' violates "
                           f"pattern '^REF_[A-Z0-9_]+$' (defined in SourceRef schema)"
                       )
   ```
4. Ensure `import re` is at the top of the file (do not duplicate if it
   already exists). Search:
   ```bash
   rg "^import re$" $PROJECT_ROOT/build_pipeline.py
   ```
   If 0 matches, add `import re` to the file's import section.

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` L1419 | Block `b)` ends without a pattern check | New block `c)` validates the regex |

**Verification:**

```bash
# V1: block c) exists in the file
rg "USDA source_refs must match the SourceRef regex" $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V2: validate_inputs rejects a DB with _MCGxIU (pre-Task-2)
python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/upload')
import json
import build_pipeline as bp
db = json.load(open('$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json'))  # old DB, with _MCGxIU
try:
    bp.validate_inputs(db, ...)
    print('FAIL: should have raised')
except ValueError as e:
    assert 'violates pattern' in str(e), str(e)
    print('OK: validate_inputs catches pattern violation')
"
# expected: 'OK: validate_inputs catches pattern violation'

# V3: validate_inputs accepts the original DB (without _MCGxIU)
python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/upload')
import json
import build_pipeline as bp
db = json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json'))
bp.validate_inputs(db, ...)  # must not raise
print('OK: original DB passes')
"
# expected exit: 0
```

> **Note on verification V2:** the old resolved DB (with `_MCGxIU`) lives at
> `$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json` and will be
> discarded. Use it ONLY for this regression test. Do not confuse it with the
> new resolved DB generated in Task-7.

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/build_pipeline.py
```

---

### Task-4: Vitamin-A policy — REWRITTEN in v2.0.0 to use the existing `category` field

```yaml
task_id: task-4
title: "Set vitamin_a_iu=0.0 to not_applicable, driven by ingredient category (not ID substring)"
depends_on: []
parallel_group: phase-2-quick-fixes
files_mutated:
  - $PROJECT_ROOT/resolve_usda_nutrients.py
idempotent: true
estimated_loc: ~30   # was ~25 in v1.0.0; +5 for the category-based branch and the
                     # explicit muscle_organ decision point
commit_message: "fix(resolve_usda): vitamin_a_iu=0.0 in non-secreting tissue is not_applicable not measured"
severity: medium
```

**Preconditions:**
- P0–P5 satisfied
- Task-1 is NOT a prerequisite

**DEPENDENCY NOTE:** this task edits the same file as Task-2.
**Therefore Task-4 is NOT parallel-safe with Task-2** — run it after Task-2
(see the explicit graph in the Task Graph section below).

**Why this was rewritten (do not re-implement the v1.0.0 substring heuristic):**

v1.0.0 classified tissue as "organ" vs. "non-organ" using a hardcoded substring
match against `ingredient_id`:
```python
_NON_ORGAN_TISSUES = ("muscle", "foot_tendon", "tongue", "heart", "blood", "fat", "tail", "tripe", "skin")
```
This is factually wrong against the DB's own data. Every ingredient already
carries a `category` field with real, distinct values (confirmed directly
against `DB_ingredientes.json`):
`muscle_organ`, `blood_source`, `fat_source`, `organ_non_secreting`, `fish`,
`organ_secreting`, `muscle_meat`, `connective_tissue`.

Concretely, `beef_heart_raw` and `beef_tongue_raw` are both categorized
`muscle_organ` — a real third bucket the binary substring heuristic cannot
represent — and `beef_green_tripe_raw` is `organ_non_secreting`, an organ that
structurally does not secrete/store vitamin A. The v1.0.0 heuristic happened
to produce the right *output* for tripe by the *wrong mechanism* (matching the
substring "tripe" in a hardcoded non-organ list), which is fragile: it breaks
silently the moment a new ingredient is added whose `ingredient_id` doesn't
happen to contain one of the nine hardcoded substrings, or contains one
coincidentally. This is the same anti-pattern already found twice elsewhere in
this project (the blanket `REF_FORMULATION_RULES_EXCLUSION` rule for
vitamin_a_iu, and `CSTR_NB_*_MIN` tier hardcoded by ID-prefix instead of read
from the registry) — a Python-level categorical policy silently reimplementing
a structured field that already exists in the data. Do not perpetuate it a
third time.

**Steps:**

1. Open `$PROJECT_ROOT/resolve_usda_nutrients.py`, locate the `resolve_direct`
   function (around line 355).
2. **Update the function signature** to receive the ingredient's `category`
   (not just its `ingredient_id` — the category field is the correct signal):
   ```python
   # Before:
   def resolve_direct(nutrients_dict, excluded_list, ...):
       ...

   # After:
   def resolve_direct(nutrients_dict, excluded_list, ingredient_id, ingredient_category, ...):
       ...
   ```
3. Locate the block at L410–414 that sets `status=measured`:
   ```python
   final_val = round(value * factor, 3)
   entry["status"] = "measured"
   entry["value"] = final_val
   entry["unit"] = cfg["unit"]
   ```
4. **Insert the policy check before** `entry["status"] = "measured"`, branching
   on `ingredient_category` rather than substring-matching `ingredient_id`:
   ```python
   final_val = round(value * factor, 3)

   # Vitamin A policy: 0.0 IU is semantically "not applicable" (the tissue does
   # not store/secrete vitamin A) rather than "measured as zero", for specific
   # categories only. Driven by the ingredient's own `category` field — NOT by
   # substring-matching ingredient_id, which cannot represent categories like
   # muscle_organ (heart, tongue: muscular tissue that is anatomically an
   # organ) or distinguish organ_non_secreting (tripe: an organ that structurally
   # does not store vitamin A) from organ_secreting (liver, kidney: DOES store
   # vitamin A and must never be overridden to not_applicable).
   if json_key == "vitamin_a_iu" and final_val == 0.0:
       _NOT_APPLICABLE_CATEGORIES = (
           "muscle_meat", "fat_source", "blood_source", "connective_tissue",
           "organ_non_secreting",
       )
       _NEVER_OVERRIDE_CATEGORIES = (
           "organ_secreting",   # e.g. liver, kidney — must remain measured
       )
       _AMBIGUOUS_CATEGORIES = (
           "muscle_organ",   # e.g. heart, tongue — muscular tissue that IS an
                              # organ; whether a 0.0 IU reading is a genuine
                              # measurement or a not_applicable case depends on
                              # the specific organ's known physiology, not a
                              # blanket rule. DO NOT auto-decide this — flag for
                              # manual review, same discipline as the FDC
                              # tie-break rule in Task-1.
       )
       if ingredient_category in _NEVER_OVERRIDE_CATEGORIES:
           pass  # fall through to measured=0.0 below; this is a real zero reading
       elif ingredient_category in _NOT_APPLICABLE_CATEGORIES:
           entry["status"] = "not_applicable"
           entry.pop("value", None)
           entry["unit"] = cfg["unit"]
           entry["basis"] = profile_basis
           entry["source_ref"] = "REF_USDA_FDC_" + str(ingredient.get("metadata", {}).get("usda_fdc_id", "unknown")) + "_POLICY_NA"
           if json_key in excluded_list:
               pass  # Task-6 stops mutating coverage_excluded_nutrients
           continue
       elif ingredient_category in _AMBIGUOUS_CATEGORIES:
           raise ValueError(
               f"{ingredient_id}: vitamin_a_iu=0.0 with category='{ingredient_category}' "
               f"is ambiguous per policy (muscle_organ tissue) and requires an "
               f"explicit, documented decision before this pipeline can run "
               f"non-interactively. Add {ingredient_id} to either "
               f"_NOT_APPLICABLE_CATEGORIES or _NEVER_OVERRIDE_CATEGORIES "
               f"overrides below, with a one-line physiological justification, "
               f"or handle it as a genuine 'missing' measurement — do not "
               f"silently default it either way."
           )
       # else: unknown category not covered by any bucket above — fall through
       # to measured=0.0 (conservative default: treat as a real reading unless
       # explicitly told otherwise)

   entry["status"] = "measured"
   entry["value"] = final_val
   entry["unit"] = cfg["unit"]
   ```
5. **Resolve the two known `muscle_organ` cases explicitly before this task can
   be committed** — `beef_heart_raw`, `chicken_heart_raw`, `beef_tongue_raw`
   will all raise the `ValueError` above on first run. This is intentional:
   the plan does not pre-decide this for you. Look up whether beef/chicken
   heart and tongue tissue have documented vitamin A content (they generally
   do, at levels far below liver/kidney but non-zero) and either:
   - add them to `_NOT_APPLICABLE_CATEGORIES` overrides with a citation, or
   - add them to `_NEVER_OVERRIDE_CATEGORIES` overrides with a citation, or
   - leave them to raise and mark them `missing` instead of `not_applicable`
     if no reliable source exists (consistent with this project's existing
     "don't invent values" standard).
   Document the decision and its source in a code comment next to the
   override, and in `download/fdc_id_migration.log` or an equivalent audit
   note.
6. **Update all callers** of `resolve_direct` to pass `ingredient_id` and
   `ingredient_category`:
   ```bash
   rg "resolve_direct\(" "$PROJECT_ROOT/resolve_usda_nutrients.py"
   ```
   Each call site must pass both values from the outer loop, where
   `ingredient_category = ingredient.get("category")`.

**State mutations:**

| File | Before | After |
|---|---|---|
| `resolve_usda_nutrients (1).py` `resolve_direct` | Signature without `ingredient_id`/`category`; sets `measured: 0.0` without context check | Signature with both; policy check branches on `category`, raises on the ambiguous `muscle_organ` bucket instead of silently guessing |
| All callers of `resolve_direct` | Do not pass `ingredient_id`/`category` | Pass both |

**Verification:**

```bash
# V1: function updated
rg "def resolve_direct\(nutrients_dict, excluded_list, ingredient_id, ingredient_category" "$PROJECT_ROOT/resolve_usda_nutrients.py"
# expected: 1 match

# V2: category-driven policy check present
rg "Driven by the ingredient's own \`category\` field" "$PROJECT_ROOT/resolve_usda_nutrients.py"
# expected: 1 match

# V3: the ambiguous muscle_organ case actually raises (proves it's not silently defaulted)
python -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/upload')
# construct a minimal call with category='muscle_organ' and final_val=0.0,
# confirm ValueError is raised, NOT a silent measured/not_applicable choice
"
# expected: ValueError raised, mentioning 'requires an explicit, documented decision'

# V4: after resolving step 5's overrides, the same call no longer raises
# (re-run V3 after the overrides are added)

# V5: syntax regression check
python -c "
import ast
with open('$PROJECT_ROOT/resolve_usda_nutrients.py') as f:
    ast.parse(f.read())
print('OK: syntax valid')
"
# expected exit: 0
```

**Rollback:**

```bash
git checkout -- "$PROJECT_ROOT/resolve_usda_nutrients.py"
```

---

### Task-5: Remove dead recompute of AAFCO composites in `build_pipeline.py`

```yaml
task_id: task-5
title: "Remove dead recompute of AAFCO composites in build_pipeline.py"
depends_on:
  - task-3   # edits the same file; task-3 must go first
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: -20   # net removal
commit_message: "refactor(build_pipeline): remove dead recompute of methionine_plus_cystine_g and phenylalanine_plus_tyrosine_g"
severity: low
```

**Preconditions:**
- P0–P5 satisfied
- Task-3 complete (same file)

**Steps:**

1. Open `$PROJECT_ROOT/build_pipeline.py`, locate the
   `convert_as_fed_to_energy_normalized` function by content:
   `rg -n "def convert_as_fed_to_energy_normalized" build_pipeline.py`.
   **Do NOT rely on line numbers — they are PRE-Plan-A baselines.** (v2.1.0 said
   L1629; actual pre-Plan-A was L1655; post-Plan-A ~L1670-1675.)
2. Locate the composite-recompute block by content:
   `rg -n "met_val = get_measured_value" build_pipeline.py`
   (v2.1.0 said L1652-1671; actual pre-Plan-A was L1700; post-Plan-A ~L1715-1735):
   ```python
   met_val = get_measured_value(nuts.get("methionine_g"))
   cys_val = get_measured_value(nuts.get("cystine_g"))
   if met_val is not None and cys_val is not None:
       raw = (met_val + cys_val) * (1000.0 / em)
       out["methionine_plus_cystine_g"] = {
           "status": "measured", "value": raw * get_bioavailability_factor(...)
       }

   phe_val = get_measured_value(nuts.get("phenylalanine_g"))
   tyr_val = get_measured_value(nuts.get("tyrosine_g"))
   if phe_val is not None and tyr_val is not None:
       raw = (phe_val + tyr_val) * (1000.0 / em)
       out["phenylalanine_plus_tyrosine_g"] = {
           "status": "measured", "value": raw * get_bioavailability_factor(...)
       }
   ```
3. **Delete the whole block** (lines 1652–1671, ~20 lines).
4. Replace with a short rationale comment:
   ```python
   # AAFCO composites (Met+Cys, Phe+Tyr) are resolved directly by
   # resolve_usda_nutrients.py.resolve_composite() from the USDA API, which
   # returns the composite as a single nutrient. The recompute from individual
   # components was removed because:
   #   1. cystine_g and tyrosine_g are not keys anywhere in the DB (0/23 ingredients)
   #   2. Even if they were, this would create a dual source of truth vs. resolve_composite
   # If we ever want to compute from components again in the future, restore
   # this block and remove resolve_composite from the USDA script.
   ```
5. Confirm the main loop `for registry_key in SOLVER_NUTRIENTS` (which adds
   `{"status": "missing"}` for absent keys) remains intact — it guarantees
   `methionine_plus_cystine_g` and `phenylalanine_plus_tyrosine_g` always
   appear in the output, even if absent from the input.

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` L1652–1671 | 20-line recompute block | 6-line comment |

**Verification:**

```bash
# V1: block removed (no 'met_val' anywhere in the file)
rg "met_val = get_measured_value" $PROJECT_ROOT/build_pipeline.py
# expected: 0 matches

# V2: rationale comment present
rg "AAFCO composites.*resolved directly" $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V3: valid syntax
python -c "import ast; ast.parse(open('$PROJECT_ROOT/build_pipeline.py').read()); print('OK')"
# expected exit: 0

# V4: convert_as_fed_to_energy_normalized still returns a dict with all 41
# SOLVER_NUTRIENTS keys
python -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/upload')
import json, build_pipeline as bp
db = json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json'))
ing = db['protein_sources']['bovinos']['ingredients'][0]
bio = {}  # mock
out = bp.convert_as_fed_to_energy_normalized(ing, bio)
assert len(out) >= 41, f'got {len(out)} keys'
print('OK:', len(out), 'keys')
"
# expected: 'OK: 41 keys' or more
```

**Rollback:**

```bash
git revert <task-5-commit-sha>
```

---

### Task-6: Update `test_5_3_composite_aa_handling` + stop mutating `coverage_excluded_nutrients`

```yaml
task_id: task-6
title: "Update test_5_3 + stop mutating coverage_excluded_nutrients in resolve_usda"
depends_on:
  - task-4   # same composite-AA logic; needs the category-driven policy check first
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/tests/test_dimensional_pipeline.py
  - $PROJECT_ROOT/resolve_usda_nutrients.py
idempotent: true
estimated_loc: ~30
commit_message: "test+fix: relax test_5_3 composite assertion and stop mutating deprecated coverage_excluded_nutrients"
severity: low
```

**Preconditions:**
- P0–P5 satisfied
- Task-4 complete (same `resolve_usda_nutrients` file)

**Steps:**

#### Part A — Update `test_5_3_composite_aa_handling`

1. Open `$PROJECT_ROOT/tests/test_dimensional_pipeline.py`, locate
   `test_5_3_composite_aa_handling` (around line 203).
2. Locate the `else` block that currently asserts:
   ```python
   else:
       # Either met or cys is missing → composite must be missing
       assert met_cys["status"] == "missing", (
           f"{ing['ingredient_id']}: Met+Cys should be missing "
           f"(met={met_measured}, cys={cys_measured}, "
           f"got status={met_cys['status']})"
       )
   ```
3. Replace with:
   ```python
   else:
       # After USDA resolution via resolve_composite(), the composite can be
       # 'measured' (the API returned Met+Cys directly) or 'missing' (the API
       # returned neither the composite nor the individual components). Both
       # are valid; we no longer require 'missing' when individual components
       # aren't measured.
       assert met_cys["status"] in ("missing", "measured"), (
           f"{ing['ingredient_id']}: Met+Cys must be missing or measured, "
           f"got status={met_cys['status']} (met={met_measured}, "
           f"cys={cys_measured})"
       )
   ```
4. Repeat the same change for the equivalent
   `phenylalanine_plus_tyrosine_g` block in the same test.
5. Update the test's docstring (around lines 205–215) to reflect the new
   semantics:
   ```python
   """Composite AAs (Met+Cys, Phe+Tyr) handling.

   After USDA resolution via resolve_composite():
     - If the API returns the compound directly -> status='measured'
     - If the API returns neither the compound nor the individual components -> status='missing'
     - Individual components (cystine_g, tyrosine_g) are NOT required keys;
       the composite can be 'measured' without them.

   This test verifies that convert_as_fed_to_energy_normalized:
     - Preserves 'measured' status when the API provided the compound
     - Preserves 'missing' status otherwise
   """
   ```

#### Part B — Stop mutating `coverage_excluded_nutrients`

6. Open `$PROJECT_ROOT/resolve_usda_nutrients.py`, locate the 2 `.remove()`
   calls on `excluded_list`:
   ```bash
   rg "excluded_list\.remove" "$PROJECT_ROOT/resolve_usda_nutrients.py"
   # expected: 2 matches, around L421 and L475
   ```
7. **Comment out** both calls (do not delete — preserve the historical
   behavior for PR review):
   ```python
   # Task-6: coverage_excluded_nutrients is DEPRECATED per schema L118.
   # Stop mutating it; it will be removed in v11. The list becomes
   # consistently stale (read-only), which is acceptable per the deprecation
   # note.
   # if json_key in excluded_list:
   #     excluded_list.remove(json_key)
   ```

**State mutations:**

| File | Before | After |
|---|---|---|
| `test_dimensional_pipeline.py` L256–264 | `assert status == "missing"` | `assert status in ("missing", "measured")` |
| `test_dimensional_pipeline.py` docstring | Describes cystine/tyrosine as a future addition | Describes the new post-resolve_composite semantics |
| `resolve_usda_nutrients (1).py` L421, L475 | Active `excluded_list.remove(json_key)` | Commented out, with a deprecation note |

**Verification:**

```bash
# V1: test updated
rg "assert met_cys\[.status.\] in \(.missing., .measured.\)" $PROJECT_ROOT/tests/test_dimensional_pipeline.py
# expected: 1 match

# V2: no active .remove call on excluded_list
rg "^[^#]*excluded_list\.remove" "$PROJECT_ROOT/resolve_usda_nutrients.py"
# expected: 0 matches (all occurrences must be commented out)

# V3: commented-out references still present (historical trace)
rg "#.*excluded_list\.remove" "$PROJECT_ROOT/resolve_usda_nutrients.py"
# expected: 2 matches
```

**Rollback:**

```bash
git revert <task-6-commit-sha>
```

---

### Task-7: Re-run USDA resolution over corrected FDCs + final integrated verification

```yaml
task_id: task-7
title: "Re-run USDA resolution over corrected FDCs + final integrated verification"
depends_on:
  - task-1
  - task-1b
  - task-2
  - task-3
  - task-4
  - task-5
  - task-6
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json   # overwrite
  - $PROJECT_ROOT/scripts/resolution_report_final.json     # new
idempotent: true   # re-running produces the same deterministic output
estimated_loc: 0   # execution only
commit_message: "chore(data): regenerate DB_ingredientes_RESOLVIDO.json with corrected FDCs and hardened pipeline"
severity: blocker
```

**Preconditions:**
- All tasks 1–6 (and 1B) in `completed` status
- `$USDA_API_KEY` available
- Clean working tree (all prior tasks committed)

**Steps:**

**Step 0 (NEW in v2.0.0) — FDC integrity check before doing anything else:**
```python
import json
db = json.load(open("$PROJECT_ROOT/data/DB_ingredientes.json"))
current = {}
for cat_name, cat_data in db["protein_sources"].items():
    for ing in cat_data.get("ingredients", []):
        current[ing["ingredient_id"]] = ing["metadata"]["usda_fdc_id"]
baseline = json.load(open("$PROJECT_ROOT/download/fdc_ids_post_task1.snapshot.json"))
assert current == baseline, (
    f"FDC IDs drifted between Task-1 and Task-7! Diff: "
    f"{ {k: (baseline.get(k), current.get(k)) for k in set(current) | set(baseline) if baseline.get(k) != current.get(k)} }"
)
print("OK: FDC IDs unchanged since Task-1")
```
If this fails, **STOP** — do not proceed with re-resolution. Something in
Tasks 2–6 corrupted or reverted an FDC ID; bisect that before continuing.

1. **Remove the old resolved DB** (generated against incorrect FDCs):
   ```bash
   rm -f $PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json
   rm -f $PROJECT_ROOT/scripts/resolution_report_write.json
   ```

2. **Probe FIRST (DS2 FIX v2.3)** — verify the USDA API response schema hasn't changed:
   ```bash
   cd $PROJECT_ROOT
   export USDA_API_KEY="$USDA_API_KEY"  # re-export per DS3
   python resolve_usda_nutrients.py --api-key "$USDA_API_KEY" --probe
   ```
   The script's own docstring says: "Rode --probe primeiro. Sempre." (Run --probe first. Always.)
   The `--probe` mode downloads and prints the raw API response for 1-2 ingredients BEFORE any write.
   **If the API response schema has changed** (e.g. `foodNutrients` format differs from what the script's `extract_nutrient_index()` handles), STOP — the script must be updated before proceeding. Do NOT skip this step.

3. **Dry-run second** — confirm the corrected FDCs return data:
   ```bash
   cd $PROJECT_ROOT
   python resolve_usda_nutrients.py \
     --input data/DB_ingredientes.json \
     --output /tmp/DB_RESOLVIDO_dryrun.json \
     --api-key "$USDA_API_KEY" \
     --dry-run \
     --log-file /tmp/dry_run_final.log

   # Inspect the log
   cat /tmp/dry_run_final.log | grep -E "(WARNING|ERROR)" | head -30
   ```
   Expected: no `ERROR`, only `WARNING` for kcal/kJ divergence (audit-only,
   writes nothing — see removed steps C2/C4 from an earlier plan revision).

3. **Write-mode execution:**
   ```bash
   cd $PROJECT_ROOT
   python resolve_usda_nutrients.py \
     --input data/DB_ingredientes.json \
     --output scripts/DB_ingredientes_RESOLVIDO.json \
     --api-key "$USDA_API_KEY" \
     --log-file scripts/resolution_log_final.log
   ```
   **S3 FIX (v2.3):** v2.2 used `--input DB_ingredientes.json` (relative path) with `cd $PROJECT_ROOT/upload`. The raw DB is at `data/DB_ingredientes.json`, NOT at repo root. Fixed to `--input data/DB_ingredientes.json`.
   **DS3 FIX (v2.3):** Re-export `USDA_API_KEY` at the start of this step — OpenCode's shell-variance bug (Plan B Task-0) means the env var may not persist from the last task:
   ```bash
   export USDA_API_KEY="$(grep USDA_API_KEY ~/.env 2>/dev/null | cut -d= -f2 || echo $USDA_API_KEY)"
   [ -z "$USDA_API_KEY" ] && echo "ERROR: USDA_API_KEY not set" && exit 1
   ```

4. **Integrated validations (ALL must pass):**

   ```bash
   # V1: jsonschema.validate passes
   python -c "
   import json, jsonschema
   db = json.load(open('$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json'))
   schema = json.load(open('$PROJECT_ROOT/data/db_ingredientes.schema.json'))
   jsonschema.validate(db, schema)
   print('OK: jsonschema passes')
   "

   # V2: 0 source_ref pattern violations
   python -c "
   import json, re
   db = json.load(open('$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json'))
   pat = re.compile(r'^REF_[A-Z0-9_]+$')
   v = 0
   for cat_name, cat_data in db.items():
       if cat_name.startswith('_') or not isinstance(cat_data, dict):
           continue
       for sub_name, sub_data in cat_data.items():
           if sub_name.startswith('_') or not isinstance(sub_data, dict):
               continue
           for ing in sub_data.get('ingredients', []):
               nuts = ing.get('bromatological_profile', {}).get('nutrients', {})
               for nkey, ndata in nuts.items():
                   if isinstance(ndata, dict):
                       sr = ndata.get('source_ref', '')
                       if sr and not pat.match(sr):
                           v += 1
                           print(f'  VIOLATION: {ing["ingredient_id"]}.{nkey} = {sr}')
   assert v == 0, f'{v} violations found'
   print('OK: 0 source_ref pattern violations')
   "

   # V3 (REWRITTEN in v2.0.0): 0 category/vitamin_a_iu mismatches — replaces
   # the old substring-based non-organ check with a category-field check
   python -c "
   import json
   db = json.load(open('$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json'))
   never_override = {'organ_secreting'}
   not_applicable_ok = {'muscle_meat', 'fat_source', 'blood_source', 'connective_tissue', 'organ_non_secreting'}
   bad = []
   for cat_name, cat_data in db.items():
       if cat_name.startswith('_') or not isinstance(cat_data, dict):
           continue
       for sub_name, sub_data in cat_data.items():
           if sub_name.startswith('_') or not isinstance(sub_data, dict):
               continue
           for ing in sub_data.get('ingredients', []):
               iid = ing.get('ingredient_id', '')
               category = ing.get('category', '')
               va = ing.get('bromatological_profile', {}).get('nutrients', {}).get('vitamin_a_iu', {})
               if va.get('status') == 'measured' and va.get('value') == 0.0 and category in not_applicable_ok:
                   bad.append((iid, category, 'should be not_applicable, is measured=0.0'))
               if va.get('status') == 'not_applicable' and category in never_override:
                   bad.append((iid, category, 'organ_secreting should never be not_applicable'))
   assert not bad, f'BAD: {bad}'
   print('OK: 0 category/vitamin_a_iu mismatches')
   "

   # V4: pytest passes
   cd $PROJECT_ROOT
   python -m pytest tests/test_dimensional_pipeline.py -q

   # V5: validate_inputs passes on the resolved DB
   python -c "
   import sys; sys.path.insert(0, '$PROJECT_ROOT/upload')
   import json, build_pipeline as bp
   db = json.load(open('$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json'))
   # ... call validate_inputs with the appropriate parameters
   print('OK: validate_inputs passes')
   "
   ```

5. **Coverage audit** — before/after comparison:
   ```bash
   python $PROJECT_ROOT/scripts/auditar_cobertura.py \
     --antes $PROJECT_ROOT/download/DB_ingredientes.backup_pre_fix.json \
     --depois $PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json \
     --output $PROJECT_ROOT/download/coverage_diff.json
   ```
   (This audit script may be created if it doesn't exist; it is not blocking.)

6. **Final commit:**
   ```bash
   cd $PROJECT_ROOT
   git add scripts/DB_ingredientes_RESOLVIDO.json scripts/resolution_log_final.log
   git commit -m "chore(data): regenerate DB_ingredientes_RESOLVIDO.json with corrected FDCs and hardened pipeline"
   ```

**State mutations:**

| File | Before | After |
|---|---|---|
| `scripts/DB_ingredientes_RESOLVIDO.json` | Generated with 20 incorrect FDCs, with `_MCGxIU`, vit A `0.0` | Regenerated with correct FDCs, `_MCGXIU`, vit A `not_applicable` only where the `category` field says so |
| `scripts/resolution_log_final.log` | does not exist | full execution log |
| Git history | 7 commits from tasks 1, 1B, 2–6 | +1 final commit (Task-7) |

**Verification (all Q0–Q6 from plan-level):**

```bash
# Q0: 23/23 FDC matches
python $PROJECT_ROOT/scripts/validar_fdc_rigoroso.py 2>&1 | grep "MATCH total" | grep "23/23"

# Q0B: FDC IDs unchanged since Task-1 (already done in Step 0 above)

# Q1: jsonschema passes (already done in V1)

# Q2: pytest passes (already done in V4)

# Q3: 0 source_ref violations (already done in V2)

# Q4: 0 category/vitamin_a_iu mismatches (already done in V3)

# Q5: coverage_excluded_nutrients not mutated
rg "^[^#]*excluded_list\.remove" "$PROJECT_ROOT/resolve_usda_nutrients.py"
# expected: 0 matches

# Q6: clean working tree
cd $PROJECT_ROOT && git status --short
# expected: empty
```

**Rollback (catastrophic):**

If Task-7 fails and the resolved DB is corrupted:

```bash
# 1. Restore the original DB
cp $PROJECT_ROOT/download/DB_ingredientes.backup_pre_fix.json \
   $PROJECT_ROOT/data/DB_ingredientes.json

# 2. Revert all 7 tasks in reverse order
git revert HEAD HEAD~1 HEAD~2 HEAD~3 HEAD~4 HEAD~5 HEAD~6 HEAD~7

# 3. Re-create a hotfix branch if needed
git checkout -b fix/rollback-fdc-pipeline
```

---

### Task-8: Regenerate MAPA with corrected nutrient data (NEW in v2.2.0)

```yaml
task_id: task-8
title: "Regenerate MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md against corrected FDCs"
depends_on:
  - task-7b   # S2/A1 FIX (v2.3): must swap DB first, otherwise MAPA regenerates against the same raw DB
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md   # overwrite
idempotent: true
estimated_loc: 0   # execution only
commit_message: "chore(docs): regenerate MAPA with corrected-FDC nutrient data (closes stale-evidence gap)"
severity: blocker
```

**Rationale:** Plan A (MAPA generator fix v1.2.0) regenerated the MAPA against
`data/DB_ingredientes.json` (raw DB) — which contained nutrient values from 20
incorrect FDC IDs. Plan A's Phase 4-1 (`capture_live_evidence`) ran the LP
solver against those wrong values and embedded the results in the MAPA's
evidence section. The pipeline behavior was honestly reported, but the
underlying data was garbage.

**A1 FIX (v2.3):** v2.2 assumed Task-7 alone would fix this — but
`build_pipeline.py` loads `data/DB_ingredientes.json`, NOT
`scripts/DB_ingredientes_RESOLVIDO.json`. Task-7B (new in v2.3) swaps the
resolved DB into `data/DB_ingredientes.json`. Only NOW can the MAPA
regeneration produce different evidence.

Task-8 regenerates the MAPA so its evidence section reflects the corrected
nutrient data now living at `data/DB_ingredientes.json`. Without Task-7B +
Task-8, the MAPA would be dishonest about clinical safety — it would show
"solver_status: optimal" against data that no longer exists in the repo.

**Preconditions:**
- Task-7 complete (corrected `DB_ingredientes_RESOLVIDO.json` exists at
  `$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json`)
- Plan A's `doc_introspector.py` and `build_pipeline.py --generate-mapa` are
  functional (verified by P-PLAN-A)
- `$PROJECT_ROOT/tests/reference_cases.py` exists (Plan A artifact)

**Steps:**

1. **Verify the corrected resolved DB loads cleanly:**
   ```bash
   python -c "import json; db=json.load(open('$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json')); n=sum(len(s.get('ingredients',[])) for s in db['protein_sources'].values() if isinstance(s,dict)); assert n==23, n; print('OK', n)"
   ```
   Expected: `OK 23`. If this fails, Task-7 did not complete correctly — go back.

2. **Back up the Plan-A-era MAPA (for audit):**
   ```bash
   cp $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md \
      $PROJECT_ROOT/download/MAPA_COMPLETO_post-Plan-A_pre-Plan-B.md.bak
   ```
   This preserves the Plan-A output so a future auditor can diff the two MAPA
   versions and see exactly which evidence values changed when the FDCs were
   corrected.

3. **Regenerate the MAPA:**
   ```bash
   cd $PROJECT_ROOT
   python build_pipeline.py --generate-mapa --out MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   ```
   This invokes Plan A's full pipeline: `ImplIntrospector.check()` for the
   implementation-status table, `compute_satellite_stats()` for bundle sizes,
   `STRUCTURE_CONTRACTS` for JSON-schema verification, and — critically —
   `capture_live_evidence()` which re-runs the LP solver against the corrected
   `DB_ingredientes_RESOLVIDO.json`.

4. **Verify the evidence section reflects the corrected data:**
   ```bash
   # V1: provenance markers preserved (Plan A's anti-regression Check 11)
   rg -c "SOURCE: IMPLEMENTATION_SPEC" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   # expected: >= 10 (same count as Plan A's output — the spec didn't change)

   # V2: live evidence section present and populated
   rg -c "capture_live_evidence\|Live Execution Evidence" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   # expected: >= 1

   # V3: LP-specific evidence fields populated (Plan A's D9 expansion)
   rg "solver_status" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   # expected: >= 1 match showing solver_status: optimal (or suboptimal — both
   # are honest; the point is the field is populated against corrected data)

   # V4: satellite line counts match actual files (Plan A's anti-regression Check 1)
   python -c "
   from pathlib import Path
   mapa = Path('$PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md').read_text()
   sat = Path('$PROJECT_ROOT/docs/architecture/sat_pipeline_codigo.md').read_text()
   actual = len(sat.splitlines())
   assert str(actual) in mapa, f'sat_pipeline_codigo actual={actual} not found in MAPA'
   print('OK: satellite line counts match')
   "
   ```

5. **Run Plan A's anti-regression gate (13 checks):**
   ```bash
   cd $PROJECT_ROOT
   python -c "
   import build_pipeline as bp
   mapa = open('MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md').read()
   bp.validate_mapa(mapa)  # Plan A's 13-check validator
   print('OK: all 13 anti-regression checks pass')
   "
   ```
   If any check fails, DO NOT commit — the MAPA regressed. Investigate which
   Plan A invariant broke.

6. **Commit:**
   ```bash
   cd $PROJECT_ROOT
   git add MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   git commit -m "chore(docs): regenerate MAPA with corrected-FDC nutrient data (closes stale-evidence gap)"
   ```

**State mutations:**

| File | Before | After |
|---|---|---|
| `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` | Evidence captured against 20 wrong FDCs (Plan A output) | Evidence captured against 23/23 correct FDCs |
| `download/MAPA_COMPLETO_post-Plan-A_pre-Plan-B.md.bak` | does not exist | Plan-A-era MAPA preserved for audit diff |
| Git history | 8 commits (tasks 1, 1B, 2–7) | +1 final commit (Task-8) |

**Verification (Q7):**

```bash
# Q7: MAPA regenerated with corrected data
rg -c "SOURCE: IMPLEMENTATION_SPEC" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
# expected: >= 10

# Plus: Plan A's validate_mapa passes (13 checks)
python -c "import build_pipeline as bp; bp.validate_mapa(open('$PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md').read()); print('OK')"
```

**Rollback:**

```bash
# Restore the Plan-A-era MAPA (evidence against wrong FDCs — honest about pipeline,
# dishonest about data — but a known rollback state)
cp $PROJECT_ROOT/download/MAPA_COMPLETO_post-Plan-A_pre-Plan-B.md.bak \
   $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
git revert HEAD
```

---

### Task-7B: Swap resolved DB into the pipeline (NEW in v2.3 — S2/A1 FIX)

```yaml
task_id: task-7b
title: "Replace data/DB_ingredientes.json with the corrected resolved DB"
depends_on:
  - task-7
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/data/DB_ingredientes.json   # OVERWRITE with resolved version
  - $PROJECT_ROOT/download/DB_ingredientes_pre_resolution.bak.json   # NEW backup
idempotent: false   # re-running without a revert would overwrite the pre-resolution backup
estimated_loc: ~15
commit_message: "chore(data): swap DB_ingredientes.json with resolved version (corrected FDCs + USDA nutrients)"
severity: blocker
```

**Rationale (S2/A1 FIX — CATASTROPHIC):**

`build_pipeline.py` L37 defines `JSON_FILES = ["DB_ingredientes.json", ...]` and
`load_all_jsons()` at L88 reads from `data/DB_ingredientes.json`. **The pipeline
does NOT load `scripts/DB_ingredientes_RESOLVIDO.json`.** Task-7 wrote the
corrected DB there — but the pipeline never sees it.

This means:
- `--runtime` mode (L3363) loads the RAW DB → LP solver runs against wrong FDC nutrient values
- `--generate-mapa` mode (L3230) loads the RAW DB → MAPA evidence captured against wrong data
- Plan A's `capture_live_evidence()` (Phase 4-1) loads the RAW DB → evidence section is dishonest

**Without this task, Plan B's entire FDC correction effort is invisible to the pipeline.**
Plan A's MAPA evidence will be identical pre- and post-Plan-B. Task-8 (regenerate
MAPA) would produce a byte-identical file. This task is the bridge between
"corrected DB exists" and "pipeline uses corrected DB".

**Preconditions:**
- Task-7 complete (`scripts/DB_ingredientes_RESOLVIDO.json` exists with 23/23 correct FDCs)
- All Task-7 verifications passed (Q0–Q6)

**Steps:**

1. **Verify the resolved DB is structurally valid before swapping:**
   ```bash
   python -c "
   import json, jsonschema
   db = json.load(open('$PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json'))
   schema = json.load(open('$PROJECT_ROOT/data/db_ingredientes.schema.json'))
   jsonschema.validate(db, schema)
   n = sum(len(s.get('ingredients', [])) for s in db['protein_sources'].values() if isinstance(s, dict))
   assert n == 23, f'expected 23 ingredients, got {n}'
   print(f'OK: resolved DB passes schema, {n} ingredients')
   "
   ```
   If this fails, DO NOT proceed — the resolved DB is corrupted. Go back to Task-7.

2. **Back up the current (pre-resolution) raw DB:**
   ```bash
   cp $PROJECT_ROOT/data/DB_ingredientes.json \
      $PROJECT_ROOT/download/DB_ingredientes_pre_resolution.bak.json
   sha256sum $PROJECT_ROOT/data/DB_ingredientes.json > $PROJECT_ROOT/download/DB_ingredientes_pre_resolution.sha256
   ```
   This backup is the rollback anchor. Do NOT delete it.

3. **Swap the resolved DB into the pipeline's load path:**
   ```bash
   cp $PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json \
      $PROJECT_ROOT/data/DB_ingredientes.json
   ```
   After this copy, `build_pipeline.py`'s `load_all_jsons()` will load the
   corrected DB. The LP solver, MAPA generator, and `--runtime` mode all see
   the corrected FDC nutrient values.

4. **Verify the swap:**
   ```bash
   # V1: SHA-256 of the new data/DB_ingredientes.json matches scripts/DB_ingredientes_RESOLVIDO.json
   sha256sum $PROJECT_ROOT/data/DB_ingredientes.json
   sha256sum $PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json
   # expected: identical hashes

   # V2: 0 source_ref pattern violations in the swapped DB (Q3 on the live DB now)
   python -c "
   import json, re
   db = json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json'))
   pat = re.compile(r'^REF_[A-Z0-9_]+$')
   v = 0
   for cat_name, cat_data in db.items():
       if cat_name.startswith('_') or not isinstance(cat_data, dict): continue
       for sub_name, sub_data in cat_data.items():
           if sub_name.startswith('_') or not isinstance(sub_data, dict): continue
           for ing in sub_data.get('ingredients', []):
               nuts = ing.get('bromatological_profile', {}).get('nutrients', {})
               for nkey, ndata in nuts.items():
                   if isinstance(ndata, dict):
                       sr = ndata.get('source_ref', '')
                       if sr and not pat.match(sr):
                           v += 1
                           print(f'  VIOLATION: {ing["ingredient_id"]}.{nkey} = {sr}')
   assert v == 0, f'{v} violations found in swapped DB'
   print('OK: 0 source_ref violations in swapped DB')
   "

   # V3: 0 _MCGxIU (lowercase) in the swapped DB (Task-2 fix is now live)
   rg "_MCGxIU" $PROJECT_ROOT/data/DB_ingredientes.json
   # expected: exit code 1 (no matches)

   # V4: pytest still passes against the swapped DB
   cd $PROJECT_ROOT && python -m pytest tests/ -q
   # expected: 32+ passed, 0 failed
   # NOTE: some test assertions may need updating if they hardcoded nutrient values
   # from the old (wrong-FDC) DB. If a test fails, inspect whether it's asserting
   # a specific nutrient value that changed — if so, update the assertion to match
   # the corrected value and document the delta in the commit message.
   ```

5. **Commit:**
   ```bash
   cd $PROJECT_ROOT
   git add data/DB_ingredientes.json
   git commit -m "chore(data): swap DB_ingredientes.json with resolved version (corrected FDCs + USDA nutrients)

   - Replaces raw DB (20 incorrect FDC IDs) with resolved DB (23/23 correct)
   - LP solver, MAPA generator, and --runtime mode now load corrected nutrient data
   - Backup at download/DB_ingredientes_pre_resolution.bak.json
   - Pre-resolution SHA256 at download/DB_ingredientes_pre_resolution.sha256
   "
   ```

**State mutations:**

| File | Before | After |
|---|---|---|
| `data/DB_ingredientes.json` | Raw DB (20 incorrect FDCs, missing nutrients) | Resolved DB (23/23 correct FDCs, USDA-resolved nutrients) |
| `download/DB_ingredientes_pre_resolution.bak.json` | does not exist | Pre-resolution raw DB (rollback anchor) |
| `download/DB_ingredientes_pre_resolution.sha256` | does not exist | SHA-256 of pre-resolution DB |
| Git history | 8 commits (tasks 1, 1B, 2–7) | +1 commit (Task-7B) |

**Verification (Q-S2):**

```bash
# Q-S2: pipeline loads the corrected DB
python -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
import build_pipeline as bp
data = bp.load_all_jsons()
db = data['DB_ingredientes.json']
# Check that a previously-incorrect FDC ID is now correct
for ing in db['protein_sources']['bovinos']['ingredients']:
    if ing['ingredient_id'] == 'beef_muscle_raw':
        fdc = ing['metadata']['usda_fdc_id']
        print(f'beef_muscle_raw FDC ID: {fdc}')
        # The corrected FDC ID should match what Task-1 set
        break
"
```

**Rollback:**

```bash
# Restore the pre-resolution raw DB
cp $PROJECT_ROOT/download/DB_ingredientes_pre_resolution.bak.json \
   $PROJECT_ROOT/data/DB_ingredientes.json
git revert HEAD
```

---

## Task Graph (visual dependencies)

```
Phase 1 (blocking, sequential):
  ┌─────────────┐      ┌─────────────┐
  │   Task-1    │      │   Task-1B   │  snapshot FDC IDs
  │ FDC IDs     │─────▶│  baseline   │  (integrity checkpoint)
  └──────┬──────┘      └──────┬──────┘
         │                    │
         ▼                    │
Phase 2 (quick fixes, partially parallel):     │
                                                 │
  ┌─────────────┐         ┌─────────────┐       │
  │   Task-2    │         │   Task-3    │       │
  │ _MCGxIU→X   │         │ validate_   │       │
  │ (resolve_   │         │ inputs      │       │
  │  usda)      │         │ (build_pip) │       │
  └──────┬──────┘         └──────┬──────┘       │
         │                       │               │
         ▼                       ▼               │
  ┌─────────────┐         ┌─────────────┐       │
  │   Task-4    │         │   Task-5    │       │
  │ vit A       │         │ remove      │       │
  │ policy      │         │ recompute   │       │
  │ (resolve_   │         │ (build_pip) │       │
  │  usda)      │         │             │       │
  └──────┬──────┘         └──────┬──────┘       │
         │                       │               │
         └──────────┬────────────┘               │
                    ▼                             │
              ┌─────────────┐                     │
              │   Task-6    │  test_5_3 + stop    │
              │             │  coverage_excluded  │
              └──────┬──────┘                     │
                     │                             │
                     └─────────────┬───────────────┘
                                   ▼
Phase 3 (final, sequential):
                            ┌─────────────┐
                            │   Task-7    │  Step 0: FDC integrity check
                            │             │  then re-resolve USDA + verify all
                            └──────┬──────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │  Task-7B    │  Swap resolved DB into data/ (S2/A1)
                            │  (NEW v2.3) │  Pipeline now loads corrected FDCs
                            └──────┬──────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   Task-8    │  Regenerate MAPA with corrected
                            │             │  nutrient data (closes stale-evidence
                            └─────────────┘  gap from Plan A's Phase 4-1)
```

**Real parallelism:**
- Task-2 and Task-3 touch disjoint files → **parallel-safe**
- Task-4 touches `resolve_usda_nutrients` (same as Task-2) → **NOT parallel with Task-2**
- Task-5 touches `build_pipeline.py` (same as Task-3) → **NOT parallel with Task-3**
- Task-6 touches `test_dimensional_pipeline.py` + `resolve_usda_nutrients` (same as Task-4) → **NOT parallel with Task-4**
- Task-1B only depends on Task-1 and can run in parallel with anything in Phase 2

**Recommended linear order (simplest):**
Task-S1 → Task-1 → Task-1B → Task-2 → Task-3 → Task-4 → Task-5 → Task-6 → Task-7 → Task-7B → Task-8

**Task-S1** (NEW v2.3): add `requests` to `requirements.txt` before any task imports `resolve_usda_nutrients.py`

**Optimized parallel order (if the agent supports it):**
- Phase A: Task-1 (blocking, isolated), then Task-1B (cheap, depends only on Task-1)
- Phase B in parallel: {Task-2 + Task-3} (disjoint files)
- Phase C in parallel: {Task-4 + Task-5} (disjoint files, but depend on B)
- Phase D: Task-6 (depends on Task-4)
- Phase E: Task-7 (depends on all)

---

## Rollback Plan (consolidated, reverse order)

| Order | Task | Rollback command |
|---|---|---|
| 1 | Task-8 | `cp $PROJECT_ROOT/download/MAPA_COMPLETO_post-Plan-A_pre-Plan-B.md.bak $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md && git revert HEAD` |
| 2 | Task-7B | `cp $PROJECT_ROOT/download/DB_ingredientes_pre_resolution.bak.json $PROJECT_ROOT/data/DB_ingredientes.json && git revert HEAD~1` |
| 3 | Task-7 | `rm $PROJECT_ROOT/scripts/DB_ingredientes_RESOLVIDO.json && git revert HEAD~2` |
| 4 | Task-6 | `git revert HEAD~3` |
| 5 | Task-5 | `git revert HEAD~4` |
| 6 | Task-4 | `git revert HEAD~5` |
| 7 | Task-3 | `git revert HEAD~6` |
| 8 | Task-2 | `git revert HEAD~7` |
| 9 | Task-1B | `rm $PROJECT_ROOT/download/fdc_ids_post_task1.snapshot.json && git revert HEAD~8` |
| 10 | Task-1 | `cp $PROJECT_ROOT/download/DB_ingredientes.backup_pre_fix.json $PROJECT_ROOT/data/DB_ingredientes.json && git revert HEAD~9` |
| 11 | Task-S1 | `git revert HEAD~10` (restores old requirements.txt without `requests`) |

**Nuclear rollback (discard the whole branch):**
```bash
cd $PROJECT_ROOT
git checkout master
git branch -D fix/usda-fdc-and-pipeline-hardening
cp $PROJECT_ROOT/download/DB_ingredientes.backup_pre_fix.json \
   $PROJECT_ROOT/data/DB_ingredientes.json
```

---

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | The correct FDC does not exist in the USDA API for some ingredient (e.g. `chicken_kidney_raw`) | Medium | Medium | Accept `missing` for that ingredient; document it in the migration log |
| R2 | The USDA API changes its response format mid-run | Low | High | Pin the API version; test with 1 FDC before running all 23 |
| R3 | ~~Task-4's policy check misclassifies an ingredient (e.g. `beef_heart_raw` is technically an organ but is in the non-organ list)~~ **RESOLVED in v2.0.0** — Task-4 now branches on the `category` field, and `muscle_organ` (heart, tongue) explicitly raises for manual review instead of being silently misclassified. See Task-4 rewrite. | — | — | — |
| R4 | `test_5_3` fails even after relaxation (a different cause) | Low | Medium | Run `pytest -x` to see the first failure; inspect the output |
| R5 | `validate_inputs` breaks on legacy DBs not covered by this plan | Low | High | Run `pytest` across all of `repo_data/tests/`, not just `test_dimensional_pipeline.py` |
| R6 | Regenerating the resolved DB changes nutrient values for ingredients that were already correct (the 3 fat_sources) | Low | High | Diff the 3 fat_sources before/after; if any value changed, investigate |
| R7 (NEW) | Task-1's fuzzy FDC matcher produces a tie or a sanity-check failure that the executing agent resolves silently instead of flagging | Medium | High | Task-1's tie-break rule and sanity cross-check are now hard requirements (V5 in Task-1's verification); the plan explicitly forbids auto-resolving either |
| R8 (NEW) | Something in Tasks 2–6 reverts or corrupts an FDC ID before Task-7 re-resolves | Low | High | Task-1B snapshot + Task-7 Step 0 integrity check now catch this before expensive re-resolution runs |

---

## Acceptance Criteria (Definition of Done)

The plan is complete when **ALL** of the following criteria are met:

- [ ] 11 atomic commits on branch `fix/usda-fdc-and-pipeline-hardening` (7 in v1.0.0 + Task-1B v2.0.0 + Task-8 v2.2.0 + Task-S1 + Task-7B v2.3.0)
- [ ] Each commit message follows Conventional Commits (`fix(scope): desc` / `feat(scope): desc` / `refactor(scope): desc` / `chore(scope): desc` / `test(scope): desc`)
- [ ] `validar_fdc_rigoroso.py` returns `MATCH total: 23/23`
- [ ] FDC IDs are byte-identical between Task-1B's snapshot and the state at the start of Task-7
- [ ] `jsonschema.validate` passes on the new resolved DB
- [ ] `pytest tests/test_dimensional_pipeline.py` exit 0
- [ ] `pytest tests/test_cascade_integration.py` exit 0 (no regression)
- [ ] 0 source_refs with a lowercase letter outside the pattern
- [ ] 0 category/vitamin_a_iu mismatches (per the rewritten category-based check, not the old substring heuristic)
- [ ] The two known `muscle_organ` ambiguous cases (heart, tongue) have an explicit, documented, cited decision — not a default
- [ ] `coverage_excluded_nutrients` is not mutated (2 `.remove()` calls commented out)
- [ ] Clean working tree (`git status --short` empty)
- [ ] Backup `DB_ingredientes.backup_pre_fix.json` preserved in `download/`
- [ ] FDC migration log `fdc_id_migration.log` preserved in `download/`, with zero unresolved `TIE_REQUIRES_REVIEW` or `SANITY_CHECK_FAILED` entries
- [ ] MAPA regenerated (Task-8) with evidence captured against corrected FDCs; Plan A's 13 anti-regression checks pass
- [ ] `download/MAPA_COMPLETO_post-Plan-A_pre-Plan-B.md.bak` preserved for audit diff
- [ ] PR description links to this plan and lists all 11 commits

---

## Out of Scope (explicitly NOT done in this plan)

- Adding `energy_kcal` to `NUTRIENT_MAP` (bug I4 validated as FALSE — energy is computed via Atwater)
- Adding a kcal/kJ filter to the `lookup` function (same reason as above)
- Migrating `coverage_excluded_nutrients` out of the schema (deprecated but still read by 4 places in `build_pipeline.py`; removal requires a separate migration)
- Updating `audit_provenance.json` with new `source_refs` (done automatically by `resolve_usda_nutrients.py` in Task-7)
- Refactoring `build_pipeline.py` to use dataclasses instead of dicts (out of scope for this fix)
- Adding new tests for the corrected FDCs (covered by `validar_fdc_rigoroso.py`)
- Adding type hints to `resolve_usda_nutrients.py` (out of scope)
- Resolving vitamin A for any `muscle_organ`-category ingredient other than the two flagged in Task-4 (if more are added to the DB later, they will raise the same explicit error — that is intentional, not a bug to silently fix)

---

## Agent Handoff Protocol

This plan is designed to be executed by an autonomous LLM agent
(Claude Code / OpenAI Agents SDK / similar). Handoff protocol:

### For the executing agent:

1. **Read this entire plan before starting any task.** Do not skip sections.
2. **Verify all Preconditions P0–P5 before Task-1.** If any fails, stop and
   report — do not attempt to auto-fix preconditions.
3. **For each task:**
   a. Verify `depends_on` is in `completed` status
   b. Verify the task's specific preconditions
   c. Execute the Steps in order
   d. Run Verification — ALL commands must pass
   e. If Verification fails, do NOT commit — report the blocker
   f. If Verification passes, commit with the exact `commit_message` from the task
   g. Update the task status to `completed` in the execution log
4. **After Task-7:** run the plan-level Verification (Q0–Q6, including Q0B).
   If any fails, do NOT merge to `master` — report it.
5. **Rollback:** if you need to revert, use `git revert <sha>` — NEVER
   `git reset --hard` (preserves the audit trail).
6. **On any unspecified decision point** (a tie in Task-1's fuzzy matching, an
   ambiguous `muscle_organ` category in Task-4, a sanity-check failure): stop
   and report, do not silently pick an option. This plan intentionally leaves
   these points as hard stops rather than pre-deciding them — a wrong silent
   guess on a food-safety-relevant lookup is worse than a paused task.

### For the reviewing agent (PR review):

1. **Confirm all 8 commits are present** on the branch
2. **Confirm each commit is atomic** (single topic, no unrelated changes)
3. **Run the plan-level Verification independently**
4. **Inspect `fdc_id_migration.log`** — every FDC change must have an
   auditable justification, and zero unresolved `TIE_REQUIRES_REVIEW` or
   `SANITY_CHECK_FAILED` entries
5. **Inspect the diff of the 3 fat_sources** (170193, 171468, 167813) in the
   resolved DB — if any nutrient value changed, investigate before approving
6. **Confirm the two `muscle_organ` cases (heart, tongue) have a documented,
   cited decision** in Task-4's code, not a default fallthrough

### For a future agent extending this plan:

- **Do not add tasks to this plan.** Create a new `plan-gsd-<next-scope>.md`.
- **Reference this plan** via `plan_id: plan-gsd-fdc-nutrient-fix` in the new
  plan's frontmatter.
- **Preserve the backup** `DB_ingredientes.backup_pre_fix.json` — it is the
  audit anchor for any future investigation.
- **If a new ingredient is added to the DB with `category: muscle_organ`**,
  it will raise the same explicit `ValueError` in Task-4's policy check. Do
  not "fix" this by adding it to a silent default bucket — resolve it the
  same way heart/tongue were resolved: look up real physiological data, cite
  a source, and document the decision.

---

## Changelog

| Date | Version | Author | Change |
|---|---|---|---|
| 2026-07-16 | 1.0.0 | Senior SWE Agent | Initial plan. Based on raw evidence from `validacao_evidencia.py` and `validar_fdc_rigoroso.py`. 6 invariants validated (1 removed: I4) + catastrophic FDC mapping discovered (20/23 wrong). |
| 2026-07-16 | 2.0.0 | Claude (review pass) | Translated plan-level prose to English (code/schema/paths/commit messages untouched — see Translation Notes). Rewrote Task-4's vitamin-A policy to branch on the existing `category` field instead of a substring match against `ingredient_id`, after finding it misclassifies `muscle_organ`-category ingredients (heart, tongue) and gets `organ_non_secreting` (tripe) right by the wrong mechanism — confirmed directly against `DB_ingredientes.json`. Added Task-1B (FDC integrity snapshot) and a Step-0 integrity check in Task-7 to catch silent FDC-ID drift between Task-1 and Task-7. Added an explicit tie-break rule and a numeric sanity cross-check to Task-1's fuzzy FDC matcher, closing two previously unspecified decision points. |
| 2026-07-16 | 2.1.0 | Claude (env fix) | v1.0.0/v2.0.0 hardcoded `repo.root: /home/z/my-project`, which does not exist — the real project is at `C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\` on Windows, run via OpenCode Desktop. Rather than substitute one hardcoded path for another, added Task-0: an explicit environment/shell detection step, since OpenCode Desktop on Windows has a documented open bug (GitHub #8396, #5557) where the spawned shell — WSL bash, Git Bash, or PowerShell/cmd.exe — can vary between individual commands, not just once per session. Task-0 confirms a POSIX-like shell is active, resolves `$PROJECT_ROOT` by testing both the Git-Bash-style and WSL-mount-style forms of the real path, and is re-run at the start of every subsequent task rather than trusting a persisted variable across tool calls. All 105 occurrences of the old hardcoded path throughout the plan were replaced with `$PROJECT_ROOT`. |
| 2026-07-16 | 2.2.0 | Claude (Plan A sequencing) | This plan is now sequenced AFTER `plan-mapa-generator-fix` v1.2.0 (MAPA generator fix). Four changes: (1) Added P-PLAN-A precondition — Plan A must be complete and merged before Task-0. (2) Path reconciliation — replaced all `upload/` paths with repo-root paths matching the actual GitHub structure (`build_pipeline.py` at repo root, `data/DB_ingredientes.json`, `tests/test_dimensional_pipeline.py`, etc.). (3) Line number caveat — all line numbers in Tasks 3 and 5 are PRE-Plan-A baselines; Plan A's L1194-1207 modification shifts Plan B's `validate_inputs` target from L1434 to ~L1449, and `convert_as_fed_to_energy_normalized` from L1655 to ~L1670. Added explicit "locate by content using `rg`" instructions. (4) Added Task-8: regenerate MAPA after Task-7 regenerates `DB_ingredientes_RESOLVIDO.json` with corrected FDCs — without this, the MAPA's evidence section would reflect nutrient data from 20 wrong FDCs, defeating Plan A's purpose. Also added Q7 postcondition, P6/P7 preconditions (resolve_usda_nutrients.py existence + Plan A test baseline), and noted that `resolve_usda_nutrients.py` is NOT in the GitHub repo (must be copied from upload/ snapshot or located on user's machine). Updated rollback table, task graph, and acceptance criteria for 9 commits (was 8). |
| 2026-07-17 | 2.3.0 | Claude (holistic multi-specialist review) | Holistic review from 4 specialist perspectives (Senior SWE, Data Analyst, Data Scraper, AI-to-AI Agent-to-Agent). 15 findings total: 4 BLOCKING/CATASTROPHIC, 4 POSITIVE (reduced unnecessary work), 7 MEDIUM/LOW. Critical fixes: (1) S1 — added Task-S1 to add `requests` to `requirements.txt` (resolver imports it but it was undeclared). (2) S2/A1 — added Task-7B to swap resolved DB into `data/DB_ingredientes.json` (build_pipeline.py loads from data/, not scripts/ — without this swap, Plan B's FDC corrections are invisible to the pipeline and Task-8 MAPA regeneration produces zero change). (3) S3 — fixed Task-7 input path from relative `DB_ingredientes.json` to `data/DB_ingredientes.json`. (4) DS2 — added `--probe` step before `--dry-run` in Task-7 (script's own docstring mandates this). (5) DS3 — added `export USDA_API_KEY` re-export in Task-7 (OpenCode shell-variance bug). Positive findings documented: S4 (--generate-mapa calls validate_mapa not validate_inputs — decoupled), DS1 (resolver already has rate limiting/retry), DS4 (resolver handles two API response formats), A3 (Task-5 changes will flow through to MAPA evidence — desired). Added Section 13 with full findings matrix. Updated to 11 commits (was 9). |

---

## Section 13 — Holistic Compatibility Findings Matrix (v2.3.0)

This section documents the 15 findings from the holistic, multi-specialist
review of Plan B against Plan A v1.2.0. Each finding is mapped to the
specialist perspective that identified it, its severity, and the fix applied.

### Findings Summary

| ID | Perspective | Severity | Finding | Fix Applied |
|---|---|---|---|---|
| S1 | Senior SWE | **BLOCKING** | `requirements.txt` missing `requests` — `resolve_usda_nutrients.py` imports it at L48 | New Task-S1: add `requests>=2.28` to `requirements.txt` before any resolver task |
| S2 | Senior SWE | **CATASTROPHIC** | Task-7 writes resolved DB to `scripts/DB_ingredientes_RESOLVIDO.json` but `build_pipeline.py` L37 `JSON_FILES` loads `data/DB_ingredientes.json` — resolved DB never loaded by pipeline | New Task-7B: swap resolved DB into `data/DB_ingredientes.json` after Task-7 |
| S3 | Senior SWE | **BLOCKING** | Task-7 `--input DB_ingredientes.json` is relative path; raw DB is at `data/DB_ingredientes.json` | Fixed to `--input data/DB_ingredientes.json` in Task-7 Step 3 |
| S4 | Senior SWE | POSITIVE | `--generate-mapa` calls `validate_mapa()` (13-check gate), NOT `validate_inputs()` — Task-3 regex check only affects `--runtime` mode | Documented in "Raw DB vs Resolved DB Clarification" section — no code change needed |
| S5 | Senior SWE | MEDIUM | Branch strategy: Plan B must rebase onto post-Plan-A main; line numbers shift +5 to +20 | Already addressed in v2.2 "Line Number Caveat" with "locate by content" instructions |
| D1 | Data Analyst | CLARIFICATION | Raw DB has ZERO `_MCGxIU`/`_MCGXIU` source_refs — suffix only exists in resolved DB (added by resolver during RAE→IU conversion) | New "Raw DB vs Resolved DB Clarification" section documents the distinction |
| D2 | Data Analyst | CONFIRMED | RESOLVIDO DB at `scripts/DB_ingredientes_RESOLVIDO.json` has 7 instances of `_MCGxIU` — confirms Task-2 is correctly targeted | No fix needed — Task-2 already correct |
| D3 | Data Analyst | MEDIUM | No nutrient-value delta quantification — 20 FDC ID changes will alter LP solver results | Out of scope for v2.3 (recommend a follow-up `plan-gsd-nutrient-delta-audit.md`); Task-8 evidence capture will document the new LP values |
| D4 | Data Analyst | LOW | `audit_provenance.json` may be updated by resolver — Plan A's STRUCTURE_CONTRACTS must still pass | Low risk — contracts are structural (list vs dict); adding source_refs doesn't change top-level keys |
| DS1 | Data Scraper | POSITIVE | `resolve_usda_nutrients.py` already has rate limiting: `THROTTLE_SECONDS=0.2`, `MAX_RETRIES=4`, `BASE_BACKOFF=1.5`, `REQUEST_TIMEOUT=15` | Documented in "Raw DB vs Resolved DB Clarification" — no code change needed |
| DS2 | Data Scraper | **BLOCKING** | Task-7 jumps to `--dry-run` without `--probe` first — script's own docstring says "Rode --probe primeiro. Sempre." | Added `--probe` step as Task-7 Step 2 (before dry-run) |
| DS3 | Data Scraper | MEDIUM | USDA API key persistence across OpenCode shell calls — Task-0 addresses `$PROJECT_ROOT` but not `$USDA_API_KEY` | Added `export USDA_API_KEY` re-export in Task-7 Steps 2-3 |
| DS4 | Data Scraper | POSITIVE | Script handles two USDA API response formats (Foundation/SR Legacy vs legacy) | No fix needed — already robust |
| A1 | AI-to-AI | **CATASTROPHIC** | Task-8 (regenerate MAPA) based on false premise — `build_pipeline.py` loads raw DB, not resolved DB; regenerating without DB swap produces zero change | Fixed by Task-7B (swap DB) + Task-8 now depends on Task-7B |
| A2 | AI-to-AI | MEDIUM | Plan A's provenance markers must survive Plan B's `build_pipeline.py` edits | Already in v2.2 Context Boundary; should be verified in Tasks 3 and 5 (noted) |
| A3 | AI-to-AI | POSITIVE | Plan B Task-5 changes `convert_as_fed_to_energy_normalized()` — IS called by LP solver during `capture_live_evidence()` | Desired behavior — Plan A's evidence will honestly report new LP results post-DB-swap |
| A4 | AI-to-AI | LOW | P-PLAN-A doesn't pin to a commit SHA | Acceptable — Plan A v1.2.0 is a version tag, not a commit; executing agent verifies artifacts exist |
| A5 | AI-to-AI | LOW | `reference_cases.py` (Plan A) vs `test_dimensional_pipeline.py` (Plan B Task-6) — disjoint, no conflict | No fix needed |

### Blocking/Catastrophic Findings Detail

#### S1 — Missing `requests` dependency
- **Root cause:** `resolve_usda_nutrients.py` was uploaded as a standalone script; its `import requests` at L48 was never reflected in `requirements.txt`
- **Impact:** Tasks 2, 4, 6, 7 all fail with `ImportError` on a fresh clone
- **Fix:** Task-S1 adds `requests>=2.28` to `requirements.txt` as the first task in the plan

#### S2/A1 — Resolved DB never loaded by pipeline
- **Root cause:** `build_pipeline.py` L37 `JSON_FILES = ["DB_ingredientes.json", ...]` loads from `data/`. Task-7 writes to `scripts/DB_ingredientes_RESOLVIDO.json`. These are different files at different paths.
- **Impact:** Plan B's entire FDC correction effort is invisible to the LP solver, MAPA generator, and `--runtime` mode. The MAPA evidence section would be byte-identical pre- and post-Plan-B.
- **Fix:** Task-7B copies `scripts/DB_ingredientes_RESOLVIDO.json` to `data/DB_ingredientes.json` (after backing up the original). Task-8 then regenerates the MAPA against the swapped DB.

#### S3 — Relative input path
- **Root cause:** v2.2 used `--input DB_ingredientes.json` with `cd $PROJECT_ROOT/upload`. The raw DB is at `data/DB_ingredientes.json`, not repo root.
- **Impact:** `resolve_usda_nutrients.py` fails with `FileNotFoundError`
- **Fix:** Changed to `--input data/DB_ingredientes.json` in Task-7 Step 3

#### DS2 — Missing `--probe` step
- **Root cause:** v2.2 jumped to `--dry-run` without first verifying the USDA API response schema
- **Impact:** If the API response format has changed since the script was written, `extract_nutrient_index()` will silently return empty dicts, producing a resolved DB with `missing` nutrients where there should be `measured` values
- **Fix:** Added `--probe` step as Task-7 Step 2, before dry-run

### v2.3.0 Net Effect

- **Tasks added:** 2 (Task-S1, Task-7B)
- **Tasks modified:** 1 (Task-7: fixed input path, added --probe step, added API key re-export)
- **Preconditions updated:** 1 (P3 now includes `requests`)
- **Postconditions:** Q7 now correctly depends on Task-7B (was depending on Task-7 alone)
- **Commits:** 11 (was 9 in v2.2, was 8 in v2.1, was 7 in v1.0)
- **Blocking fixes applied:** 4 (S1, S2/A1, S3, DS2)
- **Positive findings documented:** 4 (S4, DS1, DS4, A3) — reduced unnecessary work
- **Estimated effort delta:** +0.5 day for Task-S1 + Task-7B; net +0.5 day vs v2.2

---

## Translation Notes (v2.0.0)

- **Translated:** all task titles/objectives, step narration, rationale prose,
  risk register, changelog, task-graph labels, agent handoff protocol.
- **NOT translated / unchanged:** every code block, regex pattern, JSON/YAML
  key, file path, `ingredient_id`, commit message, `source_ref` value, task ID,
  and bash command. These are the plan's actual schema and logic and must
  match the live codebase exactly.
- **NOT translated:** `display_name` fields inside `DB_ingredientes.json`
  (e.g. `"Rim Bovino Cru"`) — these are real Brazilian-market-facing product
  names, not machine identifiers, and were never part of this plan's own text
  to begin with.
- **New code comments** inserted into `.py` files by this plan (Task-4, Task-5)
  are written in English to match the existing comment convention already
  present in `build_pipeline.py` (e.g. `# Mineral antagonism ratio constraints`).
  If the target repo's actual comment convention differs, adjust before
  executing — do not assume this plan's language choice overrides the
  codebase's existing convention without checking.
