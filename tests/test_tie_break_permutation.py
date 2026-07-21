"""Ingredient-ID permutation regression test (R-03, Plan Part 2 Task 3-3).

Proves the deterministic tie-break cannot let an arbitrary ingredient ID
influence a nutrition-constrained decision: two nutritionally-identical
ingredients that swap IDs must produce an identical nutritional outcome
(same total grams, same per-nutrient values). Only which arbitrary ID
carries the grams may differ.

Given Task 3-0's confirmation that the tie-break is already structurally
gated to the final non-fixed stage (and Task 3-2's runtime bound keeps it
negligible), this is a CONFIRMING regression test: it must pass against the
current code and would fail if a future change let IDs leak into the
protected (fixed-optimum) objectives.

AAA+A pattern.
"""

import copy
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from gsd.core import load_all_jsons, AnimalInput
from gsd.nutrition import calculate_der_and_envelope, build_matrix, get_ingredient_by_id
from gsd.solver import build_lp_problem, call_lp_solver


BASE_ID = "beef_muscle_raw"
PARTNERS = ["beef_fat_raw", "beef_liver_raw"]
SCENARIO = "SCN_B_SLOW_GROWTH"
ANIMAL = AnimalInput(sex="male", weight_kg=25.0, age_months=8, gonadal_status="intact")


def _audit(test_name, got, expected):
    log_file = os.path.join(os.path.dirname(__file__), "test_audit_log.md")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"## {test_name}\n")
        f.write(f"- **Expected:** {expected}\n")
        f.write(f"- **Got:** {got}\n\n")


def _data_with_two_clones(id1: str, id2: str):
    """Deep-copy the DB and inject two nutritionally-identical clones of BASE_ID
    under ids id1 and id2 (same bromatological profile → interchangeable)."""
    data = load_all_jsons()
    data = copy.deepcopy(data)
    db = data["DB_ingredientes.json"]
    base = get_ingredient_by_id(BASE_ID, db)
    assert base is not None, f"base ingredient {BASE_ID} must exist"

    for group in db.get("protein_sources", {}).values():
        ings = group.get("ingredients", [])
        if any(i["ingredient_id"] == BASE_ID for i in ings):
            for new_id in (id1, id2):
                clone = copy.deepcopy(base)
                clone["ingredient_id"] = new_id
                if "name" in clone:
                    clone["name"] = new_id
                ings.append(clone)
            break
    else:
        raise AssertionError("could not locate group containing base ingredient")
    return data, db


def _solve_level3(id1: str, id2: str) -> dict:
    """Run the Level 3 solve with the two clones (ids id1, id2) + real partners."""
    data, db = _data_with_two_clones(id1, id2)
    selected = [id1, id2] + PARTNERS

    der_env = calculate_der_and_envelope(ANIMAL, data["growth_energy_skeletal.json"], SCENARIO, selected, db)
    matrix = build_matrix(selected, db, data["formulation_rules.json"])
    problem = build_lp_problem(
        selected, matrix, data, der_env, 3,
        apply_clinical_floor=True, db=db, scenario_id=SCENARIO,
    )
    cascade = data["lp_parameters_data.json"].get("solve_cascade", [])
    level3_config = next((c for c in cascade if c.get("level") == 3), None)
    objective_stages = level3_config.get("objective_stages", [])
    solver_params = data["lp_parameters_data.json"].get("solver_params", {})

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # runtime auto-scaling warning is expected
        return call_lp_solver(problem, objective_stages, solver_params)


def _nutrient_signature(raw_result: dict, precision: int = 6) -> dict:
    return {k: round(float(v), precision) for k, v in raw_result.get("nutrient_values", {}).items()}


def _total_grams(raw_result: dict) -> float:
    return round(sum(float(v) for v in raw_result.get("x_values", {}).values()), 6)


def _clone_pair_grams(raw_result: dict, id1: str, id2: str, precision: int = 6) -> float:
    """Grams carried by the identical clone pair together (label-order-independent)."""
    xv = raw_result.get("x_values", {})
    return round(float(xv.get(id1, 0.0)) + float(xv.get(id2, 0.0)), precision)


def test_id_permutation_preserves_nutrition_outcome():
    """Swapping the IDs of two nutritionally-tied ingredients changes no nutrition value."""
    # Arrange + Act: same problem under two ID labelings.
    run_a = _solve_level3("tie_aaa", "tie_zzz")
    run_b = _solve_level3("tie_zzz", "tie_aaa")

    assert run_a["status"] == "feasible" and run_b["status"] == "feasible"

    # Assert: nutritional outcome is identical regardless of ID assignment.
    sig_a = _nutrient_signature(run_a)
    sig_b = _nutrient_signature(run_b)
    assert sig_a == sig_b, "per-nutrient values must be identical across ID permutation"

    grams_a = _total_grams(run_a)
    grams_b = _total_grams(run_b)
    assert grams_a == pytest.approx(grams_b, abs=1e-4), (
        f"total diet grams must be invariant to ID permutation: {grams_a} vs {grams_b}"
    )

    # The combined grams on the identical clone pair must also be invariant.
    pair_a = _clone_pair_grams(run_a, "tie_aaa", "tie_zzz")
    pair_b = _clone_pair_grams(run_b, "tie_aaa", "tie_zzz")
    assert pair_a == pytest.approx(pair_b, abs=1e-4), (
        f"clone-pair grams must be invariant to ID permutation: {pair_a} vs {pair_b}"
    )

    # Objective real component (fixed predecessor stages) must match.
    assert run_a.get("fix_optimum_applied") == run_b.get("fix_optimum_applied")

    _audit(
        "test_id_permutation_preserves_nutrition_outcome",
        f"nutrient_sig_equal={sig_a == sig_b}, total_grams=({grams_a},{grams_b}), "
        f"pair_grams=({pair_a},{pair_b}), fix_applied={run_a.get('fix_optimum_applied')}",
        "identical nutrition outcome across ID permutation",
    )


def test_identical_clones_have_identical_coefficients():
    """Sanity: the injected clones really are nutritionally identical (else the test is vacuous)."""
    data, db = _data_with_two_clones("tie_aaa", "tie_zzz")
    matrix = build_matrix(["tie_aaa", "tie_zzz", BASE_ID], db, data["formulation_rules.json"])
    row_a = matrix["tie_aaa"]
    row_z = matrix["tie_zzz"]
    row_base = matrix[BASE_ID]

    # Compare measured values nutrient-by-nutrient.
    def _measured(row):
        return {k: v.get("value") for k, v in row.items() if v.get("status") == "measured"}

    assert _measured(row_a) == _measured(row_z), "clones must be identical to each other"
    assert _measured(row_a) == _measured(row_base), "clones must match the base ingredient"

    _audit("test_identical_clones_have_identical_coefficients",
           f"clones_equal={_measured(row_a) == _measured(row_z)}",
           "clones nutritionally identical to base and each other")


if __name__ == "__main__":
    test_identical_clones_have_identical_coefficients()
    test_id_permutation_preserves_nutrition_outcome()
    print("All tie-break permutation tests passed!")
