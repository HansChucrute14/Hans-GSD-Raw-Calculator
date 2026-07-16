# Phase 0a-2: Call-Site Audit of validate_output() AND round() at L2857

## Executive Summary

This audit identifies all callers of `validate_output()` and all `round(..., 1)` call sites in `build_pipeline.py`. It classifies risks for Option A implementation.

---

## 1. validate_output() Callers

| # | File | Line | Context | Risk |
|---|------|------|---------|------|
| 1 | `build_pipeline.py` | 3434 | `validate_output(result, data, der_env)` in `main()` | **LOW** - Direct call, result consumed for assertion |

**Call Chain:**
```
main() at L3434
  └─> validate_output(result, data, der_env)
        └─> asserts envelope bounds (L3063)
```

**Conclusion:** Only 1 caller. Adding `_unrounded_total_g` field to result dict is safe — the `or` fallback in Option A handles results built without the field.

---

## 2. All round(..., 1) Call Sites

| # | Line | Field | Context | Risk |
|---|------|-------|---------|------|
| 1 | L2566 | `pct_of_min` | Nutrient result display | **LOW** - Display only |
| 2 | L2720 | `pct_of_min` | Gap calculation | **LOW** - Display only |
| 3 | L2806 | `ratio_pct` | Ratio display | **LOW** - Display only |
| 4 | L2810 | `pct_of_min` | Ratio gap display | **LOW** - Display only |
| 5 | L2857 | `grams_per_day` | Allocation output | **HIGH** - Used in envelope validation |
| 6 | L2858 | `pct_of_total` | Allocation output | **HIGH** - Compounds rounding error |
| 7 | L2859 | `kcal_per_day` | Allocation output | **LOW** - Not used in validation |
| 8 | L2984 | `grams_needed_for_der` | Diagnostic analysis | **LOW** - Display only |
| 9 | L3176 | `pct_of_min` | Fat adequacy check | **LOW** - Display only |
| 10 | L3183 | `estimated_fat_at_structural_min` | Fat adequacy check | **LOW** - Display only |

**Critical Sites (RISK: HIGH):**
- **L2857:** `grams_per_day` - directly causes F#18 gap
- **L2858:** `pct_of_total` - compounds rounding error for allocations

---

## 3. Rounding Precision Analysis

Current precision: 0.1g (1 decimal)

**Is 0.1g the right precision?**

For clinical use:
- Daily food: ~709g → 0.1g is 0.014% precision (acceptable)
- Trace minerals: selenium ~0.03mg/day → 0.1g food precision is adequate
- For individual ingredients, 0.1g is clinically meaningful

**Recommendation:** Retain 0.1g precision for `grams_per_day`. The error is bounded by `n_allocs × 0.05g`.

---

## 4. Conclusion

**apply Option A**

Rationale:
1. Only 1 caller of `validate_output()` (LOW risk for adding `_unrounded_total_g`)
2. The rounding issue is isolated to L2857-2859 in `build_output_contract()`
3. Option A fixes the root cause; Option B would mask real violations

**Implementation Notes:**
- Add `result["_unrounded_total_g"] = raw_total_g` at L2843 (before rounding loop)
- Modify L3061 to use `result.get("_unrounded_total_g") or sum(...)`
- Add comment block referencing this audit document