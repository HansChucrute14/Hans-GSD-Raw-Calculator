# Phase 0c-1: Rounding Policy Audit

## Executive Summary

This document audits all rounding sites in `build_pipeline.py` and recommends a unified rounding policy.

---

## 1. All round() Call Sites in build_pipeline.py

| # | Line | Statement | Field | Precision | Downstream Consumers |
|---|------|-----------|-------|-----------|----------------------|
| 1 | L2566 | `round(pct_of_min, 1)` | `pct_of_min` | 0.1 | JSON output |
| 2 | L2720 | `round(achieved / target_min * 100, 1)` | `pct_of_min` | 0.1 | JSON output |
| 3 | L2806 | `round(ratio / bound_ratio * 100, 1)` | `ratio_pct` | 0.1 | JSON output |
| 4 | L2810 | `round(ratio / bound_ratio * 100, 1)` | `pct_of_min` | 0.1 | JSON output |
| 5 | L2857 | `round(grams, 1)` | `grams_per_day` | 0.1 | JSON output, validate_output() |
| 6 | L2858 | `round(grams / total_g * 100, 1)` | `pct_of_total` | 0.1 | JSON output |
| 7 | L2859 | `round(kcal, 1)` | `kcal_per_day` | 0.1 | JSON output |
| 8 | L2984 | `round(total_grams_for_der, 1)` | `grams_needed_for_der` | 0.1 | JSON output |
| 9 | L3176 | `round(100 * total_fat_est / aafco_fat_min, 1)` | `pct_of_min` | 0.1 | JSON output |
| 10 | L3183 | `round(total_fat_est, 1)` | `estimated_fat_at_structural_min` | 0.1 | JSON output |

---

## 2. Rounding Precision Analysis

### 2.1 grams_per_day (L2857)

**Current:** 0.1g precision
**Issue:** Sum of rounded values ≠ unrounded sum (F#18)
**Impact:** HIGH - causes envelope validation failure

### 2.2 pct_of_total (L2858)

**Current:** 0.1% precision
**Issue:** Computed FROM rounded grams - compounds error
**Impact:** MEDIUM - trace nutrients at SUL boundaries may appear compliant when not

### 2.3 All other fields

**Current:** 0.1 precision (where applicable)
**Issue:** None identified
**Impact:** LOW - display only, not used in validation

---

## 3. Inconsistencies Flagged

| Inconsistency | Location | Issue |
|---------------|----------|-------|
| Rounding before validation | L2857, L3061 | `validate_output()` sums rounded values but compares against unrounded envelope |
| pct_of_total from rounded grams | L2858 | Compounds rounding error for percentage calculations |

---

## 4. Recommended Unified Rounding Policy

**Policy Statement:**

> Round only at the presentation layer (JSON output), never at the computation layer. Internal calculations must use full precision. The `_unrounded_total_g` field should be exposed for downstream audit purposes.

**Implementation:**

1. **Computation Layer (internal):** Use full float precision
2. **Presentation Layer (output):** Round to 0.1g for `grams_per_day`, 1% for percentages
3. **Validation Layer:** Use unrounded values from computation layer

**Specific Actions:**

1. **L2857:** Retain `round(grams, 1)` for output - this is correct for presentation
2. **L2858:** Compute `pct_of_total` from unrounded grams internally, round only for output
3. **L3061:** Use `result.get("_unrounded_total_g")` instead of summing rounded values
4. **All other sites:** No change needed (display only, not used in validation)

---

## 5. Out of Scope

The following items are **out of scope** for this plan and require a separate follow-up:

1. **Trace nutrient SUL boundary analysis:** Whether 0.1g rounding on `pct_of_total` affects trace minerals at SUL boundaries needs a separate risk assessment
2. **UI display precision:** Whether the frontend should display rounded or unrounded values
3. **Audit trail format:** Whether `_unrounded_total_g` should be included in `solver_output.json` (currently a private field)

---

## 6. Summary Table

| Site | Current Precision | Recommended | Change Required |
|------|-------------------|-------------|-----------------|
| grams_per_day | 0.1g | 0.1g | No (but fix validation using it) |
| pct_of_total | 0.1% | 0.1% | No (compute from unrounded) |
| pct_of_min | 0.1% | 0.1% | No |
| kcal_per_day | 0.1 | 0.1 | No |
| All others | 0.1 | 0.1 | No |

**Key Fix:** The envelope validation at L3063 must use unrounded total grams, not the sum of rounded allocations.