"""Category-goals fix regression tests (R-04/R-05, Plan Part 2 Task 4-7).

Formalizes the two Phase 4b guarantees:

  (a) R-04 — output template_adherence percentages are INDEPENDENTLY reproducible
      from allocations[] alone (100 × category_grams / total_grams), with no
      reference to the LP's internal gram-valued deviation variables.
  (b) R-05 — the load-time validator rejects any cascade level whose category
      target_pct values do not sum to 100% under disjoint-category semantics.

AAA+A pattern.
"""

import copy
import os
import sys
import warnings
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from gsd.core import load_all_jsons, AnimalInput, validate_category_goals, CategoryGoalsConfigError
from gsd.nutrition import calculate_der_and_envelope
from gsd.solver import solve_cascade


SCENARIO = "SCN_B_SLOW_GROWTH"
ANIMAL = AnimalInput(sex="male", weight_kg=25.0, age_months=8, gonadal_status="intact")
SELECTION = ["beef_muscle_raw", "beef_foot_tendon_raw", "beef_liver_raw",
             "beef_kidney_raw", "chicken_heart_raw"]


def _audit(test_name, got, expected):
    log_file = os.path.join(os.path.dirname(__file__), "test_audit_log.md")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"## {test_name}\n")
        f.write(f"- **Expected:** {expected}\n")
        f.write(f"- **Got:** {got}\n\n")


# ──────────────────────────────────────────────────────────────────────────────
# (a) R-04: independent reproducibility from allocations[]
# ──────────────────────────────────────────────────────────────────────────────

def test_template_adherence_percentages_reproducible_from_allocations():
    """Every reported achieved_pct must equal 100×category_grams/total_grams
    computed independently from allocations[]."""
    data = copy.deepcopy(load_all_jsons())
    data["lp_parameters_data.json"]["solver_params"]["category_goals_enabled"] = True
    db = data["DB_ingredientes.json"]
    der = calculate_der_and_envelope(ANIMAL, data["growth_energy_skeletal.json"], SCENARIO, SELECTION, db)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = solve_cascade(SELECTION, data, der, SCENARIO, ANIMAL)

    if result.get("cascade_level_used") not in (1, 2) or not result.get("allocations"):
        pytest.skip("did not reach an allocation-producing level")

    allocs = result["allocations"]
    total = sum(a["grams_per_day"] for a in allocs)
    cat_g = defaultdict(float)
    for a in allocs:
        cat_g[a["category"]] += a["grams_per_day"]

    lvl_cfg = next(c for c in data["lp_parameters_data.json"]["solve_cascade"]
                   if c.get("level") == result["cascade_level_used"])
    goals = lvl_cfg["category_goals"]
    components = result["template_adherence"]["components"]

    checked = 0
    for gname, goal in goals.items():
        cats = goal["categories"]
        independent = 100.0 * sum(cat_g.get(c, 0.0) for c in cats) / total if total > 0 else 0.0
        reported = components[gname]["achieved_pct"]
        assert reported == pytest.approx(independent, abs=0.05), (
            f"{gname}: reported {reported}% != independent {independent}%"
        )
        # deviation must be |achieved - target| on the 0-100 scale
        expected_dev = abs(independent - goal["target_pct"])
        assert components[gname]["absolute_deviation_pct"] == pytest.approx(expected_dev, abs=0.05)
        checked += 1

    assert checked > 0, "no category goals were checked"
    _audit("test_template_adherence_percentages_reproducible_from_allocations",
           f"level={result['cascade_level_used']}, goals_checked={checked}",
           "all achieved_pct reproducible from allocations[]")


def test_achieved_pct_on_percent_scale_not_grams():
    """Guard against R-04 regression: achieved_pct must be a plausible percentage
    (0-100), never a gram-magnitude value."""
    data = copy.deepcopy(load_all_jsons())
    data["lp_parameters_data.json"]["solver_params"]["category_goals_enabled"] = True
    db = data["DB_ingredientes.json"]
    der = calculate_der_and_envelope(ANIMAL, data["growth_energy_skeletal.json"], SCENARIO, SELECTION, db)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = solve_cascade(SELECTION, data, der, SCENARIO, ANIMAL)

    if result.get("cascade_level_used") not in (1, 2):
        pytest.skip("did not reach an allocation-producing level")

    for gname, comp in result["template_adherence"]["components"].items():
        ap = comp["achieved_pct"]
        if ap is not None:
            assert 0.0 <= ap <= 100.0, f"{gname}: achieved_pct {ap} not on 0-100 scale"
    _audit("test_achieved_pct_on_percent_scale_not_grams", "all in [0,100]", "percent scale")


# ──────────────────────────────────────────────────────────────────────────────
# (b) R-05: load-time validation
# ──────────────────────────────────────────────────────────────────────────────

def test_shipped_config_targets_sum_to_100_both_levels():
    """The shipped config must pass the validator for every level with category goals."""
    data = load_all_jsons()  # would raise on load if invalid
    lp = data["lp_parameters_data.json"]
    for lvl in lp["solve_cascade"]:
        cg = lvl.get("category_goals", {})
        if cg:
            total = sum(g.get("target_pct", 0) for g in cg.values())
            assert total == pytest.approx(100.0, abs=0.01), (
                f"Level {lvl['level']} targets sum to {total}, expected 100"
            )
    # validator itself must accept it
    validate_category_goals(lp)
    _audit("test_shipped_config_targets_sum_to_100_both_levels", "both levels sum 100", "valid")


@pytest.mark.parametrize("level_idx", [0, 1])
def test_validator_rejects_corrupted_110_config_per_level(level_idx):
    """A deliberately-corrupted 110% config in EITHER level must be rejected."""
    data = load_all_jsons()
    lp = copy.deepcopy(data["lp_parameters_data.json"])
    # find the Nth level that actually has category goals and corrupt it
    levels_with_goals = [l for l in lp["solve_cascade"] if l.get("category_goals")]
    target_level = levels_with_goals[level_idx]
    first_goal = next(iter(target_level["category_goals"].values()))
    first_goal["target_pct"] = first_goal.get("target_pct", 0) + 10  # push sum to 110

    with pytest.raises(CategoryGoalsConfigError):
        validate_category_goals(lp)
    _audit(f"test_validator_rejects_corrupted_110_config_level_{level_idx}",
           f"corrupted level index {level_idx} raised", "raises CategoryGoalsConfigError")


def test_validator_ignores_levels_without_category_goals():
    """Level 3 (no category goals) must not trip the validator."""
    lp = {"solve_cascade": [{"level": 3}]}  # no category_goals
    validate_category_goals(lp)  # must not raise
    _audit("test_validator_ignores_levels_without_category_goals", "no raise", "level 3 ok")


if __name__ == "__main__":
    test_template_adherence_percentages_reproducible_from_allocations()
    test_achieved_pct_on_percent_scale_not_grams()
    test_shipped_config_targets_sum_to_100_both_levels()
    test_validator_rejects_corrupted_110_config_per_level(0)
    test_validator_rejects_corrupted_110_config_per_level(1)
    test_validator_ignores_levels_without_category_goals()
    print("All category-goals fix tests passed!")
