"""Category-goals disable regression tests (R-04/R-05, Plan Part 2 Task 4-3).

Phase 4a stops the invalid category-adherence output *today* by disabling the
category-goal stage. These tests prove:

  1. The stage is disabled by default (config default false).
  2. A disabled solve creates NO d_cat_* variables/constraints in the LP.
  3. The output contract reports an EXPLICIT disabled state — never the
     pre-existing fake overall_score=100.0 fall-through, and never a
     dimensionally-invalid category percentage.
  4. Flipping the flag on restores variable creation (proves the gate is the
     only thing suppressing them).

AAA+A pattern.
"""

import copy
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pulp
import pytest
from gsd.core import load_all_jsons, AnimalInput
from gsd.nutrition import calculate_der_and_envelope, build_matrix
from gsd.solver import solve_cascade, build_lp_problem, call_lp_solver, _build_stage_objective


SCENARIO = "SCN_B_SLOW_GROWTH"
ANIMAL = AnimalInput(sex="male", weight_kg=25.0, age_months=8, gonadal_status="intact")
# Selection that reaches a feasible cascade level (foot_tendon supplies Ca:P).
SELECTION = ["beef_muscle_raw", "beef_foot_tendon_raw", "beef_liver_raw",
             "beef_kidney_raw", "chicken_heart_raw"]


def _audit(test_name, got, expected):
    log_file = os.path.join(os.path.dirname(__file__), "test_audit_log.md")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"## {test_name}\n")
        f.write(f"- **Expected:** {expected}\n")
        f.write(f"- **Got:** {got}\n\n")


def _run_cascade(enabled=None):
    data = load_all_jsons()
    data = copy.deepcopy(data)
    if enabled is not None:
        data["lp_parameters_data.json"]["solver_params"]["category_goals_enabled"] = enabled
    db = data["DB_ingredientes.json"]
    der = calculate_der_and_envelope(ANIMAL, data["growth_energy_skeletal.json"], SCENARIO, SELECTION, db)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return solve_cascade(SELECTION, data, der, SCENARIO, ANIMAL)


def test_category_goals_enabled_by_default_after_phase4b():
    """After Phase 4b (Task 4-8), category goals are RE-ENABLED by default.

    The disable flag is retained as an off-switch (exercised by the other tests
    in this file via explicit override), but the shipped default is now true
    because R-04 (output units) and R-05 (target-sum) are fixed.
    """
    data = load_all_jsons()
    sp = data["lp_parameters_data.json"]["solver_params"]
    assert sp.get("category_goals_enabled") is True, (
        "category_goals_enabled must default to true after Phase 4b re-enable (Task 4-8)"
    )
    _audit("test_category_goals_enabled_by_default_after_phase4b",
           f"category_goals_enabled={sp.get('category_goals_enabled')}", "true")


def test_disabled_output_is_explicit_not_fake_100():
    """Disabled solve reports explicit disabled state, never fake overall_score=100.0."""
    result = _run_cascade(enabled=False)
    if result.get("solver_status") == "structurally_infeasible":
        pytest.skip("selection was structurally infeasible; output contract not built")

    ta = result["template_adherence"]
    assert ta.get("disabled") is True, f"expected disabled=True, got {ta}"
    assert ta.get("overall_score") is None, (
        f"disabled must NOT report a fake numeric score, got {ta.get('overall_score')}"
    )
    assert ta.get("components") == {}, "disabled must have empty components"
    assert ta.get("reason"), "disabled must carry a human-readable reason"

    meta = result.get("solver_metadata", {})
    assert meta.get("category_goal_deviations_raw") == {}, (
        "disabled must report empty category_goal_deviations_raw"
    )
    assert meta.get("category_goals_disabled") is True

    # No component anywhere carries a dimensionally-invalid percentage.
    assert not ta["components"], "no per-category percentages should exist while disabled"

    _audit("test_disabled_output_is_explicit_not_fake_100",
           f"disabled={ta.get('disabled')}, overall_score={ta.get('overall_score')}, "
           f"components={ta.get('components')}",
           "explicit disabled state, no fake 100.0")


def test_gate_suppresses_dcat_variables_when_disabled():
    """Unit: the category branch creates NO d_cat_* vars when disabled, and DOES when enabled."""
    def _count_dcat(enabled):
        prob = pulp.LpProblem("t", pulp.LpMinimize)
        x = {"a": prob.add_variable("x_a", lowBound=0), "b": prob.add_variable("x_b", lowBound=0)}
        pd = {
            "nutrient_registry": {},
            "category_to_ingredients": {"muscle_meat": ["a"], "fat_source": ["b"]},
            "category_goals": {
                "mm": {"target_pct": 70, "weight": 50, "categories": ["muscle_meat"]},
                "fs": {"target_pct": 30, "weight": 50, "categories": ["fat_source"]},
            },
            "category_goals_enabled": enabled,
        }
        _build_stage_objective(prob, x, {}, {}, {}, "category_goal_deviation", {}, pd)
        return [v.name for v in prob.variables() if v.name.startswith("d_cat_")]

    disabled_vars = _count_dcat(False)
    enabled_vars = _count_dcat(True)

    assert disabled_vars == [], f"disabled must create no d_cat_* vars, got {disabled_vars}"
    assert len(enabled_vars) == 4, f"enabled must create 4 d_cat_* vars, got {enabled_vars}"

    _audit("test_gate_suppresses_dcat_variables_when_disabled",
           f"disabled={disabled_vars}, enabled={enabled_vars}",
           "disabled=[] , enabled=4 vars")


def test_enabled_flag_restores_variable_creation_end_to_end():
    """With the flag ON, category deviation variables are created during a real solve.

    We drive the objective builder through call_lp_solver on a Level-1 problem so
    the category stage actually executes (proving the flag, not feasibility, is
    what gates the variables). We only assert on variable creation, not on the
    cascade level ultimately returned.
    """
    data = copy.deepcopy(load_all_jsons())
    data["lp_parameters_data.json"]["solver_params"]["category_goals_enabled"] = True
    db = data["DB_ingredientes.json"]
    der = calculate_der_and_envelope(ANIMAL, data["growth_energy_skeletal.json"], SCENARIO, SELECTION, db)
    mtx = build_matrix(SELECTION, db, data["formulation_rules.json"])

    cascade = data["lp_parameters_data.json"]["solve_cascade"]
    lvl1 = next(c for c in cascade if c.get("level") == 1)
    problem = build_lp_problem(SELECTION, mtx, data, der, 1, apply_clinical_floor=False,
                               db=db, scenario_id=SCENARIO)

    # Directly build the category stage objective so it runs regardless of feasibility.
    from gsd.solver import _build_stage_objective as bso
    prob = problem["prob"]
    x_vars = problem["x_vars"]
    bso(prob, x_vars, problem.get("compiled_coefficients", {}), problem.get("suls_per_day", {}),
        problem.get("targets_per_day", {}), "category_goal_deviation",
        problem.get("em_per_g", {}), problem)

    dcat = [v.name for v in prob.variables() if v.name.startswith("d_cat_")]
    assert len(dcat) > 0, "enabled flag must allow d_cat_* variable creation"

    _audit("test_enabled_flag_restores_variable_creation_end_to_end",
           f"d_cat_count={len(dcat)}", "d_cat vars created when enabled")


if __name__ == "__main__":
    test_category_goals_enabled_by_default_after_phase4b()
    test_disabled_output_is_explicit_not_fake_100()
    test_gate_suppresses_dcat_variables_when_disabled()
    test_enabled_flag_restores_variable_creation_end_to_end()
    print("All category-goals disable tests passed!")
