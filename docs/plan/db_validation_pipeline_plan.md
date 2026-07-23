# DB Validation & Update Pipeline — Implementation Plan

**Version:** 1.0.0 | **Date:** 2026-07-22 | **Status:** PLANNED | **Target:** Production-grade automated validation

---

## 1. Problem Summary

The DB has 28 ingredients with nutrients from 10+ different sources. Current state:

- **202 MECHANICAL orphan refs** resolved (patch already applied)
- **96 EXTERNAL refs** remaining — need verification against official sources
- **3 low-coverage ingredients** (chicken_blood 11.6%, chicken_foot_tendon 19%, chicken_kidney 28.6%) with 30-38 estimated nutrients each
- **5 bone ingredients** with 3-source composition (FDC meat+skin + DogsFirst.ie Ca/P + Monica Segal bone%)
- No automated way to detect future data drift or verify new ingredients
- Known FDC ID bugs already fixed (chicken_back/chicken_neck swap)

**Zero tolerance**: this is a calculator where a wrong value can kill a puppy. Any deviation from source data is unacceptable.

---

## 2. Architecture — 4 Layers

```
Layer 4: CLI / Reports        run_validate.py → human-readable reports
Layer 3: Pipeline Engine      orchestration, backup, rollback, git, audit
Layer 2: Validators           FDC, CoFID, bone composite, coverage analysis
Layer 1: Source Fetchers      FDC API, CoFID, cached literature data
```

**File structure:**

```
src/gsd/validation/
    __init__.py
    config.py                     # API keys, tolerances, paths
    ingredient_registry.py        # Per-ingredient source metadata (28 entries)
    fetchers/
        __init__.py
        base.py                   # Abstract Fetcher interface
        fdc_fetcher.py            # USDA FDC API (with API key, rate limiting)
        cofid_fetcher.py          # CoFID UK open data
        cached_fetcher.py         # Literature/Monica Segal/DogsFirst.ie (pre-cached)
    validators/
        __init__.py
        base.py                   # Abstract Validator → ValidationResult
        fdc_validator.py          # Compares DB vs FDC per nutrient
        cofid_validator.py        # Compares DB vs CoFID per nutrient
        bone_validator.py         # Multi-source: validates each layer + final composite
        coverage_analyzer.py      # Identifies ingredients with <50% measured coverage
        source_searcher.py        # Searches FDC API for better matches on estimated nutrients
    pipeline/
        __init__.py
        orchestrator.py           # Main pipeline: fetch → validate → diff → decide → apply
        diff_generator.py         # Human-readable diff reports (markdown)
        backup_manager.py         # Backup before apply, rollback on failure
        git_manager.py            # Auto-commit with conventional commit messages
        audit_logger.py           # Structured audit trail (JSON + human-readable)

scripts/
    validate_db.py                # CLI entry point (runs from repo root with -X utf8)
```

---

## 3. Ingredient Source Registry (`ingredient_registry.py`)

A declarative JSON-embedded registry for all 28 ingredients specifying:

- `source_type`: how nutrients were sourced (FDC, CoFID, bone_composite, literature, estimated)
- `fdc_ids`: list of FDC IDs used (with role: "primary", "fallback", "cut_match")
- `meat_fraction`: for bone ingredients (back=0.56, neck=0.64, wing=0.60, etc.)
- `bone_sources`: DogsFirst.ie (Ca/P) + Monica Segal (bone%)
- `cofid_nutrients`: which nutrients came from CoFID
- `estimated_nutrients`: which nutrients are estimated (for low-coverage ingredients)
- `risk_level`: LOW / MEDIUM / HIGH / CRITICAL

### Example: bone ingredient (`chicken_back_raw`)

```python
{
    "ingredient_id": "chicken_back_raw",
    "source_type": "bone_composite",
    "fdc_ids": [
        {"fdc_id": 171469, "role": "primary",
         "description": "Chicken, broilers or fryers, back, meat and skin, raw"}
    ],
    "meat_fraction": 0.56,
    "bone_sources": {
        "ca_p": {"source": "DogsFirst.ie", "ref": "REF_DOGSFIRST_IE"},
        "bone_pct": {"source": "Monica Segal", "ref": "REF_MC_MONICA_SEGAL"}
    },
    "cofid_nutrients": [],
    "estimated_nutrients": [],
    "risk_level": "MEDIUM"
}
```

### Example: low-coverage ingredient (`chicken_blood_raw`)

```python
{
    "ingredient_id": "chicken_blood_raw",
    "source_type": "fdc_mixed",
    "fdc_ids": [
        {"fdc_id": 175668, "role": "primary",
         "description": "Chicken, blood, raw"}
    ],
    "meat_fraction": None,
    "fdc_coverage_pct": 11.6,
    "estimated_nutrients": [
        "arginine_g", "histidine_g", "isoleucine_g", "leucine_g",
        "lysine_g", "methionine_g", "phenylalanine_g", "threonine_g",
        "tryptophan_g", "valine_g", "linoleic_acid_g",
        "ala_alpha_linolenic_acid_g", "ara_arachidonic_acid_g",
        "epa_plus_dha_g", "calcium_g", "phosphorus_g", "magnesium_g",
        "sodium_g", "potassium_g", "iron_mg", "copper_mg",
        "manganese_mg", "zinc_mg", "selenium_mg", "vitamin_a_iu",
        "vitamin_d3_iu", "vitamin_e_iu", "thiamine_b1_mg",
        "riboflavin_b2_mg", "pantothenic_acid_b5_mg", "niacin_b3_mg",
        "pyridoxine_b6_mg", "folic_acid_b9_mg", "cobalamin_b12_mg"
    ],
    "risk_level": "CRITICAL",
    "search_recommended": True
}
```

---

## 4. Source Fetchers

### 4.1 FDC Fetcher (`fdc_fetcher.py`)

- Uses FDC API v1 with API key
- Rate limiting: max 30 req/hour (conservative, key allows more)
- Returns normalized `{nutrient_id: value_per_100g}` for a given FDC ID
- Handles FDC nutrient ID to solver nutrient ID mapping (150+ FDC nutrient IDs mapped to 41 solver nutrients)
- Caches results to disk (`docs/plan/data/fdc_cache/`) to avoid re-fetching
- Handles HTTP errors gracefully (404 for invalid FDC IDs like the pork_rib 100088 case)

### 4.2 CoFID Fetcher (`cofid_fetcher.py`)

- Downloads CoFID UK open data (CSV/XML from gov.uk)
- Maps CoFID nutrient names to solver nutrient IDs
- Caches to disk (`docs/plan/data/cofid_cache/`)
- No API key needed (UK government open data)

### 4.3 Cached Fetcher (`cached_fetcher.py`)

- Pre-cached values for:
  - Monica Segal bone% composition
  - DogsFirst.ie Ca/P values
  - Milagres2020 iodine values
  - Schweigert1943 biotin values
  - WholeFoodCatalog values
  - Frida (Swedish) values
  - Matvaretabellen (Norwegian) values
- Stored in `docs/plan/data/literature_cache.json`
- Human-curated, not auto-fetched

---

## 5. Validators

### 5.1 FDC Validator (`fdc_validator.py`)

For each nutrient with `source_ref = REF_USDA_FDC_<id>`:

1. Fetch FDC nutrient panel for that ID
2. Compare DB value (as_fed/100g) with FDC value (per100g)
3. For bone ingredients: compare `DB_value = FDC_value * meat_fraction` (expected derived value)
4. Deviation classification:

| Deviation | Threshold | Meaning |
|-----------|-----------|---------|
| CLEAN | = 0% | Exact match |
| ROUNDING | > 0% and ≤ 0.1% | Rounding difference |
| SMALL_DRIFT | > 0.1% and ≤ 1% | Minor data drift |
| MISMATCH | > 1% | Significant discrepancy |
| MISSING | No source value | Source doesn't have this nutrient |

### 5.2 CoFID Validator (`cofid_validator.py`)

Same flow as FDC but for `REF_COFID_*` refs. 46 refs, 1 occurrence each.

### 5.3 Bone Composite Validator (`bone_validator.py`) — Both Layers

**Layer 1 — Source validation (independent):**
- Validate FDC base values independently (meat+skin raw)
- Validate DogsFirst.ie Ca/P values independently
- Validate Monica Segal bone% independently
- Each source is checked against its own authoritative origin

**Layer 2 — Final value validation (composite):**
- Compute expected bone-in value: `FDC_value * meat_fraction + bone_source_value * bone_fraction`
- Compare with DB value
- Flag if composite doesn't match expected
- This catches calculation errors in the composition step

### 5.4 Coverage Analyzer (`coverage_analyzer.py`)

- Identifies ingredients with FDC coverage < 50%
- Currently flags: chicken_blood (11.6%), chicken_foot_tendon (19%), chicken_kidney (28.6%)
- Reports: which nutrients are estimated, what sources exist, recommendation
- Run on every validation pass (catches new low-coverage ingredients)

### 5.5 Source Searcher (`source_searcher.py`)

For each estimated nutrient in a low-coverage ingredient:

1. Search FDC API by ingredient name + nutrient category
2. Find FDC entries with the missing nutrient
3. Score by: same animal species, same organ type, same preparation (raw)
4. Report recommendations (never auto-apply — always flag for human)
5. Human must verify: cut match, preparation match, freshness of source data

---

## 6. Pipeline Engine

### 6.1 Orchestrator Flow (`orchestrator.py`)

```
1. LOAD DB + ingredient_registry + config
2. FOR each ingredient in registry:
   a. FETCH source data (FDC/CoFID/cached) per ingredient_registry
   b. VALIDATE each nutrient against source
   c. CLASSIFY deviations (CLEAN/ROUNDING/SMALL_DRIFT/MISMATCH/MISSING)
   d. GENERATE per-ingredient diff
3. AGGREGATE all diffs
4. IF coverage_analyzer flagged ingredients:
   a. SEARCH for better sources
   b. INCLUDE search results in report
5. GENERATE human-readable report (markdown)
6. IF auto-apply mode:
   a. BACKUP DB + provenance
   b. APPLY auto-correctable changes (ROUNDING + SMALL_DRIFT)
   c. VALIDATE DB (orphan audit + schema check)
   d. IF validation passes: GIT COMMIT with professional message
   e. IF validation fails: ROLLBACK + report error
7. FLAG MISMATCH + MISSING for human review
```

### 6.2 Backup Manager (`backup_manager.py`)

- Before any apply: `cp data/DB_ingredientes.json data/DB_ingredientes.json.backup-{timestamp}`
- Before any apply: `cp data/audit_provenance.json data/audit_provenance.json.backup-{timestamp}`
- On failure: restore from backup
- Retains last 10 backups (circular, oldest deleted)
- Backup naming: `{filename}.backup-{YYYYMMDD-HHMMSS}`

### 6.3 Git Manager (`git_manager.py`)

Auto-commit with conventional commits format:

```
fix(db): validate FDC nutrient values for {ingredient_id}

Source: FDC API (key verified)
Nutrients verified: {count}
Changes applied: {count}
Deviations flagged: {count}

Co-Authored-By: GSD Validation Pipeline
```

Rules:
- Separate commits for: data fixes, provenance updates, schema changes
- Never commits without validation passing
- Never force-pushes
- Never amends existing commits
- Always runs orphan audit before commit

### 6.4 Audit Logger (`audit_logger.py`)

Two output formats:

**1. Structured JSON** (`docs/plan/data/validation_audit_{timestamp}.json`):
```json
{
    "timestamp": "2026-07-22T12:00:00Z",
    "pipeline_version": "1.0.0",
    "summary": {
        "ingredients_checked": 28,
        "nutrients_checked": 1148,
        "deviations_found": 12,
        "auto_applied": 8,
        "flagged_for_review": 4
    },
    "ingredient_results": [...],
    "search_results": [...],
    "git_commits": [...]
}
```

**2. Human-readable Markdown** (`docs/plan/data/validation_report_{timestamp}.md`):
- Summary table
- Per-ingredient breakdown with FDC coverage, deviations, actions
- Source search results for low-coverage ingredients
- Git commit hashes for traceability

---

## 7. Deviation Handling — Zero Tolerance

| Deviation | Threshold | Action | Git Commit |
|-----------|-----------|--------|------------|
| CLEAN | = 0% | Skip | None |
| ROUNDING | ≤ 0.1% | Auto-apply | `fix(db):` |
| SMALL_DRIFT | 0.1% – 1% | Auto-apply + warning | `fix(db):` |
| MISMATCH | > 1% | Flag for human review | None (pending) |
| MISSING | No source value | Flag + search | None (pending) |
| ESTIMATED | Low coverage | Search FDC | None (pending) |

**Zero tolerance means:** no value is silently accepted. Every non-zero deviation is recorded. Auto-applied deviations (ROUNDING/SMALL_DRIFT) are still committed with full audit trail. MISMATCH always requires human approval.

---

## 8. Implementation Order

### Phase 1: Foundation (no external API calls)
1. `ingredient_registry.py` — source metadata for all 28 ingredients
2. `config.py` — API keys, tolerances, paths
3. `fetchers/base.py` — abstract interface
4. `validators/base.py` — ValidationResult dataclass
5. `validators/coverage_analyzer.py` — identify low-coverage ingredients
6. `pipeline/diff_generator.py` — human-readable diff format
7. `pipeline/audit_logger.py` — structured + markdown logging

### Phase 2: FDC Integration
1. `fetchers/fdc_fetcher.py` — FDC API with rate limiting + caching
2. FDC nutrient ID to solver nutrient ID mapping (150+ mappings)
3. `validators/fdc_validator.py` — DB vs FDC comparison
4. `pipeline/backup_manager.py` — backup/restore/rollback

### Phase 3: Pipeline + Git
1. `pipeline/orchestrator.py` — main flow
2. `pipeline/git_manager.py` — conventional commits
3. `scripts/validate_db.py` — CLI entry point
4. Integration test: run against real DB, verify 0 regressions

### Phase 4: CoFID + Bone Composite
1. `fetchers/cofid_fetcher.py` — CoFID UK data
2. `validators/cofid_validator.py` — DB vs CoFID comparison
3. `validators/bone_validator.py` — two-layer bone validation
4. `fetchers/cached_fetcher.py` — literature cache

### Phase 5: Source Search + Low Coverage
1. `validators/source_searcher.py` — FDC API search for estimated nutrients
2. Run against chicken_blood, chicken_foot_tendon, chicken_kidney
3. Generate recommendations report

### Phase 6: Integration + Remaining Refs
1. Run full pipeline against all 96 EXTERNAL refs
2. Auto-apply verified changes
3. Generate final report with remaining human-review items
4. Update `external_verification_checklist.json` with verification_status

---

## 9. Key Design Decisions

1. **Registry-driven, not hardcoded** — adding a new ingredient = adding one entry to `ingredient_registry.py`. Zero code changes for new ingredients.

2. **Fetch-then-compare, never compute from DB** — the pipeline fetches the SOURCE value independently, then compares with DB. It never derives what the DB "should" contain from the DB itself.

3. **Two backup mechanisms** — file-level backup (for rollback) + git history (for audit). Both are always created before any apply.

4. **Auto-apply only ROUNDING + SMALL_DRIFT** — these are safe to auto-correct because the deviation is tiny and the source is verified. MISMATCH always needs human judgment.

5. **Search never auto-applies** — the source searcher finds BETTER sources for estimated nutrients, but never applies them. Human must review because: (a) the found source might be for a different cut/preparation, (b) the estimated value might be intentionally conservative.

6. **Bone validation is two-layer** — validates each source independently (catches source-level errors), then validates the composite (catches calculation errors). This is critical because bone ingredients combine 3 data sources.

7. **FDC ID verification is first** — before comparing nutrient values, verify that each FDC ID actually refers to the correct food item. The chicken_back/chicken_neck swap proves this is not theoretical.

8. **No retry on failed lookups** — if FDC API returns 404 or CoFID has no data, flag as MISSING. Never retry-guess to avoid converging on a plausible-but-wrong match.

---

## 10. Scope Estimate

| Component | Lines | Files |
|-----------|-------|-------|
| ingredient_registry.py | ~300 | 1 |
| config.py | ~50 | 1 |
| fetchers (3) | ~400 | 4 |
| validators (5) | ~600 | 6 |
| pipeline (4) | ~500 | 5 |
| CLI + tests | ~300 | 4 |
| **Total** | **~2150** | **~21** |

---

## 11. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FDC API rate limiting | Slow validation | Cache aggressively, batch by ingredient |
| FDC ID 100088 (pork_rib) 404 | Cannot validate pork_rib | Flag as MISSING, find correct FDC ID manually |
| CoFID format changes | Fetcher breaks | Pin to specific CoFID release version |
| Bone composite math errors | Wrong expected values | Two-layer validation catches this |
| Git commit on dirty repo | Unintended changes | Always run `git status` before commit, never force |
| Low-coverage ingredients have no better source | Estimated values remain | Document as LIMITATION, flag in reports |

---

## 12. Integration with Existing Code

- **`src/gsd/validation/`** is a new subpackage of the existing `src/gsd/` package
- **`scripts/validate_db.py`** is a thin CLI wrapper (like `build_pipeline.py`)
- **`validate_inputs()` in `nutrition.py`** gains an optional `strict=True` mode that runs the full validation pipeline
- **`load_all_jsons()` in `core.py`** is unchanged — the validation pipeline reads the same JSONs
- **Existing tests** must continue to pass — the validation pipeline is additive, not modifying existing behavior

---

## 13. Next Steps (When Ready to Implement)

1. Start with Phase 1 (Foundation) — no external dependencies, can be built and tested immediately
2. Build `ingredient_registry.py` first — this is the data foundation everything else depends on
3. Then `coverage_analyzer.py` — immediately useful to quantify the problem
4. Then FDC fetcher + validator — highest leverage (5 FDC IDs cover 174 occurrences)
