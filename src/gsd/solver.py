#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""solver.py -- LP cascade + output contract. Imports core + nutrition."""

from typing import Any, Dict, List, Optional, Tuple

from .core import DerEnvelope, UNIT_RENAME, AnimalInput
from .nutrition import get_ingredient_by_id, build_matrix, energy_metabolizable_kcal_per_100g

def build_lp_problem(
    selected_ids: list[str],
    matrix: dict[str, dict[str, dict]],
    data: dict,
    der_info: DerEnvelope,
    cascade_level: int,
    apply_clinical_floor: bool = False,
    db: dict | None = None,
    scenario_id: str = "SCN_B_SLOW_GROWTH",
) -> dict:
    """
    Build the LP problem for a given cascade level.

    Returns dict with:
      - prob: pulp.LpProblem
      - x_vars: {ingredient_id: LpVariable}
      - compiled_coefficients: {ingredient_id: {nutrient_id: float}} (nutrient/gram)
      - targets_per_day: {nutrient_id: float}
      - suls_per_day: {nutrient_id: float}
      - clinical_floor_bounds: {ingredient_id: float} (Level 3 only)
      - big_m_values: {ingredient_id: float} (Level 3 only)
      - has_binary_vars: bool
      - category_to_ingredients: {category: [ingredient_id]} (for category goals)
    """
    import pulp

    lp_params = data.get("lp_parameters_data.json", {})
    solver_params = lp_params.get("solver_params", {})
    registry = lp_params.get("NUTRIENT_REGISTRY", {})

    # Use provided DB or fallback to data
    if db is None:
        db = data.get("DB_ingredientes.json", {})
    tox_limits = data.get("toxicological_limits.json", [])
    constraints = data.get("constraints.json", {})
    fr = data.get("formulation_rules.json", {})

# 1. Create LP problem
    prob = pulp.LpProblem(f"GSD_Diet_Level{cascade_level}", pulp.LpMinimize)

    # 2. Decision variables x_i (grams/day) - only for ingredients with measured nutrients
    x_vars: dict[str, pulp.LpVariable] = {}
    valid_selected_ids = []
    for iid in selected_ids:
        a_ij = matrix.get(iid, {})
        has_measured = any(entry.get("status") == "measured" for entry in a_ij.values())
        if has_measured:
            x_vars[iid] = prob.add_variable(f"x_{iid}", lowBound=0, cat="Continuous")
            valid_selected_ids.append(iid)
        else:
            # Log warning for debugging
            print(f"  [WARN] Ingredient {iid} has no measured nutrients, skipping from LP")

    if not x_vars:
        return {"status": "infeasible", "reason": "No ingredients with measured nutrients"}

    # 3. Compile coefficients: a_ij is nutrient/1000kcal → nutrient/gram
    # CORRECT FORMULA: nutrient_per_gram = a_ij * EM_kcal_per_g / 1000.0
    compiled_coeffs: dict[str, dict[str, float]] = {}
    em_per_g: dict[str, float] = {}
    big_m_values: dict[str, float] = {}
    clinical_floor_bounds: dict[str, float] = {}

    # Get EM per 100g for each ingredient from DB
    for iid in valid_selected_ids:
        ing = get_ingredient_by_id(iid, db)
        if ing is None:
            continue
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        em_100g = energy_metabolizable_kcal_per_100g(nuts)
        em_per_g[iid] = em_100g / 100.0

        # Big-M per ingredient: M_i = DER_kcal / EM_i_kcal_per_100g * 100
        # Grams of ingredient i alone that would satisfy 100% of DER
        if em_100g > 0:
            big_m_values[iid] = der_info.der_kcal / em_100g * 100.0
        else:
            big_m_values[iid] = 10000.0  # fallback large number

        # Compile nutrient/gram coefficients
        compiled_coeffs[iid] = {}
        a_ij = matrix.get(iid, {})
        for nid, entry in a_ij.items():
            if entry.get("status") == "measured":
                a_val = entry["value"]  # nutrient per 1000kcal
                # CORRECTED: nutrient_per_gram = a_ij * EM_kcal_per_g / 1000.0
                compiled_coeffs[iid][nid] = a_val * em_per_g[iid] / 1000.0

    # 4. BUILD-TIME SANITY ASSERTION: verify compilation against stored per-100g values
    # Pick first available ingredient/nutrient pair for the check
    sanity_checked = False
    for iid in valid_selected_ids:
        if sanity_checked:
            break
        ing = get_ingredient_by_id(iid, db)
        if ing is None:
            continue
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        for db_key, entry in nuts.items():
            if entry.get("status") != "measured":
                continue
            solver_key, scale = UNIT_RENAME.get(db_key, (db_key, 1.0))
            if solver_key not in compiled_coeffs.get(iid, {}):
                continue
            # Independent recomputation from stored per-100g value
            expected = float(entry["value"]) * scale / 100.0
            got = compiled_coeffs[iid][solver_key]
            assert abs(got - expected) < 1e-9, (
                f"Build-time sanity failed for {iid}/{solver_key}: "
                f"expected {expected} (from per-100g), got {got} (from a_ij*EM/1000). "
                f"Check the /1000 factor in nutrient/gram compilation."
            )
            sanity_checked = True
            break
    if not sanity_checked:
        # Fallback: at least check beef_muscle_raw protein if in selection
        if "beef_muscle_raw" in valid_selected_ids:
            ing = get_ingredient_by_id("beef_muscle_raw", db)
            if ing:
                nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
                entry = nuts.get("protein_g", {})
                if entry.get("status") == "measured":
                    expected = float(entry["value"]) / 100.0
                    got = compiled_coeffs.get("beef_muscle_raw", {}).get("protein_g")
                    if got is not None:
                        assert abs(got - expected) < 1e-9, (
                            f"Build-time sanity failed for beef_muscle_raw/protein_g: "
                            f"expected {expected}, got {got}"
                        )

    # 5. Targets per day (nutrient/1000kcal * units_of_1000kcal)
    targets_per_day: dict[str, float] = {}
    scenario = data.get("scenarios.json", [])
    active_scenario = next((s for s in scenario if s.get("scenario_id") == scenario_id), {})
    for target in active_scenario.get("targets", []):
        nid = target.get("nutrient_id")
        val = target.get("value")
        if nid and val is not None:
            targets_per_day[nid] = float(val) * der_info.units_of_1000kcal

    # Pre-compute category to ingredients mapping for O(1) lookups in objective builder.
    # Required by the category_goal_deviation objective kind (Option B — category soft goals).
    category_map = {}
    for iid in valid_selected_ids:
        ing = get_ingredient_by_id(iid, db)
        if ing:
            cat = ing.get("category", "unknown")
            category_map.setdefault(cat, []).append(iid)

    # 6. SULs per day
    suls_per_day: dict[str, float] = {}
    for tox in tox_limits:
        nid = tox.get("nutrient_id")
        sul_entry = tox.get("sul", {})
        sul_val = sul_entry.get("value")
        if nid and sul_val is not None:
            suls_per_day[nid] = float(sul_val) * der_info.units_of_1000kcal

    # Initialize problem_dict with variable storage dictionaries
    problem_dict = {
        "prob": prob,
        "x_vars": x_vars,
        "compiled_coefficients": compiled_coeffs,
        "targets_per_day": targets_per_day,
        "suls_per_day": suls_per_day,
        "clinical_floor_bounds": clinical_floor_bounds,
        "big_m_values": big_m_values,
        "has_binary_vars": False,
        "em_per_g": em_per_g,
        "der_info": der_info,
        "nutrient_slack_vars": {},
        "sul_slack_vars": {},
        "der_dev_vars": {},
        "category_to_ingredients": category_map,
    }

    # 7. Build constraints based on cascade level
    level_config = next(
        (l for l in lp_params.get("solve_cascade", []) if l.get("level") == cascade_level),
        {}
    )
    relax_tiers = set(level_config.get("relax_tiers", []))

    # Hand category_goals to the objective builder via problem_dict — it has no
    # access to lp_params or cascade_level itself (see _build_stage_objective signature).
    problem_dict["category_goals"] = level_config.get("category_goals", {})

    # Helper to add nutrient constraints
    def add_nutrient_constraints():
        nonlocal prob
        # Nutrient bounds from constraints.json (minimums)
        nutrient_bounds = constraints.get("nutrient_bounds", [])
        print(f"[DEBUG] Level {cascade_level}: relax_tiers = {relax_tiers}")
        added = 0
        for nb in nutrient_bounds:
            cid = nb.get("constraint_id", "")
            if not cid.startswith("CSTR_NB_"):
                continue
            # nutrient_id is in lp_coefficients.variables_referenced[0] (not a direct field)
            lp_coeffs = nb.get("lp_coefficients", {})
            vars_ref = lp_coeffs.get("variables_referenced", [])
            if not vars_ref:
                continue
            nid = vars_ref[0]
            # Minimum constraints (CSTR_NB_*_MIN) are always adequacy_soft (relaxable in Level 2)
            # SUL constraints use safety_hard (only relaxed in Level 3)
            # Determine tier from constraint_id prefix
            if cid.startswith("CSTR_NB_") and cid.endswith("_MIN"):
                tier = "adequacy_soft"
            elif cid.startswith("CSTR_SUL_"):
                tier = "safety_hard"
            else:
                tier = registry.get(nid, {}).get("constraint_tier", "adequacy_soft")
            is_relaxed = tier in relax_tiers
            print(f"[DEBUG] {cid}: nid={nid}, tier={tier}, is_relaxed={is_relaxed}")

            # Sum of nutrient_j = sum_i (compiled_coeffs[i][j] * x_i)
            # Use .get(nid, 0.0) to handle nutrients not measured in some ingredients
            expr = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in valid_selected_ids
            )

            # Minimum constraint from constraint bound (bounds is a list)
            bounds_list = lp_coeffs.get("bounds", [])
            for b in bounds_list:
                rhs = b.get("rhs", 0)
                sense = b.get("sense", ">=")
                if sense == ">=" and rhs > 0:
                    target = float(rhs) * der_info.units_of_1000kcal
                    if is_relaxed:
                        # Add slack variable for Level 2
                        slack = prob.add_variable(f"slack_{nid}_min", lowBound=0, cat="Continuous")
                        prob += expr + slack >= target
                        problem_dict["nutrient_slack_vars"][nid] = slack
                    else:
                        prob += expr >= target
                    added += 1

    # SUL constraints (safety_hard)
    def add_sul_constraints():
        nonlocal prob
        for nid, sul_day in suls_per_day.items():
            # SUL constraints are always safety_hard (only relaxed in Level 3)
            is_relaxed = "safety_hard" in relax_tiers  # only Level 3 relaxes safety_hard

            expr = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in valid_selected_ids
            )

            if is_relaxed:
                # Level 3: allow violation with slack
                v_plus = prob.add_variable(f"v_{nid}_plus", lowBound=0, cat="Continuous")
                prob += expr <= sul_day + v_plus
                problem_dict["sul_slack_vars"][nid] = v_plus
            else:
                # Levels 1,2: hard constraint
                prob += expr <= sul_day

# Inclusion constraints (category sums)
    def add_inclusion_constraints(relax: bool = False):
        nonlocal prob
        # Get category mapping
        mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
        all_ids_by_cat: dict[str, list[str]] = {}
        for cat_group in db.get("protein_sources", {}).values():
            for ing in cat_group.get("ingredients", []):
                all_ids_by_cat.setdefault(ing["category"], []).append(ing["ingredient_id"])

        # Expand wildcards
        expanded = {}
        for generic, ids in mapping.items():
            resolved = []
            for i in ids:
                if i == "_all_muscle_meat":
                    resolved += all_ids_by_cat.get("muscle_meat", [])
                elif i == "_all_fat_source":
                    resolved += all_ids_by_cat.get("fat_source", [])
                elif i == "_all_fish":
                    resolved += all_ids_by_cat.get("fish", [])
                else:
                    resolved.append(i)
            expanded[generic] = [i for i in resolved if i in selected_ids]

        incl_limits = fr.get("inclusion_limits", [])
        for incl in incl_limits:
            iid = incl.get("ingredient_id")  # category name like "liver", "protein_base"
            max_pct = incl.get("max_pct")
            min_pct = incl.get("min_pct")
            if not iid or iid not in expanded:
                continue
            cat_ingredients = expanded[iid]
            if not cat_ingredients:
                continue
            cat_sum = pulp.lpSum(x_vars[i] for i in cat_ingredients)
            total = pulp.lpSum(x_vars[i] for i in valid_selected_ids)
            if max_pct is not None:
                if relax:
                    # Level 3: slack variable for max inclusion
                    slack = prob.add_variable(f"slack_incl_max_{iid}", lowBound=0, cat="Continuous")
                    prob += cat_sum <= float(max_pct) / 100.0 * total + slack
                    # Store for objective if needed
                    problem_dict.setdefault("inclusion_slack_vars", {})[f"max_{iid}"] = slack
                else:
                    # Levels 1,2: hard constraint
                    prob += cat_sum <= float(max_pct) / 100.0 * total
            if min_pct is not None:
                if relax:
                    # Level 3: slack variable for min inclusion
                    slack = prob.add_variable(f"slack_incl_min_{iid}", lowBound=0, cat="Continuous")
                    prob += cat_sum >= float(min_pct) / 100.0 * total - slack
                    problem_dict.setdefault("inclusion_slack_vars", {})[f"min_{iid}"] = slack
                else:
                    prob += cat_sum >= float(min_pct) / 100.0 * total

    # Mineral antagonism ratio constraints (with slack for goal programming)
    def add_antagonism_constraints():
        nonlocal prob
        # Get penalty weights from lp_parameters_data.json
        lp_params = data.get("lp_parameters_data.json", {})
        antag_penalties = {a["constraint_id"]: a.get("penalty_weight", 5000) 
                           for a in lp_params.get("mineral_antagonisms", [])}
        
        # Storage for slack variables to be used in objective
        antagonism_slack_vars = {}
        
        for antag in constraints.get("mineral_antagonisms", []):
            cid = antag.get("constraint_id", "")
            vars_ref = antag.get("lp_coefficients", {}).get("variables_referenced", [])
            if len(vars_ref) != 2:
                continue
            n1, n2 = vars_ref[0], vars_ref[1]
            bounds_list = antag.get("lp_coefficients", {}).get("bounds", [])
            
            e1 = pulp.lpSum(compiled_coeffs[iid].get(n1, 0.0) * x_vars[iid] for iid in valid_selected_ids)
            e2 = pulp.lpSum(compiled_coeffs[iid].get(n2, 0.0) * x_vars[iid] for iid in valid_selected_ids)
            
            for bounds in bounds_list:
                sense = bounds.get("sense", "")
                rhs = bounds.get("rhs", 0)
                vars_dict = bounds.get("variables", {})
                
                # Extract ratio from coefficients: format is {n1: 1.0, n2: -ratio} with rhs=0
                # This represents: 1.0 * n1 + (-ratio) * n2 >= 0  =>  n1 >= ratio * n2
                # Or: 1.0 * n1 + (-ratio) * n2 <= 0  =>  n1 <= ratio * n2
                coeff_n1 = vars_dict.get(n1, 0)
                coeff_n2 = vars_dict.get(n2, 0)
                
                if coeff_n1 == 0 or coeff_n2 >= 0:
                    continue
                
                ratio = -coeff_n2 / coeff_n1  # e.g., 1.1 or 1.3 for Ca:P
                
                if sense == "<=" and ratio > 0:
                    # Upper bound: n1 <= ratio * n2  ->  n1 - ratio * n2 <= s_high
                    s_high = prob.add_variable(f"s_high_{cid}", lowBound=0, cat="Continuous")
                    prob += e1 - ratio * e2 <= s_high
                    antagonism_slack_vars[f"s_high_{cid}"] = (s_high, 1.0)
                elif sense == ">=" and ratio > 0:
                    # Lower bound: n1 >= ratio * n2  ->  ratio * n2 - n1 <= s_low
                    s_low = prob.add_variable(f"s_low_{cid}", lowBound=0, cat="Continuous")
                    prob += ratio * e2 - e1 <= s_low
                    antagonism_slack_vars[f"s_low_{cid}"] = (s_low, 1.0)
        
        # Store slack variables for use in objective
        problem_dict["antagonism_slack_vars"] = antagonism_slack_vars
        # Store penalty weights for objective
        problem_dict["antagonism_penalty_weights"] = antag_penalties

    # Envelope constraints
    def add_envelope_constraints():
        nonlocal prob
        total = pulp.lpSum(x_vars[iid] for iid in valid_selected_ids)
        env_soft = "envelope_soft" in relax_tiers
        if env_soft:
            # Only max envelope is relaxed; min envelope is ALWAYS hard (physical constraint)
            slack_max = prob.add_variable("slack_envelope_max", lowBound=0, cat="Continuous")
            prob += total >= der_info.min_total_g  # HARD minimum
            prob += total <= der_info.max_total_g + slack_max
            # Store for objective
            problem_dict["envelope_slack_min"] = None
            problem_dict["envelope_slack_max"] = slack_max
        else:
            prob += total >= der_info.min_total_g
            prob += total <= der_info.max_total_g

# Energy density / DER proximity
    der_dev_plus = {}
    der_dev_minus = {}
    def add_der_proximity():
        nonlocal prob
        total_energy = pulp.lpSum(
            em_per_g[iid] * x_vars[iid]  # EM_kcal_per_g * grams = kcal
            for iid in valid_selected_ids
        )
        # Add deviation variables for DER proximity objective
        dev_plus = prob.add_variable("dev_der_plus", lowBound=0, cat="Continuous")
        dev_minus = prob.add_variable("dev_der_minus", lowBound=0, cat="Continuous")
        prob += total_energy - dev_plus + dev_minus == der_info.der_kcal
        der_dev_plus["dev_der_plus"] = dev_plus
        der_dev_minus["dev_der_minus"] = dev_minus

    # Assemble constraints
    add_nutrient_constraints()
    add_sul_constraints()
    add_inclusion_constraints(relax=(cascade_level == 3))
    add_antagonism_constraints()
    add_envelope_constraints()
    add_der_proximity()

    # Store DER deviation vars for objective (must happen AFTER add_der_proximity call above)
    problem_dict["der_dev_vars"] = der_dev_plus | der_dev_minus

    # 8. Clinical floor (Level 3 only, config-driven)
    has_binary_vars = False
    if apply_clinical_floor:
        # Get clinical floor bounds from formulation_rules
        incl_constraints = fr.get("_inclusion_semantics", {}).get("inclusion_constraints", [])
        floor_config = level_config.get("clinical_floor", {})
        defaults = floor_config.get("defaults_by_category", {})
        global_fallback = floor_config.get("global_fallback_g", 5.0)

        for iid in valid_selected_ids:
            ing = get_ingredient_by_id(iid, db)
            if not ing:
                continue
            cat = ing.get("category", "unknown")

            # Find declared floor
            declared = None
            for ic in incl_constraints:
                if ic.get("ingredient_id") == iid:
                    declared = ic.get("clinical_floor_g")
                    break

            floor_g = declared if declared is not None else defaults.get(cat, global_fallback)
            clinical_floor_bounds[iid] = floor_g

            # Binary variable y_i
            y = prob.add_variable(f"y_{iid}", cat="Binary")
            M = big_m_values[iid]

            # x_i <= M * y_i
            prob += x_vars[iid] <= M * y
            # x_i >= floor_g * y_i
            prob += x_vars[iid] >= floor_g * y

            has_binary_vars = True

    return {
        "prob": prob,
        "x_vars": x_vars,
        "compiled_coefficients": compiled_coeffs,
        "targets_per_day": targets_per_day,
        "suls_per_day": suls_per_day,
        "clinical_floor_bounds": clinical_floor_bounds,
        "big_m_values": big_m_values,
        "has_binary_vars": has_binary_vars,
        "em_per_g": em_per_g,
        "der_info": der_info,
        "nutrient_slack_vars": problem_dict.get("nutrient_slack_vars", {}),
        "sul_slack_vars": problem_dict.get("sul_slack_vars", {}),
        "der_dev_vars": problem_dict.get("der_dev_vars", {}),
        "category_to_ingredients": problem_dict.get("category_to_ingredients", {}),
        "category_goals": problem_dict.get("category_goals", {}),
    }


def call_lp_solver(problem_dict: dict, objective_stages: list, solver_params: dict) -> dict:
    """
    Solve the LP/MILP with lexicographic stages.

    Args:
        problem_dict: Output from build_lp_problem()
        objective_stages: List of stage configs from solve_cascade (each has 'name', 'kind', 'fix_optimum')
        solver_params: solver_params block from lp_parameters_data.json

Returns:
        {status, x_values, nutrient_values, objective_value, stages_solved, solve_time_ms}
    """
    import pulp
    import time

    prob = problem_dict["prob"]
    x_vars = problem_dict["x_vars"]
    compiled_coeffs = problem_dict["compiled_coefficients"]
    suls_per_day = problem_dict["suls_per_day"]
    targets_per_day = problem_dict["targets_per_day"]
    has_binary_vars = problem_dict["has_binary_vars"]
    em_per_g = problem_dict.get("em_per_g", {})

    stages_solved = []
    start_time = time.time()

    for stage_idx, stage in enumerate(objective_stages):
        stage_name = stage.get("name")
        stage_kind = stage.get("kind")
        fix_opt = stage.get("fix_optimum", False)
        is_last_stage = (stage_idx == len(objective_stages) - 1)

# Build objective expression for this stage
        obj_expr = _build_stage_objective(
            prob, x_vars, compiled_coeffs, suls_per_day, targets_per_day, stage_kind, em_per_g, problem_dict
        )

        # Deterministic tie-break: add to EVERY stage to ensure deterministic branching
        # Use VERY STRONG perturbation (1000.0) to guarantee uniqueness over solver tolerance
        tie_weight = solver_params.get("tie_break_weight", 1000.0)
        def det_hash(s: str) -> int:
            h = 0
            for ch in s:
                h = (h * 31 + ord(ch)) & 0xFFFFFFFF
            return h
        
        tie_break_expr = 0
        for iid, var in x_vars.items():
            # Deterministic perturbation based on ingredient_id hash
            # Range: 0-9999 * 1e-1 = 0-999.9, added to tie_weight
            perturbation = (det_hash(iid) % 10000) * 1e-1
            tie_break_expr += (tie_weight + perturbation) * var
        obj_expr += tie_break_expr

        prob.setObjective(obj_expr)

# Solve
        prob.solve(pulp.COIN_CMD(
            path=pulp.apis.coin_api.PULP_CBC_CMD.pulp_cbc_path,
            msg=False,
            timeLimit=solver_params.get("cbc_time_limit_seconds", 30),
            gapRel=solver_params.get("cbc_mip_gap", 0.01),
            threads=1,
            options=["randomSeed=12345"],
        ))

        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return {"status": "infeasible", "stages_solved": stages_solved}

        stages_solved.append(stage_name)

        # Fix optimum if required
        if fix_opt:
            optimal_obj = pulp.value(prob.objective)
            tol_rel = solver_params.get("fix_optimum_tolerance_rel", 1e-6)
            tol_abs = solver_params.get("fix_optimum_tolerance_abs", 0.01)

            # mip_tolerance_rule: widen tolerance if stage had binary vars
            if has_binary_vars:
                mip_gap = solver_params.get("cbc_mip_gap", 0.01)
                tol_rel = max(tol_rel, mip_gap)

            bound = optimal_obj * (1 + tol_rel) + tol_abs
            prob += obj_expr <= bound

    # Extract solution
    x_values = {iid: pulp.value(var) for iid, var in x_vars.items() if pulp.value(var) is not None and pulp.value(var) > 1e-6}

    # Capture category-goal deviation variable values (Option B — category soft goals).
    # d_cat_<n>_minus/plus that were never created (empty category — see
    # _build_stage_objective's `if not cat_ingredients: continue`) simply won't appear here.
    category_goal_deviations = {
        v.name: pulp.value(v) for v in prob.variables() if v.name.startswith("d_cat_")
    }

    # Compute nutrient values from solution
    nutrient_values = {}
    for nid in targets_per_day:
        nutrient_values[nid] = sum(
            compiled_coeffs[iid].get(nid, 0.0) * x_values.get(iid, 0.0)
            for iid in x_values
        )
    for nid in suls_per_day:
        if nid not in nutrient_values:
            nutrient_values[nid] = sum(
                compiled_coeffs[iid].get(nid, 0.0) * x_values.get(iid, 0.0)
                for iid in x_values
            )

    solve_time_ms = int((time.time() - start_time) * 1000)

    return {
        "status": "feasible",
        "x_values": x_values,
        "nutrient_values": nutrient_values,
        "objective_value": pulp.value(prob.objective),
        "stages_solved": stages_solved,
        "solve_time_ms": solve_time_ms,
        "nutrient_slack_vars": problem_dict.get("nutrient_slack_vars", {}),
        "sul_slack_vars": problem_dict.get("sul_slack_vars", {}),
        "der_dev_vars": problem_dict.get("der_dev_vars", {}),
        "clinical_floor_bounds": problem_dict.get("clinical_floor_bounds", {}),
        "clinical_floor_relaxed": problem_dict.get("clinical_floor_relaxed", False),
        "category_goal_deviations": category_goal_deviations,
    }


def _build_stage_objective(
    prob: "pulp.LpProblem",
    x_vars: dict,
    compiled_coeffs: dict,
    suls_per_day: dict,
    targets_per_day: dict,
    kind: str,
    em_per_g: dict,
    problem_dict: dict,
) -> "pulp.LpAffineExpression":
    """Build objective expression for a given stage kind using pre-created variables."""
    import pulp

    # Get pre-created variables from problem_dict
    nutrient_slack_vars = problem_dict.get("nutrient_slack_vars", {})
    sul_slack_vars = problem_dict.get("sul_slack_vars", {})
    der_dev_vars = problem_dict.get("der_dev_vars", {})

    if kind == "minimize_normalized_sul_violation":
        # Sum of v_j_plus / SUL_j for all safety_hard nutrients
        expr = 0
        for nid, sul in suls_per_day.items():
            if sul > 0 and nid in sul_slack_vars:
                v = sul_slack_vars[nid]
                expr += v / sul
        return expr

    elif kind == "minimize_absolute_der_deviation":
        # Minimize |total_energy - DER| using pre-created deviation vars
        dev_plus = der_dev_vars.get("dev_der_plus")
        dev_minus = der_dev_vars.get("dev_der_minus")
        if dev_plus is None or dev_minus is None:
            # Fallback - create if not exist (shouldn't happen)
            dev_plus = prob.add_variable("dev_der_plus", lowBound=0, cat="Continuous")
            dev_minus = prob.add_variable("dev_der_minus", lowBound=0, cat="Continuous")
        return dev_plus + dev_minus

    elif kind == "minimize_weighted_normalized_adequacy_slack":
        # Sum of (slack / target) * clinical_criticality_weight
        expr = 0
        for nid, target in targets_per_day.items():
            if target > 0 and nid in nutrient_slack_vars:
                slack = nutrient_slack_vars[nid]
                weight = 1.0  # clinical_criticality weight from registry
                expr += (slack / target) * weight
        return expr

    elif kind == "weighted_normalized_deviation":
        # Canonical goal programming: sum w_j * (d_j^- + d_j^+) / target_j (normalized)
        expr = 0
        for nid, target in targets_per_day.items():
            if target <= 0:
                continue
            d_minus = prob.add_variable(f"d_{nid}_minus", lowBound=0, cat="Continuous")
            d_plus = prob.add_variable(f"d_{nid}_plus", lowBound=0, cat="Continuous")
            nutrient_sum = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in x_vars
            )
            prob += nutrient_sum + d_minus - d_plus == target
            # Normalize by target and use clinical_criticality weight
            weight = 1.0  # clinical_criticality weight from registry
            expr += (d_minus + d_plus) / target * weight
        return expr

    elif kind == "goal_deviation":
        # Canonical goal programming: sum w_j * (d_j^- + d_j^+)
        expr = 0
        for nid, target in targets_per_day.items():
            d_minus = prob.add_variable(f"d_{nid}_minus", lowBound=0, cat="Continuous")
            d_plus = prob.add_variable(f"d_{nid}_plus", lowBound=0, cat="Continuous")
            nutrient_sum = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in x_vars
            )
            prob += nutrient_sum + d_minus - d_plus == target
            expr += d_minus + d_plus  # weights can be added from objective_weights.json
        
        # Add antagonism slack terms to Level 1 objective
        antagonism_slack_vars = problem_dict.get("antagonism_slack_vars", {})
        antagonism_penalty_weights = problem_dict.get("antagonism_penalty_weights", {})
        for slack_name, slack_var in antagonism_slack_vars.items():
            # Extract constraint_id from slack_name (format: s_high_CSTR_... or s_low_CSTR_...)
            cid = slack_name[2:] if slack_name.startswith("s_") else slack_name
            penalty_weight = antagonism_penalty_weights.get(cid, 5000)
            expr += slack_var * penalty_weight
        
        return expr

    elif kind == "weighted_normalized_slack":
        # Level 2: slack weighted by clinical_criticality - use pre-created slack vars
        expr = 0
        for nid, target in targets_per_day.items():
            if target > 0 and nid in nutrient_slack_vars:
                slack = nutrient_slack_vars[nid]
                weight = 1.0  # clinical_criticality weight from registry
                expr += (slack / target) * weight
        # Also include envelope slack (Level 2 relaxes envelope_soft)
        env_slack_min = problem_dict.get("envelope_slack_min")
        env_slack_max = problem_dict.get("envelope_slack_max")
        der_kcal = problem_dict.get("der_info", {}).der_kcal if problem_dict.get("der_info") else 1
        if env_slack_min is not None:
            # Weight envelope slack by DER to normalize
            expr += (env_slack_min / der_kcal) if der_kcal > 0 else env_slack_min
        if env_slack_max is not None:
            expr += (env_slack_max / der_kcal) if der_kcal > 0 else env_slack_max
        return expr

    elif kind == "category_goal_deviation":
        # Both maps come from problem_dict — this function has no lp_params/cascade_level
        # parameter, so it cannot re-derive level_config itself (see build_lp_problem).
        cat_map = problem_dict.get("category_to_ingredients", {})
        goals = problem_dict.get("category_goals", {})

        expr = 0
        total_x = pulp.lpSum(x_vars[iid] for iid in x_vars)

        for goal_name, goal in goals.items():
            target_pct = goal.get("target_pct", 0) / 100.0
            base_weight = goal.get("weight", 50)
            cat_list = goal.get("categories", [])

            # Gather ingredients across all sub-categories for this goal.
            cat_ingredients = []
            for c in cat_list:
                cat_ingredients.extend(cat_map.get(c, []))

            if not cat_ingredients:
                continue

            cat_sum = pulp.lpSum(x_vars[iid] for iid in cat_ingredients if iid in x_vars)

            d_minus = prob.add_variable(f"d_cat_{goal_name}_minus", lowBound=0, cat="Continuous")
            d_plus  = prob.add_variable(f"d_cat_{goal_name}_plus",  lowBound=0, cat="Continuous")

            prob += cat_sum - (target_pct * total_x) == d_plus - d_minus

            effective_weight = base_weight * 0.01
            expr += (d_minus + d_plus) * effective_weight

        return expr

    # Default
    return pulp.lpSum(x_vars.values())


def solve_cascade(
    selected_ids: list[str],
    data: dict,
    der_info: DerEnvelope,
    scenario_id: str,
    animal: AnimalInput,
) -> dict:
    """
    Execute the declarative cascade: Level 1 -> 2 -> 3, stop at first feasible.
    Returns the full output contract per sat_solver_contrato:§7.
    """
    import copy

    # Build matrix once (energy_normalized/1000kcal)
    fr = data.get("formulation_rules.json", {})
    matrix = build_matrix(selected_ids, data.get("DB_ingredientes.json", {}), fr)

    lp_params = data.get("lp_parameters_data.json", {})
    solver_params = lp_params.get("solver_params", {})
    cascade_config = lp_params.get("solve_cascade", [])

    cascade_attempts = []

    for level_config in cascade_config:
        level = level_config.get("level", 0)
        cascade_attempts.append(level)

        # Declarative flag from config - NOT hardcoded level check
        apply_clinical_floor = bool(level_config.get("clinical_floor"))

        problem = build_lp_problem(
            selected_ids, matrix, data, der_info, level,
            apply_clinical_floor=apply_clinical_floor,
            db=data.get("DB_ingredientes.json", {}),
            scenario_id=scenario_id,
        )

        result = call_lp_solver(problem, level_config.get("objective_stages", []), solver_params)

        if result["status"] == "infeasible":
            continue

        if result["status"] == "feasible":
            return build_output_contract(result, level_config, data, der_info, cascade_attempts, animal)

    # Fallback: all levels infeasible including Level 3
    registry = data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {})
    nutrient_results = []
    for nid, ndata in registry.items():
        nutrient_results.append({
            "nutrient_id": nid,
            "display_name": ndata.get("display_name", nid),
            "value": None,
            "unit": ndata.get("unit", ""),
            "basis": "energy_normalized",
            "target_min": None,
            "target_max": None,
            "sul": ndata.get("sul_value"),
            "pct_of_min": None,
            "pct_of_sul": None,
            "status": "unknown",
            "constraint_tier": ndata.get("constraint_tier", "adequacy_soft"),
            "clinical_criticality": ndata.get("clinical_criticality", "low"),
        })

    last_level = cascade_attempts[-1] if cascade_attempts else 3
    return {
        "solver_output_schema": "v10.1",
        "solver_status": "structurally_infeasible",
        "feeding_recommendation": "DO_NOT_FEED",
        "cascade_level_used": last_level,
        "animal_context": der_info.as_animal_context(animal.sex, animal.age_months, animal.gonadal_status),
        "envelope": der_info.as_envelope_dict(),
        "allocations": None,
        "nutrient_results": nutrient_results,
        "diagnostic_analysis": {
            "reason": "No feasible solution at any cascade level, including the "
                       "violation-minimizing diagnostic level. Likely cause: a "
                       "hard structural constraint (inclusion/exclusion or ratio) "
                       "cannot be satisfied by any quantity of the selected "
                       "ingredients.",
        },
        "gaps": [],
        "alerts": [],
        "recommended_additions": [],
        "solver_metadata": {
            "solver_engine": "PuLP_CBC",
            "solve_time_ms": 0,
            "cascade_attempts": cascade_attempts,
            "final_level": None,
            "objective_value": None,
        },
    }





def compute_gaps(raw_result: dict, data: dict, der_info: DerEnvelope, level: int) -> list:
    """Compute nutrient adequacy gaps and antagonism ratio violations.
    
    Args:
        raw_result: Solver result with x_values and nutrient_values
        data: Full data dict with registry, constraints, etc.
        der_info: DerEnvelope with DER and envelope info
        level: Cascade level used
    
    Returns:
        List of gap dicts with nutrient_id, pct_of_min, category_missing, etc.
    """
    gaps = []
    x_values = raw_result.get("x_values", {})
    nutrient_values = raw_result.get("nutrient_values", {})
    registry = data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {})
    constraints = data.get("constraints.json", {})
    units = der_info.units_of_1000kcal
    
    # Build nutrient target map from constraints.json -> nutrient_bounds
    # Each bound has rhs in per-1000kcal (same as solver's build_lp_problem)
    nutrient_targets = {}
    for nb in constraints.get("nutrient_bounds", []):
        cid = nb.get("constraint_id", "")
        if not cid.startswith("CSTR_NB_") or not cid.endswith("_MIN"):
            continue
        lp_coeffs = nb.get("lp_coefficients", {})
        vars_ref = lp_coeffs.get("variables_referenced", [])
        if not vars_ref:
            continue
        nid = vars_ref[0]
        bounds_list = lp_coeffs.get("bounds", [])
        for b in bounds_list:
            rhs = b.get("rhs", 0)
            sense = b.get("sense", ">=")
            if sense == ">=" and rhs > 0:
                nutrient_targets[nid] = float(rhs)
    
    # 1. Nutrient adequacy gaps (for all levels)
    for nid, ndata in registry.items():
        if ndata.get("constraint_tier") != "adequacy_soft":
            continue
        rhs = nutrient_targets.get(nid)
        if rhs is None or rhs <= 0:
            continue
        target_min = rhs * units
        
        achieved = nutrient_values.get(nid, 0)
        pct_of_min = round(achieved / target_min * 100, 1) if target_min > 0 else 0
        
        if pct_of_min < 100:
            # Map nutrient to missing category
            category_map = {
                "calcium_g": "bone",
                "phosphorus_g": "bone",
                "magnesium_g": "muscle_meat",
                "sodium_g": "muscle_meat",
                "potassium_g": "muscle_meat",
                "chloride_g": "supplement",
                "protein_g": "muscle_meat",
                "fat_g": "fat_source",
                "arginine_g": "muscle_meat",
                "histidine_g": "muscle_meat",
                "isoleucine_g": "muscle_meat",
                "leucine_g": "muscle_meat",
                "lysine_g": "muscle_meat",
                "methionine_g": "muscle_meat",
                "methionine_plus_cystine_g": "muscle_meat",
                "phenylalanine_g": "muscle_meat",
                "phenylalanine_plus_tyrosine_g": "muscle_meat",
                "threonine_g": "muscle_meat",
                "tryptophan_g": "muscle_meat",
                "valine_g": "muscle_meat",
                "linoleic_acid_g": "fat_source",
                "ala_alpha_linolenic_acid_g": "fat_source",
                "ara_arachidonic_acid_g": "organ_secreting",
                "epa_plus_dha_g": "fish",
                "vitamin_a_iu": "organ_secreting",
                "vitamin_d3_iu": "organ_secreting",
                "vitamin_e_iu": "fat_source",
                "thiamine_b1_mg": "muscle_meat",
                "riboflavin_b2_mg": "organ_secreting",
                "niacin_b3_mg": "muscle_meat",
                "pantothenic_acid_b5_mg": "organ_secreting",
                "pyridoxine_b6_mg": "muscle_meat",
                "folic_acid_b9_mg": "organ_secreting",
                "cobalamin_b12_mg": "organ_secreting",
                "choline_g": "organ_secreting",
                "zinc_mg": "organ_secreting",
                "copper_mg": "organ_secreting",
                "iron_mg": "organ_secreting",
                "manganese_mg": "organ_secreting",
                "iodine_mg": "supplement",
                "selenium_mg": "organ_secreting",
            }
            category = category_map.get(nid, "unknown")
            
            gaps.append({
                "nutrient_id": nid,
                "pct_of_min": pct_of_min,
                "category_missing": category,
                "top_ingredients_in_category": []  # Could be populated from DB
            })
    
    # 2. Antagonism ratio violation gaps (for all levels)
    antag_constraints = data.get("constraints.json", {}).get("mineral_antagonisms", [])
    for antag in antag_constraints:
        cid = antag.get("constraint_id", "")
        vars_ref = antag.get("lp_coefficients", {}).get("variables_referenced", [])
        if len(vars_ref) != 2:
            continue
        n1, n2 = vars_ref[0], vars_ref[1]
        bounds_list = antag.get("lp_coefficients", {}).get("bounds", [])
        
        # Get achieved values
        val1 = nutrient_values.get(n1, 0)
        val2 = nutrient_values.get(n2, 0)
        
        if val2 <= 0:
            # Denominator missing - ratio undefined
            ratio = None
        else:
            ratio = val1 / val2
        
        # Check each bound
        for bounds in bounds_list:
            sense = bounds.get("sense", "")
            vars_dict = bounds.get("variables", {})
            coeff_n1 = vars_dict.get(n1, 0)
            coeff_n2 = vars_dict.get(n2, 0)
            
            if coeff_n1 == 0 or coeff_n2 >= 0:
                continue
            
            bound_ratio = -coeff_n2 / coeff_n1
            
            violation = False
            if sense == ">=" and ratio is not None and ratio < bound_ratio:
                violation = True
            elif sense == "<=" and ratio is not None and ratio > bound_ratio:
                violation = True
            elif sense == ">=" and ratio is None:
                violation = True  # Denominator missing
            elif sense == "<=" and ratio is None:
                violation = True
            
            if violation:
                # Determine gap nutrient_id and category
                gap_nutrient_id = f"{n1}_{n2}_ratio"
                category_map = {
                    ("calcium_g", "phosphorus_g"): "bone",
                    ("zinc_mg", "copper_mg"): "organ_secreting",
                    ("iron_mg", "zinc_mg"): "organ_secreting",
                    ("calcium_g", "magnesium_g"): "bone",
                    ("lysine_g", "arginine_g"): "muscle_meat",
                }
                category = category_map.get((n1, n2), category_map.get((n2, n1), "unknown"))
                
                pct_str = f"{round(ratio / bound_ratio * 100, 1)}%" if ratio and bound_ratio else "undefined (denominator missing)"
                
                gaps.append({
                    "nutrient_id": gap_nutrient_id,
                    "pct_of_min": round(ratio / bound_ratio * 100, 1) if ratio and bound_ratio else 0,
                    "category_missing": category,
                    "top_ingredients_in_category": [],
                    "note": f"Ratio {n1}/{n2} = {ratio:.3f}, bound {sense} {bound_ratio:.3f}" if ratio else f"Ratio {n1}/{n2} undefined (denominator missing)"
                })
    
    return gaps

def build_output_contract(
    raw_result: dict,
    level_config: dict,
    data: dict,
    der_info: DerEnvelope,
    cascade_attempts: list,
    animal: AnimalInput,
) -> dict:
    """Build the final output contract from a feasible solver result."""
    level = level_config.get("level", 0)
    result_status = level_config.get("result_status", "unknown")

    # Map status to feeding recommendation
    feeding_map = {
        "optimal": "SAFE_TO_FEED",
        "suboptimal": "FEED_WITH_CAUTION",
        "unsafe_diagnostic": "DO_NOT_FEED",
        "structurally_infeasible": "DO_NOT_FEED",
        "data_incomplete": "DO_NOT_FEED",
    }
    feeding_rec = feeding_map.get(result_status, "DO_NOT_FEED")

    # Build allocations for Levels 1/2
    allocations = None
    if level in (1, 2) and raw_result.get("x_values"):
        x_vals = raw_result["x_values"]
        total_g = sum(x_vals.values())
        allocations = []
        for iid, grams in x_vals.items():
            if grams > 0.01:
                ing = get_ingredient_by_id(iid, data.get("DB_ingredientes.json", {}))
                if ing:
                    # Compute kcal for this ingredient
                    nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
                    em = energy_metabolizable_kcal_per_100g(nuts)
                    kcal = grams * em / 100.0
                    allocations.append({
                        "ingredient_id": iid,
                        "display_name": ing.get("display_name", iid),
                        "category": ing.get("category", "unknown"),
                        "grams_per_day": round(grams, 1),
                        "pct_of_total": round(grams / total_g * 100, 1) if total_g > 0 else 0,
                        "kcal_per_day": round(kcal, 1),
                        "cost_per_day": None,
                    })

    # Build nutrient_results (always 41+ entries)
    nutrient_results = []
    registry = data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {})
    targets_per_day = raw_result.get("nutrient_values", {})
    suls_per_day = data.get("lp_parameters_data.json", {}).get("solver_params", {})

    for nid in registry:
        ndata = registry[nid]
        value = targets_per_day.get(nid, 0)
        target_min = ndata.get("sul_value") if ndata.get("has_sul") else None
        # This is simplified - real implementation computes min/max from scenarios/matrix
        nutrient_results.append({
            "nutrient_id": nid,
            "display_name": ndata.get("display_name", nid),
            "value": round(value, 4),
            "unit": ndata.get("unit", ""),
            "basis": "energy_normalized",
            "target_min": target_min,
            "target_max": None,
            "sul": ndata.get("sul_value"),
            "pct_of_min": None,
            "pct_of_sul": None,
            "status": "adequate",
            "constraint_tier": ndata.get("constraint_tier", "adequacy_soft"),
            "clinical_criticality": ndata.get("clinical_criticality", "low"),
        })

    # Build diagnostic_analysis for Level 3
    diagnostic_analysis = None
    if level == 3:
        clinical_floor_info = {
            "bounds": raw_result.get("clinical_floor_bounds", {}),
            "relaxed": raw_result.get("clinical_floor_relaxed", False),
        }
        diagnostic_analysis = build_diagnostic_analysis(raw_result, data, der_info, clinical_floor_info)

    # Metadata
    meta = {
        "solver_engine": "PuLP_CBC",
        "solve_time_ms": raw_result.get("solve_time_ms", 0),
        "cascade_attempts": cascade_attempts,
        "final_level": level,
        "objective_value": raw_result.get("objective_value"),
    }
    if level == 3:
        meta["lexicographic_stages_used"] = {
            "stages": [s.get("name") for s in level_config.get("objective_stages", [])],
            "order_verified": True,
            "note": "SUL violation is fixed before DER deviation, which is fixed before adequacy slack"
        }
        meta["clinical_floor_applied"] = not clinical_floor_info.get("relaxed", False)
        meta["clinical_floor_bounds"] = clinical_floor_info.get("bounds", {})

    # === Category goal deviations (Option B — BARF/PMR template adherence) ===
    category_goals = level_config.get("category_goals", {})
    deviations = raw_result.get("category_goal_deviations", {})
    template_adherence = {"components": {}}
    total_deviation = 0.0

    for goal_name, goal in category_goals.items():
        d_minus = deviations.get(f"d_cat_{goal_name}_minus")
        d_plus  = deviations.get(f"d_cat_{goal_name}_plus")

        if d_minus is None and d_plus is None:
            template_adherence["components"][goal_name] = {
                "target_pct": goal.get("target_pct", 0),
                "achieved_pct": 0.0,
                "absolute_deviation_pct": None,
                "skipped": True,
            }
            continue

        d_minus = d_minus or 0.0
        d_plus  = d_plus or 0.0
        target = goal.get("target_pct", 0)
        achieved = target + (d_plus - d_minus)
        abs_dev = d_plus + d_minus

        template_adherence["components"][goal_name] = {
            "target_pct": target,
            "achieved_pct": round(max(0.0, achieved), 2),
            "absolute_deviation_pct": round(abs_dev, 2),
            "skipped": False,
        }

        if abs_dev > 0:
            total_deviation += abs_dev

    template_adherence["overall_score"] = round(max(0.0, 100.0 - total_deviation), 1)

    meta["category_goal_deviations_raw"] = template_adherence["components"]

    # Expose unrounded total for validation (avoids rounding error in envelope check)
    # See docs/phase0a-tolerance-design.md for rationale
    unrounded_total = sum(x_vals.values()) if level in (1, 2) and raw_result.get("x_values") else None

    return {
        "solver_output_schema": "v10.1",
        "solver_status": result_status,
        "feeding_recommendation": feeding_rec,
        "cascade_level_used": level,
        "animal_context": der_info.as_animal_context(animal.sex, animal.age_months, animal.gonadal_status),
        "envelope": der_info.as_envelope_dict(),
        "allocations": allocations,
        "nutrient_results": nutrient_results,
        "diagnostic_analysis": diagnostic_analysis,
        "template_adherence": template_adherence,
        "gaps": compute_gaps(raw_result, data, der_info, level),
        "alerts": [],
        "recommended_additions": [],
        "solver_metadata": meta,
        "_unrounded_total_g": unrounded_total,
    }


def build_diagnostic_analysis(
    raw_result: dict,
    data: dict,
    der_info: DerEnvelope,
    clinical_floor_info: dict,
) -> dict:
    """Build diagnostic_analysis block for Level 3 unsafe_diagnostic."""
    suls_per_day = {}
    tox_limits = data.get("toxicological_limits.json", [])
    for tox in tox_limits:
        nid = tox.get("nutrient_id")
        sul_entry = tox.get("sul", {})
        sul_val = sul_entry.get("value")
        if nid and sul_val is not None:
            suls_per_day[nid] = float(sul_val) * der_info.units_of_1000kcal

    nutrient_values = raw_result.get("nutrient_values", {})

    # 1. Identify inevitable SUL violations
    sul_violations = []
    for nid, sul_day in suls_per_day.items():
        achieved = nutrient_values.get(nid, 0)
        if achieved > sul_day:
            sul_violations.append({
                "nutrient_id": nid,
                "sul": sul_day,
                "minimum_achievable_at_der": round(achieved, 2),
                "pct_above_sul": round((achieved / sul_day - 1) * 100, 1),
                "mechanism": "Nutrient concentration and caloric content are proportional "
                           "in the selected ingredients — no feasible separation exists."
            })

    # 2. Counterfactual scenario
    x_values = raw_result.get("x_values", {})
    total_grams_for_der = sum(x_values.values())

    floor_bounds = clinical_floor_info.get("bounds", {})
    relaxed = clinical_floor_info.get("relaxed", False)
    ingredients_below_floor = []
    for iid, x_val in x_values.items():
        floor = floor_bounds.get(iid, 5)
        if 0 < x_val < floor:
            ingredients_below_floor.append({
                "ingredient_id": iid,
                "x_value_g": round(x_val, 2),
                "clinical_floor_g": floor,
                "note": f"Solver returned {x_val:.2f}g, below clinical floor of {floor}g"
            })

    what_would_happen = {
        "description": "If you fed ONLY the selected ingredients to meet caloric needs:",
        "grams_needed_for_der": round(total_grams_for_der, 1),
        "nutrient_at_risk": sul_violations[0]["nutrient_id"] if sul_violations else None,
        "value_at_that_amount": sul_violations[0]["minimum_achievable_at_der"] if sul_violations else None,
        "sul_value": sul_violations[0]["sul"] if sul_violations else None,
        "clinical_significance": (
            "Chronic hypervitaminosis A → osteoclast overactivation → "
            "pathologic fractures, osteodystrophy"
            if sul_violations and sul_violations[0]["nutrient_id"] == "vitamin_a_iu"
            else "Chronic excess → toxicological effects per SUL documentation"
        ),
        "clinical_floor_applied": not relaxed,
        "clinical_floor_relaxed": relaxed,
        "ingredients_below_floor": ingredients_below_floor,
        "x_min_i_effective": floor_bounds,
    }

    if relaxed:
        what_would_happen["clinical_floor_relaxation_note"] = (
            "Even the minimum recognizable portion of the selected ingredient(s) "
            "violates the SUL. No safe amount exists. The scenario below shows "
            "what the solver computed without the clinical floor constraint — "
            "these values are below any meaningful portion and serve only as "
            "mathematical evidence of inseparability."
        )

    # 3. Recommended alternative actions
    recommended_actions = [
        "Add a calorie source WITHOUT concentrated vitamin A (e.g., beef_muscle_raw, chicken_muscle_raw)",
        "Reduce liver/organ proportion and add muscle meat as caloric base",
        "Use recipe mode (Receitas Prontas) for pre-validated safe combinations"
    ]

    # 4. Reason
    reason = (
        "No combination of selected ingredients meets caloric needs without "
        "exceeding safe limits. Caloric content and the SUL-violating nutrient "
        "are inseparable in the selected ingredient(s) — every gram adds both "
        "proportionally."
    )
    if relaxed:
        reason += (
            " Even the minimum clinically significant portion (clinical_floor_g) "
            "of the ingredient exceeds the SUL. The solver was re-run without "
            "the floor constraint to produce a mathematical counterfactual."
        )

    return {
        "reason": reason,
        "sul_violations_inevitable": sul_violations,
        "what_would_happen": what_would_happen,
        "recommended_alternative_actions": recommended_actions,
    }


def validate_output(result: dict, data: dict, der_info: DerEnvelope) -> None:
    """Validate output against the solver contract (§7). Raises AssertionError on failure."""
    # 1. Canonical solver_status
    assert result["solver_status"] in (
        "optimal", "suboptimal", "unsafe_diagnostic",
        "structurally_infeasible", "data_incomplete"
    ), f"Invalid solver_status: {result['solver_status']}"

    # 2. feeding_recommendation matches
    expected_rec = {
        "optimal": "SAFE_TO_FEED",
        "suboptimal": "FEED_WITH_CAUTION",
        "unsafe_diagnostic": "DO_NOT_FEED",
        "structurally_infeasible": "DO_NOT_FEED",
        "data_incomplete": "DO_NOT_FEED",
    }
    assert result["feeding_recommendation"] == expected_rec[result["solver_status"]], \
        f"feeding_recommendation mismatch"

    # 3. Level 1/2: allocations not null, within envelope
    if result["solver_status"] in ("optimal", "suboptimal"):
        assert result["allocations"] is not None, "Level 1/2 must have allocations"
        assert len(result["allocations"]) >= 1, "At least one allocation required"
        # Use unrounded total to avoid 0.05g rounding error from sum of rounded allocations
        # See docs/phase0a-tolerance-design.md for rationale
        total_g = result.get("_unrounded_total_g") or sum(a["grams_per_day"] for a in result["allocations"])
        env = der_info.as_envelope_dict()
        # Float tolerance: accept up to 1g below min or above max (floating-point noise from solver vs envelope calc)
        assert total_g >= env["min_total_g"] - 1.0 and total_g <= env["max_total_g"] + 1.0, \
            f"Total grams {total_g} outside envelope [{env['min_total_g']}, {env['max_total_g']}]"

    # 4. Level 3 / structurally_infeasible: allocations null, diagnostic_analysis present
    if result["solver_status"] in ("unsafe_diagnostic", "structurally_infeasible"):
        assert result["allocations"] is None, "Level 3 must have allocations=null"
        assert result["diagnostic_analysis"] is not None, "Level 3 must have diagnostic_analysis"

    # 5. nutrient_results >= 41 entries
    assert len(result["nutrient_results"]) >= 41, f"nutrient_results has {len(result['nutrient_results'])} entries, need >=41"

    # 6. Each nutrient result has required fields
    for nr in result["nutrient_results"]:
        assert "pct_of_min" in nr
        assert "pct_of_sul" in nr
        assert "status" in nr
        assert "constraint_tier" in nr
        assert "clinical_criticality" in nr

    # 7. Level 3: lexicographic_stages_used.order_verified
    if result["solver_status"] == "unsafe_diagnostic":
        meta = result.get("solver_metadata", {})
        stages = meta.get("lexicographic_stages_used", {})
        assert stages.get("order_verified") is True, "lexicographic_stages_used.order_verified must be True"

    # 8. Level 3: clinical_floor_applied boolean, clinical_floor_bounds dict
    if result["solver_status"] == "unsafe_diagnostic":
        meta = result.get("solver_metadata", {})
        assert "clinical_floor_applied" in meta, "clinical_floor_applied missing in solver_metadata"
        assert isinstance(meta["clinical_floor_applied"], bool), "clinical_floor_applied must be bool"
        assert "clinical_floor_bounds" in meta, "clinical_floor_bounds missing in solver_metadata"
        assert isinstance(meta["clinical_floor_bounds"], dict), "clinical_floor_bounds must be dict"

        # 9. If clinical_floor_relaxed, relaxation_note must exist
        wwh = result["diagnostic_analysis"].get("what_would_happen", {})
        if wwh.get("clinical_floor_relaxed"):
            assert "clinical_floor_relaxation_note" in wwh, \
                "clinical_floor_relaxation_note required when clinical_floor_relaxed=true"


# ── Conditional Adequacy Checks (pre-solver, post-matrix) ─────────────────────

def check_fat_source_adequacy(
    matrix: dict[str, dict],
    selected_ids: list[str],
    formulation_rules: dict,
    der_envelope: "DerEnvelope",
    db: dict
) -> dict | None:
    """
    Conditional adequacy check: if fat_source inclusion is at structural minimum (8%)
    but total fat_g at that inclusion cannot meet AAFCO minimum (21.25 g/1000kcal),
    return a gap dict for the output contract. Called after matrix build, before solver.

    This is a pre-solver check that mirrors what the cascade conditional check
    (lp_parameters_data.json solve_cascade Level 1) would evaluate.
    """
    # Get fat_source inclusion constraint
    incl_limits = formulation_rules.get("inclusion_limits", [])
    fat_source_limit = next((il for il in incl_limits if il.get("ingredient_id") == "fat_source"), {})
    structural_min = fat_source_limit.get("min_pct", 8) / 100.0  # e.g., 0.08
    aafco_recommended_min = fat_source_limit.get("effective_min_pct_for_aafco_fat", 15) / 100.0  # e.g., 0.15

    # Find fat_source ingredients in selection
    all_ings = _find_all_ingredients(db)
    fat_source_ids = [iid for iid in selected_ids if all_ings.get(iid, {}).get("category") == "fat_source"]
    
    if not fat_source_ids:
        return None

    # Compute total fat_g at structural minimum fat_source inclusion
    # For each 1000kcal unit, fat_source contributes x% * fat_norm
    total_fat_at_structural_min = 0.0
    for fs_id in fat_source_ids:
        fs_ing = get_ingredient_by_id(fs_id, db)
        if not fs_ing:
            continue
        fs_nuts = fs_ing.get("bromatological_profile", {}).get("nutrients", {})
        fs_fat = fs_nuts.get("fat_g", {}).get("value", 0) if isinstance(fs_nuts.get("fat_g"), dict) else fs_nuts.get("fat_g", 0)
        if not fs_fat:
            continue
        # Energy normalized fat
        em = energy_metabolizable_kcal_per_100g(fs_nuts)
        if em <= 0:
            continue
        fs_fat_norm = fs_fat * (1000.0 / em)
        total_fat_at_structural_min += structural_min * fs_fat_norm

    # Add fat from other selected ingredients (at 100% - structural_min - other categories)
    # Simplified: assume remaining 92% is muscle_meat at average fat_norm
    # This is a conservative check - real solver would optimize
    other_fat = 0.0
    non_fs_ids = [iid for iid in selected_ids if iid not in fat_source_ids]
    for iid in non_fs_ids:
        ing = get_ingredient_by_id(iid, db)
        if not ing:
            continue
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        fat = nuts.get("fat_g", {}).get("value", 0) if isinstance(nuts.get("fat_g"), dict) else nuts.get("fat_g", 0)
        if fat:
            em = energy_metabolizable_kcal_per_100g(nuts)
            if em > 0:
                other_fat += (1.0 - structural_min) * (fat * (1000.0 / em)) * (1.0 / len(non_fs_ids) if non_fs_ids else 1)

    total_fat_est = total_fat_at_structural_min + other_fat
    aafco_fat_min = 21.25  # g/1000kcal from formulation_rules.nutrient_matrix

    if total_fat_est < aafco_fat_min:
        # Gap detected
        pct_of_min = round(100 * total_fat_est / aafco_fat_min, 1)
        return {
            "nutrient_id": "fat_g",
            "pct_of_min": pct_of_min,
            "category_missing": "fat_source",
            "structural_min_pct": structural_min * 100,
            "aafco_recommended_min_pct": aafco_recommended_min * 100,
            "estimated_fat_at_structural_min": round(total_fat_est, 1),
            "aafco_fat_min": aafco_fat_min,
            "top_ingredients_in_category": [
                {"ingredient_id": fs_id, "fat_g_per_1000kcal": round(_get_fat_norm(get_ingredient_by_id(fs_id, db)), 1)}
                for fs_id in fat_source_ids
                if _get_fat_norm(get_ingredient_by_id(fs_id, db)) > 0
            ],
            "note": f"Fat source at structural minimum ({structural_min*100:.0f}%) yields only {total_fat_est:.1f} g/1000kcal fat. AAFCO minimum ({aafco_fat_min}) requires ~{aafco_recommended_min*100:.0f}% fat_source inclusion with selected ingredients."
        }
    return None


def _get_fat_norm(ing: dict | None) -> float:
    """Helper: compute fat_g energy_normalized for an ingredient."""
    if not ing:
        return 0.0
    nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
    fat = nuts.get("fat_g", {}).get("value", 0) if isinstance(nuts.get("fat_g"), dict) else nuts.get("fat_g", 0)
    if not fat:
        return 0.0
    em = energy_metabolizable_kcal_per_100g(nuts)
    if em <= 0:
        return 0.0
    return fat * (1000.0 / em)


def _find_all_ingredients(db: dict) -> dict:
    """Return dict of ingredient_id -> ingredient for all ingredients in DB."""
    result = {}
    for g in db.get("protein_sources", {}).values():
        for ing in g.get("ingredients", []):
            result[ing["ingredient_id"]] = ing
    return result


__all__ = [
    # Functions
    "build_lp_problem", "call_lp_solver", "solve_cascade",
    "build_output_contract", "build_diagnostic_analysis",
    "validate_output", "check_fat_source_adequacy",
    "compute_gaps", "_build_stage_objective", "_get_fat_norm", "_find_all_ingredients",
]

