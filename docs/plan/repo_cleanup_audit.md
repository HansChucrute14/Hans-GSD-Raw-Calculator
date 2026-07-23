# Repo Cleanup Audit Report — CORRECTED

**Date:** 2026-07-22 | **Status:** REVISED — After deep verification of all claims

---

## Executive Summary

The repo has **58 root-level entries** when it should have ~15. This audit was revised after verifying every claim against actual code dependencies. **3 original claims were wrong** — one would have broken the pipeline.

**Original audit errors found:**
1. ~~Move MAPA file to `docs/`~~ — **WRONG.** `core.py:38` hardcodes `MAPA_FILENAME = "MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md"` and `cli.py` reads/writes at `BASE_DIR / MAPA_FILENAME`. Moving it breaks `--generate-mapa`, `--gate-mapa`, `--audit-mapa`.
2. ~~docs/plan/data/ copies are fine~~ — **UNDERSTATED.** Copies are stale (provenance: 6,527 bytes different; DB: 2,034 bytes different). `audit_orphans.py` reads from these stale copies via `Path(__file__).resolve().parent / path`.
3. ~~Archive category_soft_goals_plan.md~~ — **WRONG.** It's a `ready_for_execution` plan (2,219 lines), not completed.

---

## 1. CRITICAL: Delete Immediately

| File | Size | Why |
|------|------|-----|
| `docs/plan/tsetup-x64.7.0.4.exe` | **54 MB** | **PostgreSQL installer binary.** Should NEVER be in a git repo. 54 megabytes of garbage. Delete immediately. |
| `Continue` | 0 bytes | Empty file, accidental keystroke |
| `out.txt` | 87 bytes | 1 line of garbage output |
| `diffstat.txt` | 722 bytes | Git diff stats from a previous commit |
| `TestOrnith.csproj` | 1.2 KB | C# project file for testing local LLM. Not part of this project |
| `run-ornith.ps1` | 389 bytes | PowerShell script to launch Ornith LLM. Not part of this project |
| `test_ornith.ps1` | 387 bytes | PowerShell script to test Ornith LLM. Not part of this project |
| `0001-remove-dead-code-fix-audit-introspection.patch` | 197 KB | Git patch, already applied. Does not belong at root |
| `opencode.json` | 1.0 KB | **LOCAL ONLY.** Configures local Ornith model. Not part of the project — should be in `~/.config/opencode/` or `.gitignore`d |

---

## 2. DELETE: Root-Level Temp Scripts (17 files)

One-time diagnostic/fix scripts. **None imported by `src/gsd/`** (verified via grep):

| File | Purpose | Evidence safe to delete |
|------|---------|------------------------|
| `add_all_external_refs.py` | One-time provenance fix | Not imported by anything in `src/` |
| `add_cofid_refs.py` | One-time CoFID ref addition | Not imported by anything in `src/` |
| `add_final_orphan_refs.py` | One-time orphan fix | Not imported by anything in `src/` |
| `add_remaining_mechanical_refs.py` | One-time mechanical patch | Not imported by anything in `src/` |
| `apply_and_validate.py` | One-time patch applier | Imports only `build_external_checklist` (also temp) |
| `apply_mechanical_patch.py` | One-time patch applier | Imports only `generate_external_checklist` (also temp) |
| `check_cascade.py` | Cascade config diagnostic | Standalone |
| `check_remaining_orphans.py` | Orphan check | Superseded by `docs/plan/audit_orphans.py` |
| `generate_external_checklist.py` | Checklist generator | **Verified duplicate** of `docs/plan/build_external_checklist.py` |
| `gen_full.py` | Plan generator | One-time use |
| `gen_plan_part1.py` | Plan generator | One-time use |
| `gen_tasks.py` | Task generator | One-time use |
| `rerun_audit.py` | Audit rerunner | One-time use |
| `run_audit.py` | Audit runner | One-time use |
| `temp_check.py` | 6-line ingredient count check | One-time use |
| `tmp_orphan_analysis.py` | Orphan analysis draft | Superseded by `audit_orphans.py` |
| `tmp_orphan_analysis2.py` | Orphan analysis draft v2 | Superseded by `audit_orphans.py` |
| `validate_and_generate_checklist.py` | Checklist + validate | One-time use |
| `verify_mechanical_patch.py` | Patch verifier | One-time use |

---

## 3. DELETE: Root-Level Data Duplicates

| File | Why safe to delete |
|------|-------------------|
| `mechanical_provenance_patch.json` (129 KB) | Already applied to `data/audit_provenance.json`. Canonical copy in `docs/plan/` |
| `runtime_request.json` (176 bytes) | Duplicate of `data/runtime_request.json`. Already in `.gitignore` |
| `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md.orig-bak` (53 KB) | Backup of MAPA. Git has full history |

---

## 4. DELETE: Stale Doc Outputs (Root)

| File | Why safe to delete |
|------|-------------------|
| `ANCHORED_SUMMARY.md` | Session summary from MAPA fix. All phases done |
| `AUDIT_TASK_FOR_HARNESS.md` | One-time audit task, completed |
| `AGENT_FIX_GUIDE_v1.md` | One-time fix guide, fixes already applied |
| `PR_DESCRIPTION.md` | Old PR description for the modular restructure |
| `plan-lp-objective-safety-fix.md` | Completed plan |
| `plan-lp-objective-safety-fix-part2 (1).md` | Completed plan + has `(1)` download artifact suffix |
| `plan-mapa-generator-fix-addendum-v2.md` | Completed addendum |

**Note:** `REVIEW.md` (578 lines) is the adversarial review that spawned the safety fix plans. It has historical value but is not referenced by code. **Archive to `docs/archive/`** rather than delete.

---

## 5. CRITICAL FIX: `docs/plan/data/` Stale Copies

**Problem:** `audit_orphans.py` reads from `docs/plan/data/` via `Path(__file__).resolve().parent / path`. These copies are stale:

| File | Canonical (`data/`) | Copy (`docs/plan/data/`) | Delta |
|---|---|---|---|
| `audit_provenance.json` | 252,731 bytes | 246,204 bytes | **6,527 bytes** |
| `DB_ingredientes.json` | 422,455 bytes | 420,421 bytes | **2,034 bytes** |
| MD5 (provenance) | `012FA3C7...` | `087857D3...` | Different |
| MD5 (DB) | `46C70093...` | `F7B1B0CD...` | Different |

The copies are the **pre-FDC-fix version** (match the backup). Running `audit_orphans.py` audits stale data.

**Fix options:**
1. **Update copies** to match canonical files (simple, preserves script compatibility)
2. **Rewrite `audit_orphans.py`** to use `../../data/` relative paths (cleaner, but requires code change)

**Recommended:** Option 1 (update copies) — simpler, no code changes needed.

---

## 6. KEEP: Files That Must Stay at Root

| File | Why it stays |
|------|-------------|
| `build_pipeline.py` | Active CLI wrapper, `pyproject.toml` entry point |
| `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` | **CODE DEPENDS ON IT.** `core.py:38` hardcodes `MAPA_FILENAME`. `cli.py:53,74,80,91,93,117,128` reads/writes at `BASE_DIR / MAPA_FILENAME`. Moving breaks `--generate-mapa`, `--gate-mapa`, `--audit-mapa` |
| `pyproject.toml` | Active project config |
| `requirements.txt` | Active dependencies |
| `README.md` | Active readme |
| `.gitignore` | Active git rules (needs update after cleanup) |

---

## 7. KEEP: `docs/plan/` Files That Are Still Active

| File | Why keep |
|------|----------|
| `provenance_remediation_plan_hardened.md` | Master plan — 82 EXTERNAL refs remaining |
| `db_validation_pipeline_plan.md` | Pipeline design we just created |
| `external_verification_checklist.json` | Active checklist (96 refs) |
| `audit_orphans.py` | Canonical orphan checker (needs path fix or copy update) |
| `build_external_checklist.py` | Checklist generator (canonical) |
| `generate_mechanical_patch.py` | Mechanical patch generator (canonical) |
| `fix_chicken_fdc_ids.py` | Reference for FDC ID fixes |
| `update_provenance_fdc.py` | Reference for provenance updates |
| `category_soft_goals_plan.md` | **READY FOR EXECUTION** (2,219 lines) — NOT completed |
| `bones_merge_plan.md` | Reference document for bones merge |
| `type-safety-guide.md` | Active documentation (117 lines) |
| `docs_governance_type-safety-implementation-plan_diff.md` | Active diff document |

**Delete from `docs/plan/`:**

| File | Why delete |
|------|-----------|
| `_temp_check_refs.py` | One-time diagnostic (29 lines) |
| `_temp_check_orphans.py` | One-time diagnostic (12 lines, imports from `audit_orphans`) |
| `repo_cleanup_audit.md` | This file (update in place, don't archive) |

---

## 8. CLEAN: Cache Directories

| Directory | Action |
|-----------|--------|
| `__pycache__/` (root) | Delete — contains cached versions of deleted temp scripts |
| `.mypy_cache/` | Delete — regenerated on next `mypy` run |
| `.pytest_cache/` | Delete — regenerated on next `pytest` run |
| `docs/plan/__pycache__/` | Delete — contains `audit_orphans.cpython-313.pyc` |
| `scripts/__pycache__/` | Delete — `scripts/` is otherwise empty |
| `src/gsd/__pycache__/` | **KEEP** — active source code cache |
| `tests/__pycache__/` | **KEEP** — active test cache |

---

## 9. ARCHIVE: Completed Artifacts

| Source | Destination | Why archive |
|--------|-------------|-------------|
| `REVIEW.md` | `docs/archive/REVIEW.md` | Historical adversarial review |
| `tempDB/` | `docs/archive/tempDB/` | Bones merge complete (28 ingredients in canonical DB) |
| `IDEIAS COM CALMA/` | Delete | Empty directory |
| `scripts/` | Delete (just `__pycache__/`) | Directory contains nothing useful |

---

## 10. PROPOSED NEW STRUCTURE

```
Hans-GSD-Raw-Calculator/
├── .github/workflows/ci.yml
├── .gitignore                          (updated)
├── build_pipeline.py                   (thin CLI wrapper)
├── pyproject.toml
├── README.md
├── requirements.txt
├── data/
│   ├── DB_ingredientes.json            (active, canonical)
│   ├── audit_provenance.json           (active, canonical)
│   ├── constraints.json
│   ├── formulation_rules.json
│   ├── growth_energy_skeletal.json
│   ├── lp_parameters_data.json
│   ├── lp_parameters.schema.json
│   ├── objective_weights.json
│   ├── scenarios.json
│   ├── toxicological_limits.json
│   ├── db_ingredientes.schema.json
│   ├── orphan_refs_manifest.json       (reference)
│   └── DB_ingredientes.json.backup-fdc-fix  (reference)
├── src/gsd/
│   ├── __init__.py
│   ├── core.py
│   ├── nutrition.py
│   ├── solver.py
│   ├── mapa.py
│   ├── cli.py
│   ├── types.py
│   └── doc_introspector.py
├── tests/
│   ├── test_cascade_integration.py
│   ├── test_dimensional_pipeline.py
│   ├── test_category_goals_fix.py
│   ├── test_category_goals_disable.py
│   ├── test_tie_break_bound.py
│   ├── test_tie_break_permutation.py
│   └── reference_cases.py
├── docs/
│   ├── MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md  (STAYS AT ROOT — code depends on it)
│   ├── current_implementation_status.md
│   ├── architecture/
│   │   ├── indice_plano_central.md
│   │   ├── sat_princípios.md
│   │   ├── sat_dados_schema.md
│   │   ├── sat_pipeline_fluxo.md
│   │   ├── sat_pipeline_codigo.md
│   │   └── sat_solver_contrato.md
│   ├── governance/
│   │   └── systemic_review_pipeline_vs_satellites.md
│   ├── data-specs/
│   │   ├── INGREDIENTE_TEMPLATE_SPEC.md
│   │   └── PROMPT_PESQUISA_INGREDIENTE.md
│   ├── archive/
│   │   ├── REVIEW.md
│   │   ├── AGENT_FIX_GUIDE_v1.md
│   │   ├── ANCHORED_SUMMARY.md
│   │   ├── AUDIT_TASK_FOR_HARNESS.md
│   │   ├── PR_DESCRIPTION.md
│   │   ├── plan-lp-objective-safety-fix.md
│   │   ├── plan-lp-objective-safety-fix-part2.md
│   │   ├── plan-mapa-generator-fix-addendum-v2.md
│   │   ├── sat_operacional.md
│   │   ├── sat_testes_consolidado.md
│   │   ├── systemic_review_findings.md
│   │   └── tempDB/                     (old snapshots)
│   └── plan/
│       ├── provenance_remediation_plan_hardened.md
│       ├── db_validation_pipeline_plan.md
│       ├── external_verification_checklist.json
│       ├── audit_orphans.py
│       ├── build_external_checklist.py
│       ├── generate_mechanical_patch.py
│       ├── fix_chicken_fdc_ids.py
│       ├── update_provenance_fdc.py
│       ├── category_soft_goals_plan.md
│       ├── bones_merge_plan.md
│       ├── type-safety-guide.md
│       └── docs_governance_type-safety-implementation-plan_diff.md
```

**Root entry count: 15** (down from 58)

---

## 11. IMPACT SUMMARY

| Category | Count | Space Saved |
|----------|-------|-------------|
| Delete critical garbage | 9 files | ~54.4 MB (mostly .exe) |
| Delete root temp scripts | 19 files | ~70 KB |
| Delete root data duplicates | 3 files | ~183 KB |
| Delete root doc outputs | 7 files | ~80 KB |
| Delete docs/plan temp scripts | 2 files | ~2 KB |
| Clean caches | 6 dirs | ~50 KB |
| Archive completed artifacts | 4 items | 0 (reorganized) |
| **Total** | **~50 items** | **~54.8 MB** |

After cleanup: **~15 root entries** instead of 58. Clean separation between active code, data, docs, and archived work.

---

## 12. `.gitignore` Updates Needed

After cleanup, add these patterns:

```gitignore
# Local opencode config (project-specific, not shared)
opencode.json

# Generated MAPA (rebuild via --generate-mapa)
MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md.new.md
MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md.orig-bak

# Stale plan data copies (regenerated by docs/plan/ scripts)
docs/plan/data/

# Binary installers
*.exe

# Patch files (use git am to apply, don't store at root)
*.patch
```

---

## 13. VERIFICATION CHECKLIST

Before executing cleanup, verify these claims:

- [ ] `core.py:38` references `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` — confirmed
- [ ] `cli.py:53,74,80,91,93,117,128` references MAPA at root — confirmed
- [ ] `audit_orphans.py` reads from `docs/plan/data/` — confirmed
- [ ] `docs/plan/data/` copies are stale — confirmed (MD5 differ)
- [ ] No code in `src/gsd/` imports any root-level temp script — confirmed
- [ ] CI only runs `pytest tests/ -v` and `mypy src/gsd/` — confirmed
- [ ] `docs/plan/category_soft_goals_plan.md` is `ready_for_execution` — confirmed
- [ ] `.golden_master/` not referenced by code — confirmed
- [ ] `tempDB/` bones merge complete (28 ingredients in canonical DB) — confirmed
- [ ] `docs/plan/tsetup-x64.7.0.4.exe` is 54 MB — confirmed
