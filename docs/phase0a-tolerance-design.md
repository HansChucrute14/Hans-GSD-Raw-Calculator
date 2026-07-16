# Phase 0a-1: Rounding-Fix Design Document

## Executive Summary

The F#18 envelope validation bug is caused by a **rounding-scale gap** of 0.052g, NOT a float-precision gap of 1e-9g. This document justifies the fix strategy.

---

## 1. Empirical Gap Value (from Phase 0-zero)

| Metric | Value |
|--------|-------|
| `total_g` | 708.8 g |
| `min_total_g` | 708.8523141483524 g |
| `gap_g` | **0.0523141483524 g** |
| Gap classification | **rounding-scale** (0.01–0.5g range) |

---

## 2. Root Cause

The gap originates from two sites in `build_output_contract()`:

1. **L2857: Rounding allocations**
   ```python
   allocations.append({
       "grams_per_day": round(grams, 1),  # Rounds to 0.1g
       "pct_of_total": round(grams / total_g * 100, 1),
       "kcal_per_day": round(kcal, 1),
   })
   ```

2. **L3061: Summing rounded values in validate_output()**
   ```python
   total_g = sum(a["grams_per_day"] for a in result["allocations"])
   ```

The `total_g` computed from rounded allocations differs from the unrounded `sum(x_vals.values())` used to compute the envelope bounds.

---

## 3. Fix Options

### Option A (PREFERRED): Retain unrounded total

**Strategy:** Compute `raw_total_g = sum(x_vals.values())` BEFORE rounding, store it as `result["_unrounded_total_g"]`, and have `validate_output()` use that field.

**Code Changes:**

In `build_output_contract()` (around L2843):
```python
# Compute raw total BEFORE rounding
raw_total_g = sum(x_vals.values())
result["_unrounded_total_g"] = raw_total_g

# Existing rounding loop
for iid, grams in x_vals.items():
    allocations.append({
        "ingredient_id": iid,
        "grams_per_day": round(grams, 1),
        ...
    })
```

In `validate_output()` (L3061-3063):
```python
total_g = result.get("_unrounded_total_g") or sum(a["grams_per_day"] for a in result["allocations"])
env = der_info.as_envelope_dict()
assert env["min_total_g"] <= total_g <= env["max_total_g"], ...
```

**Pros:**
- Fixes the root cause (rounding at wrong time)
- Exposes `_unrounded_total_g` for downstream audit
- No tolerance masking real violations

**Cons:**
- Adds a private field to the result dict
- Requires caller awareness (currently only `validate_output()`)

---

### Option B (FALLBACK): Explicit rounding tolerance

**Strategy:** Add `rounding_tolerance = n_allocs * 0.05 + 1e-9` to the comparison.

**Code Changes (L3063):**
```python
n_allocs = len(result["allocations"])
rounding_tol = n_allocs * 0.05 + 1e-9
assert env["min_total_g"] - rounding_tol <= total_g <= env["max_total_g"] + rounding_tol, ...
```

**Pros:**
- Minimal code change
- Mathematically honest (N × 0.05g cumulative rounding error)

**Cons:**
- Still uses rounded `total_g` (masks real violations up to tolerance)
- Tolerance is a band-aid, not a fix

---

### Option C (FORBIDDEN): Generic `math.isclose()`

**Strategy:** Replace comparison with `math.isclose(total_g, env["min_total_g"], rel_tol=1e-6, abs_tol=1e-9)`.

**Why FORBIDDEN:**
- This would mask real envelope violations up to 1e-9g
- The R8 trap: tolerance hides drift, not just rounding
- Does not distinguish between float error and intentional violation
- Biologically, 0.05g rounding error is acceptable, but 0.05g intentional violation is NOT

---

## 4. Recommendation

**Use Option A (PREFERRED).**

Rationale:
1. Fixes the root cause, not the symptom
2. Exposes `_unrounded_total_g` for downstream audit
3. No tolerance masking real violations
4. The `or` fallback preserves backward compatibility with results built without the unrounded field

---

## 5. Biological Relevance

For the reference animal (45kg German Shepherd puppy):
- Daily food: ~709g
- Rounding error: 0.05g
- Error as percentage: 0.007%

**Conclusion:** 0.05g rounding error on total food is biologically negligible. However, for trace nutrients (selenium, iodine) at SUL boundaries, the rounding on `pct_of_total` at L2858 could compound — addressed by Phase 0c-1 rounding policy audit.