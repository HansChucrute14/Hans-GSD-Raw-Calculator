# Phase 0-zero Pre-flight Sanity Check

## Task: Confirm the F#18 envelope gap is 0.05g (rounding), not 1e-9 g (float)

**Execution Date:** 2026-07-16
**Reference Case:** 5-ingredient selection (beef_muscle_raw, chicken_heart_raw, beef_liver_raw, beef_kidney_raw, salmon_atlantic_raw)

---

## Live Run Output

```
=== DER & Envelope ===
BW=45.0 kg, TER=1216 kcal, k=1.2
DER=1459 kcal, units of 1000kcal=1.459
Envelope: [709, 1459] g (selected_ingredients)

=== Built matrix for 5 ingredients ===
  [LP solver runs...]
  Level 1: relax_tiers = set()
  Level 2: relax_tiers = {'envelope_soft', 'adequacy_soft'}
```

---

## AssertionError Traceback

```
File "build_pipeline.py", line 3434, in main
    validate_output(result, data, der_env)
File "build_pipeline.py", line 3063, in validate_output
    assert env["min_total_g"] <= total_g <= env["max_total_g"], \
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Total grams 708.8 outside envelope [708.8523141483524, 1459.4481534632191]
```

---

## Gap Analysis

| Metric | Value |
|--------|-------|
| `total_g` | 708.8 g |
| `min_total_g` | 708.8523141483524 g |
| `max_total_g` | 1459.4481534632191 g |
| `gap_g = min_total_g - total_g` | **0.0523141483524 g** |
| `gap_g` as percentage of `min_total_g` | 0.0074% |

**Classification: rounding-scale** (0.01–0.5g range)

---

## Root Cause Analysis

Per the D2 v1.2 specialist review:

1. **Rounding Site (L2857):** `build_output_contract()` rounds each `grams_per_day` to 1 decimal place via `round(grams, 1)`.

2. **Sum-site (L3061):** `validate_output()` computes `total_g = sum(a["grams_per_day"] for a in result["allocations"])` — this sums the **rounded** values.

3. **Envelope Source:** `env["min_total_g"]` is derived from `der_env.min_total_g`, which retains **full float precision** (708.8523141483524g).

4. **The Gap:** The difference (0.052g) is the cumulative rounding error from rounding 5 allocations to 0.1g precision. This is **not** a floating-point precision issue (1e-9g scale).

---

## Conclusion

**Gap classification: rounding-scale**

Proceed with **Option A** or **Option B** (rounding-scale fixes) as documented in `docs/phase0a-tolerance-design.md`.

**DO NOT** use generic `math.isclose()` with `rel_tol=1e-6, abs_tol=1e-9` — this would mask real envelope violations up to 1e-9g, which is the R8 trap.

---

## Next Steps

1. Phase 0a-1: Write rounding-fix design document (Option A vs Option B)
2. Phase 0a-2: Call-site audit of `validate_output()` and `round()` calls
3. Phase 0c-1: Audit all rounding sites and document rounding policy
4. Phase 0b-1: Apply the chosen fix to `build_pipeline.py`