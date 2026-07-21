"""Tie-break coefficient bound tests (R-03, Plan Part 2 Task 3-2).

Proves that the deterministic tie-break can never act as a primary objective:
its maximum possible contribution is enforced, at solver-construction time,
to stay strictly below the solver's own fix-optimum tolerance — derived live
from data/lp_parameters_data.json.solver_params, not hardcoded.

AAA+A pattern (Arrange real files, Act on real code, Assert on real output,
Audit by literal command+output).
"""

import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from gsd.core import load_all_jsons, AnimalInput
from gsd.nutrition import calculate_der_and_envelope, build_matrix
from gsd.solver import (
    build_lp_problem,
    call_lp_solver,
    derive_tie_break_bound,
    enforce_tie_break_bound,
    TieBreakConfigError,
)


def _audit(test_name, got, expected):
    log_file = os.path.join(os.path.dirname(__file__), "test_audit_log.md")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"## {test_name}\n")
        f.write(f"- **Expected:** {expected}\n")
        f.write(f"- **Got:** {got}\n\n")


def _real_solver_params():
    data = load_all_jsons()
    lp_data = data.get("lp_parameters_data.json", {})
    return data, lp_data.get("solver_params", {})


def _real_level3_problem():
    """Build a real Level 3 problem so big_m_values reflect live data."""
    data = load_all_jsons()
    db = data.get("DB_ingredientes.json", {})
    growth = data.get("growth_energy_skeletal.json", {})
    lp_data = data.get("lp_parameters_data.json", {})
    fr = data.get("formulation_rules.json", {})

    selected_ids = ["beef_liver_raw", "beef_muscle_raw", "beef_fat_raw"]
    animal = AnimalInput(sex="male", weight_kg=25.0, age_months=8, gonadal_status="intact")
    der_env = calculate_der_and_envelope(animal, growth, "SCN_B_SLOW_GROWTH", selected_ids, db)
    matrix = build_matrix(selected_ids, db, fr)
    problem = build_lp_problem(
        selected_ids, matrix, data, der_env, 3,
        apply_clinical_floor=True, db=db, scenario_id="SCN_B_SLOW_GROWTH",
    )
    cascade = lp_data.get("solve_cascade", [])
    level3_config = next((c for c in cascade if c.get("level") == 3), None)
    solver_params = lp_data.get("solver_params", {})
    return problem, level3_config, solver_params, data, der_env, animal


# ──────────────────────────────────────────────────────────────────────────────
# Unit tests: the derivation math
# ──────────────────────────────────────────────────────────────────────────────

def test_derive_bound_math_is_weight_times_grams_vs_tolerance():
    """derive_tie_break_bound: max_contribution = weight × grams; tolerance = max(abs, rel*1)."""
    params = {
        "tie_break_weight": 0.001,
        "fix_optimum_tolerance_abs": 0.01,
        "fix_optimum_tolerance_rel": 1e-6,
    }
    info = derive_tie_break_bound(params, max_single_ingredient_grams=1000.0)

    assert info["max_contribution"] == pytest.approx(1.0)         # 0.001 * 1000
    assert info["tolerance"] == pytest.approx(0.01)               # max(0.01, 1e-6)
    assert info["within_bound"] is False                          # 1.0 !< 0.01

    _audit("test_derive_bound_math", info, "max_contribution=1.0, tolerance=0.01, within_bound=False")


def test_derive_bound_flags_within_bound_for_tiny_weight():
    """A genuinely negligible weight is reported within bound."""
    params = {
        "tie_break_weight": 1e-8,
        "fix_optimum_tolerance_abs": 0.01,
        "fix_optimum_tolerance_rel": 1e-6,
    }
    info = derive_tie_break_bound(params, max_single_ingredient_grams=1000.0)
    assert info["max_contribution"] == pytest.approx(1e-5)
    assert info["within_bound"] is True
    _audit("test_derive_bound_tiny", info, "within_bound=True")


# ──────────────────────────────────────────────────────────────────────────────
# Enforcement: raise (config-validation) vs scale (runtime)
# ──────────────────────────────────────────────────────────────────────────────

def test_oversized_weight_raises_in_config_mode():
    """(c) A deliberately-too-large tie_break_weight is REJECTED in config mode."""
    params = {
        "tie_break_weight": 5.0,   # absurdly large
        "fix_optimum_tolerance_abs": 0.01,
        "fix_optimum_tolerance_rel": 1e-6,
    }
    with pytest.raises(TieBreakConfigError):
        enforce_tie_break_bound(params, max_single_ingredient_grams=1000.0, raise_on_violation=True)
    _audit("test_oversized_weight_raises", "TieBreakConfigError raised", "raises in config mode")


def test_oversized_weight_scaled_in_runtime_mode():
    """Runtime mode never aborts: it scales the weight strictly below tolerance and warns."""
    params = {
        "tie_break_weight": 5.0,
        "fix_optimum_tolerance_abs": 0.01,
        "fix_optimum_tolerance_rel": 1e-6,
    }
    grams = 1000.0
    with pytest.warns(UserWarning):
        effective = enforce_tie_break_bound(params, max_single_ingredient_grams=grams, raise_on_violation=False)

    assert effective < params["tie_break_weight"]
    # The guarantee: scaled contribution is strictly below tolerance.
    assert effective * grams < 0.01
    _audit("test_oversized_weight_scaled", f"effective={effective}, contribution={effective*grams}",
           "scaled below tolerance")


def test_within_bound_weight_returned_unchanged():
    """A weight already within bound is returned untouched (no scale, no raise, no warning)."""
    params = {
        "tie_break_weight": 1e-8,
        "fix_optimum_tolerance_abs": 0.01,
        "fix_optimum_tolerance_rel": 1e-6,
    }
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning would fail the test
        effective = enforce_tie_break_bound(params, max_single_ingredient_grams=1000.0, raise_on_violation=True)
    assert effective == pytest.approx(1e-8)
    _audit("test_within_bound_unchanged", f"effective={effective}", "unchanged 1e-8")


# ──────────────────────────────────────────────────────────────────────────────
# Live-config tests
# ──────────────────────────────────────────────────────────────────────────────

def test_current_config_effective_weight_is_within_bound():
    """(a) Current config: after enforcement the effective weight satisfies the bound.

    NOTE: this test also documents a genuine finding — the *configured*
    tie_break_weight (0.001) exceeds the derived tolerance against realistic
    single-ingredient gram maxima, so runtime enforcement scales it down. The
    invariant that matters (effective contribution < tolerance) is what we assert.
    """
    _, solver_params = _real_solver_params()
    grams = 1000.0  # realistic Big-M single-ingredient max (der/em*100)

    info = derive_tie_break_bound(solver_params, grams)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        effective = enforce_tie_break_bound(solver_params, grams, raise_on_violation=False)

    assert effective * grams < info["tolerance"], (
        f"effective contribution {effective*grams} must be < tolerance {info['tolerance']}"
    )
    _audit("test_current_config_within_bound",
           f"configured={info['tie_break_weight']}, configured_contribution={info['max_contribution']}, "
           f"effective={effective}, tolerance={info['tolerance']}",
           "effective contribution < tolerance")


def test_solver_reports_bounded_effective_weight_end_to_end():
    """End-to-end: call_lp_solver reports tie_break_weight_used, and it is within bound."""
    problem, level3_config, solver_params, data, der_env, animal = _real_level3_problem()
    objective_stages = level3_config.get("objective_stages", [])

    big_m_vals = problem.get("big_m_values", {})
    max_big_m = max(big_m_vals.values()) if big_m_vals else 2000.0

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw_result = call_lp_solver(problem, objective_stages, solver_params)

    assert raw_result["status"] == "feasible"
    assert raw_result.get("tie_break_applied") is True
    used = raw_result.get("tie_break_weight_used")
    assert used is not None, "tie_break_weight_used must be reported when tie-break applied"

    info = derive_tie_break_bound(solver_params, max_big_m)
    assert used * max_big_m < info["tolerance"], (
        f"effective tie-break contribution {used*max_big_m} must be < tolerance {info['tolerance']}"
    )
    _audit("test_solver_reports_bounded_weight",
           f"tie_break_weight_used={used}, max_big_m={max_big_m}, tolerance={info['tolerance']}",
           "used * max_big_m < tolerance")


if __name__ == "__main__":
    test_derive_bound_math_is_weight_times_grams_vs_tolerance()
    test_derive_bound_flags_within_bound_for_tiny_weight()
    test_oversized_weight_raises_in_config_mode()
    test_oversized_weight_scaled_in_runtime_mode()
    test_within_bound_weight_returned_unchanged()
    test_current_config_effective_weight_is_within_bound()
    test_solver_reports_bounded_effective_weight_end_to_end()
    print("All tie-break bound tests passed!")
