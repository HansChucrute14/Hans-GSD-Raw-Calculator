# AUDIT TASK — Verify Every Claim Below Against the Live Repo
## Mode: verification only. No fixes. No interpretation. No "looks fine."
## Output: one evidence table. Nothing else. Do not act on anything you find.

---

## 0. Rules (read before running anything)

1. This is a read-only audit. Do not edit, delete, or create any file except your own
   report. Do not run `git commit`, `git push`, or any pipeline command that writes
   output (`--runtime` is fine to run since it's read-only against current state, but
   do not act on its results beyond reporting them).
2. For every claim below, run the exact command given, and report EXACTLY what it
   returned — full output, not a summary of whether it "looked right."
3. If a command errors, fails to find something, or returns something different from
   the claimed result — that is not a problem for you to fix. Report the mismatch
   verbatim in the `MATCH / MISMATCH / COULD NOT VERIFY` column and move to the next
   claim.
4. Do not skip a claim because a nearby one already "covers it." Every numbered claim
   gets its own row in the output table, checked independently.
5. If you find something concerning that isn't one of the numbered claims below (a
   new bug, an unrelated inconsistency), do NOT fix it and do NOT expand scope. Add
   it as an extra row at the bottom under "UNCLAIMED FINDINGS" and stop there.
6. When finished, output ONE table, per the format in Section 8. No prose before or
   after except a one-line header. Do not add a "summary" or "recommendation"
   section — that is for the human to decide after reading your evidence.

---

## 1. Cleanup pass — file removals

**Claim:** `scripts/migrate_db_3state.py`, `scripts/fix_db_complete.py`,
`scripts/comprehensive_fix.py`, `scripts/quick_fix.py` were deleted.
`scripts/remigrate_db.py` and `scripts/validate_db_ingredientes.py` remain.

```bash
ls scripts/
git log --all --diff-filter=D --summary -- scripts/migrate_db_3state.py scripts/fix_db_complete.py scripts/comprehensive_fix.py scripts/quick_fix.py
```
Report: exact current contents of `scripts/`, and whether git history shows a deletion
commit for each of the 4 named files.

## 2. Cleanup pass — audit artifacts untracked

**Claim:** `audit/baseline_manifest.json`, `audit/cross_ref_index.json`,
`audit/cross_refs_drift.json` are gitignored, not tracked, but still regeneratable.

```bash
cat .gitignore
git ls-files audit/
python build_pipeline.py --audit-mapa
git status --porcelain audit/
```
Report: whether `.gitignore` contains entries for these 3 files, whether `git
ls-files audit/` returns them (it should NOT, if untracked correctly), and whether
`--audit-mapa` regenerates them without error.

## 3. Cleanup pass — `PEN_MANGANESE_NEG` field

**Claim:** `objective_weights.json` has `"solver_penalty_multiplier": null` added to
the `PEN_MANGANESE_NEG` entry, and exactly one associated test was updated from
expecting `missing == ["PEN_MANGANESE_NEG"]` to expecting `missing == []`.

```bash
grep -A5 "PEN_MANGANESE_NEG" objective_weights.json
grep -rn "PEN_MANGANESE_NEG" --include="*.py" --include="*.md" .
```
Report: the exact JSON block for `PEN_MANGANESE_NEG`, and every file/line where it's
referenced elsewhere (should include exactly the test that was claimed to be updated
— quote its current assertion verbatim).

## 4. Cleanup pass — `lp_parameters.schema.json` untouched

**Claim:** this file was NOT modified, because it's loaded at runtime by
`build_pipeline.py`, `audit_mapa.py`, and `inventory.py`.

```bash
git log -p -- lp_parameters.schema.json | head -50
grep -rn "lp_parameters.schema.json" build_pipeline.py
```
Report: whether git history shows any commit touching this file during or after the
cleanup pass, and confirm/deny the runtime-loading claim by showing the actual
loading code, if found.

## 5. Phase 1 — `convert_as_fed_to_energy_normalized()` fix

**Claim:** every nutrient entry in the output is now one of:
`{"status": "measured", "value": <float>}` / `{"status": "missing"}` /
`{"status": "not_applicable"}` / `{"status": "data_incomplete", "anomaly_ref": ...,
"reason": ...}` (for ingredient IDs absent from the DB entirely) — and no nutrient
key is ever silently omitted. All 41 `NUTRIENT_REGISTRY` keys are guaranteed present
per ingredient.

```bash
grep -n "def convert_as_fed_to_energy_normalized" -A 100 build_pipeline.py
pytest tests/test_dimensional_pipeline.py::test_41_key_guarantee -v
pytest tests/test_dimensional_pipeline.py::test_all_output_keys_have_valid_status -v
pytest tests/test_dimensional_pipeline.py::test_5_1_dimensional_round_trip -v
pytest tests/test_dimensional_pipeline.py::test_5_2_three_state_preservation -v
pytest tests/test_dimensional_pipeline.py::test_5_3_composite_aa_handling -v
```
Report: paste the actual function body found. Confirm or deny: is there any `continue`
statement that skips a nutrient without first writing an entry for it into the output
dict? Paste all 5 test results (PASS/FAIL + full output if FAIL).

## 6. Phase 1 — `build_matrix()` unchanged

**Claim:** `build_matrix()` itself was not modified during the Row 1 fix — it
inherits the corrected behavior purely because it stores whatever
`convert_as_fed_to_energy_normalized()` returns.

```bash
grep -n "def build_matrix" -A 40 build_pipeline.py
git log -p --follow -- build_pipeline.py | grep -B2 -A40 "^\+.*def build_matrix"
```
Report: current function body, and whether git history shows this function's body
changing in the same commit(s) that fixed `convert_as_fed_to_energy_normalized()`.
If it changed, quote the diff — the claim would be false.

## 7. Data — fat_source ingredients added

**Claim:** `beef_fat_raw`, `chicken_fat_raw`, `pork_fat_raw` exist in
`DB_ingredientes.json` with `category: "fat_source"`. **This claim has never been
independently verified for data quality — only a count was seen via a test failure.**

```bash
python3 -c "
import json
d = json.load(open('DB_ingredientes.json'))
for grp in d['protein_sources'].values():
    for ing in grp.get('ingredients', []):
        if ing.get('category') == 'fat_source':
            print('---', ing.get('ingredient_id'))
            print(json.dumps(ing, indent=2)[:2000])
"
python build_pipeline.py --validate-db
```
Report: full printed structure of all 3 ingredients (or however many are actually
found — do not assume it's 3). For each: does it have real `source_ref` citations
(e.g. `REF_USDA_FDC_*`), or are values unsourced/estimated/placeholder? Does
`--validate-db` pass with these entries included, with zero errors?

## 8. Constraint reachability — `CSTR_INCL_MIN_FAT_SOURCE` / wildcard expansion

**Claim:** `expand_category_wildcards()` does NOT exist in `build_pipeline.py` as of
the last known state — meaning `_all_fat_source` is never resolved to the concrete
fat_source ingredient IDs anywhere in current code, so the constraint may be
data-satisfiable but not yet pipeline-reachable. **This was explicitly flagged as
UNRESOLVED, not claimed as fixed.**

```bash
grep -n "def expand_category_wildcards" build_pipeline.py
grep -n "_all_fat_source\|_all_muscle_meat" build_pipeline.py formulation_rules.json
grep -n "CSTR_INCL_MIN_FAT_SOURCE" -A 15 constraints.json
```
Report: does `expand_category_wildcards` exist now or not? Is there ANY code path
that turns the literal string `_all_fat_source` into
`[beef_fat_raw, chicken_fat_raw, pork_fat_raw]`? Quote the constraint block again to
reconfirm it's still `HARD_FAIL_INFEASIBLE` at `>= 0.08`.

## 9. Test suite — current full state

**Claim (as of last known run):** 10 passed, 3 failed
(`test_5_4_missing_supplement_graceful`, `test_5_6_wildcard_expansion`,
`test_build_matrix_edges`), and all 3 failures are due to stale pre-fix/pre-migration
expectations, not regressions.

```bash
pytest tests/test_dimensional_pipeline.py -v
git log -p -- tests/test_dimensional_pipeline.py | grep -B10 "0 fat_source ingredients\|kelp is not in DB\|should return empty dict"
```
Report: current full pass/fail count and names. For each of the 3 previously-failing
tests, is it still failing, now passing, or does it no longer exist? If the numbers
differ from 10/3, report the actual numbers — do not reconcile them yourself.

---

## Output format — required, exact

```
# AUDIT REPORT

| # | Claim | Command run | Actual result (verbatim/summarized honestly) | MATCH / MISMATCH / COULD NOT VERIFY |
|---|---|---|---|---|
| 1 | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... |
...
| 9 | ... | ... | ... | ... |

## UNCLAIMED FINDINGS (if any — do not fix, just list)
- ...

## Claims marked COULD NOT VERIFY or MISMATCH (repeat here for visibility)
- ...
```

Stop after producing this. Do not add a conclusion, a recommendation, a "next
steps" section, or an offer to fix anything found. That decision belongs to the
human reading this report.
