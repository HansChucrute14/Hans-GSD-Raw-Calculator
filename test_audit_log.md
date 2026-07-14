# Test Audit Log — chicken_fat_raw Insertion

**Date:** 2026-07-14
**Ingredient added:** chicken_fat_raw
**DB version:** 2.2.0
**Total ingredients:** 22
**Aves count:** 7

## Validation Result

```
VALIDATION RESULT: PASS
Total errors: 0
```

## Test Results (13/13 PASS after hardening)

```
============================= 13 passed in 0.17s ==============================
tests/test_dimensional_pipeline.py::test_5_1_dimensional_round_trip PASSED
tests/test_dimensional_pipeline.py::test_5_2_three_state_preservation PASSED
tests/test_dimensional_pipeline.py::test_5_3_composite_aa_handling PASSED
tests/test_dimensional_pipeline.py::test_5_4_missing_supplement_graceful PASSED
tests/test_dimensional_pipeline.py::test_5_5_unit_rename_spot_check PASSED
tests/test_dimensional_pipeline.py::test_5_6_wildcard_expansion PASSED
tests/test_dimensional_pipeline.py::test_41_key_guarantee PASSED
tests/test_dimensional_pipeline.py::test_registry_covers_solver_nutrients PASSED
tests/test_dimensional_pipeline.py::test_independent_em_precondition PASSED
tests/test_dimensional_pipeline.py::test_5_5_unit_rename_across_ingredients PASSED
tests/test_dimensional_pipeline.py::test_build_matrix_edges PASSED
tests/test_dimensional_pipeline.py::test_all_output_keys_have_valid_status PASSED
tests/test_dimensional_pipeline.py::test_calculate_der_and_envelope PASSED
```

## Anti-Metagaming Verification (Hardened 2026-07-14)

| Test | Gamifiable? | Hardening added |
|---|---|---|
| `test_5_2_three_state_preservation` | **Hard** | Exhaustive count across ALL 22×41=902 entries (measured > missing). Plus spot-checks for each state. |
| `test_5_4_missing_supplement_graceful` | **Hard** | Added random unknown ID `nonexistent_ingredient_xyz` — proves behavior is generic, not hardcoded for 3 known IDs. |
| `test_5_6_wildcard_expansion` | **Hard** | Asserts specific `ingredient_id` strings (`"beef_fat_raw" in`, `"chicken_fat_raw" in`), not just count. |
| `test_41_key_guarantee` | **Hard** | Asserts exact sorted key list match, not just length. Catches wrong-key-name bugs. |
| `test_build_matrix_edges` | **Hard** | Added random unknown ID `zzz_fictional_ingredient_does_not_exist` — proves data_incomplete is generic. |
| `test_independent_em_precondition` | **Hard** | Computes ME from real protein/fat values — wrong values produce wrong EM. Exhaustive (all ingredients). |
| `test_calculate_der_and_envelope` | **Hard** | Gompertz + TER + DER math verifiable by hand. Reads params dynamically from JSON (catches data drift). |
| `test_all_output_keys_have_valid_status` | **Hard** | Exhaustive (22×41=902 entries). Every entry must have valid status. |
| `test_5_1_dimensional_round_trip` | **Hard** | Independent EM + ratio cross-checks that cancel EM entirely. |
| `test_5_3_composite_aa_handling` | **Hard** | Exhaustive (all ingredients), verifies math when both measured. |
| `test_5_5_unit_rename_spot_check` | **Hard** | Independent EM + off-by-1000x detection. |
| `test_5_5_unit_rename_across_ingredients` | **Hard** | 3 different fat profiles, dynamic DB values (not hardcoded). |
| `test_registry_covers_solver_nutrients` | **Hard** | Cross-compares two lists — catches drift. |

All 13 tests now classified **Hard** to gamify after hardening pass.
