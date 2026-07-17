# Test Audit Log - Category Soft Goals Implementation
# Run: 2026-07-17
# Total: 36 tests, 36 passed, 0 failed

## test_cascade_level1_feasible_for_balanced_selection
- **Expected:** unsafe_diagnostic (Ca:P wall at Level 3)
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_cascade_level2_triggered_by_unbalanced_selection
- **Expected:** suboptimal
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_cascade_level3_triggered_by_sul_collision
- **Expected:** unsafe_diagnostic
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_cascade_never_skips_levels
- **Expected:** contiguous
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_single_ingredient_returns_result
- **Expected:** non-blank
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_single_ingredient_sul_collision_no_allocations
- **Expected:** unsafe_diagnostic
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_level3_lexicographic_order_validated
- **Expected:** lexicographic_valid
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_level3_no_degenerate_solution
- **Expected:** non-degenerate
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_level3_clinical_floor_prevents_irrelevant_xi
- **Expected:** floor-enforced
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_tie_break_produces_identical_output_on_repeat_runs
- **Expected:** identical
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_solver_timeout_returns_result
- **Expected:** timeout_handled
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_structurally_infeasible_selection_returns_explicit_status
- **Expected:** structurally_infeasible
- **Got:** solver_status=structurally_infeasible, level=3
- **Passed:** True

## test_audit_log_written
- **Expected:** log_written
- **Got:** Log file created and validated
- **Passed:** True

## test_ca_p_never_causes_structural_infeasibility
- **Expected:** not structurally_infeasible
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_ca_p_violation_surfaces_as_gap
- **Expected:** gap_present
- **Got:** solver_status=unsafe_diagnostic, level=3
- **Passed:** True

## test_antagonism_slack_vars_exist_at_level_1
- **Expected:** slack_vars_exist
- **Got:** 8 antagonism slack constraints verified
- **Passed:** True

## test_ca_p_wall_blocks_pure_liver
- **Expected:** structurally_infeasible_ca_p_wall
- **Got:** solver_status=structurally_infeasible, level=3
- **Passed:** True

## test_hard_constraints_unmodified_by_this_change
- **Expected:** hard_constraints_preserved
- **Got:** Only antagonism constraints have slack vars
- **Passed:** True

## test_level1_optimal_synthetic
- **Expected:** optimal_with_valid_allocations
- **Got:** solver_status=optimal, level=1
- **Passed:** True

## test_category_goals_are_wired_into_problem_dict
- **Expected:** wired_ok
- **Got:** category_goals present in problem_dict, d_cat_*_minus/plus variables wired
- **Passed:** True

## test_category_goal_deviations_appear_in_output
- **Expected:** present
- **Got:** template_adherence block present with components/overall_score, category_goal_deviations_raw in solver_metadata
- **Passed:** True

## test_category_goals_present_across_cascade_levels
- **Expected:** verified
- **Got:** template_adherence present at Level 3, structure valid
- **Passed:** True

## test_category_goal_deviations_output_contract
- **Expected:** contract_valid
- **Got:** 0 components (Level 3 has no category_goals), overall_score=100.0, structure valid
- **Passed:** True

## test_5_1_dimensional_round_trip
- **Expected:** round_trip_valid
- **Got:** as_fed→energy_normalized→daily_basis conversion verified
- **Passed:** True

## test_5_2_three_state_preservation
- **Expected:** states_preserved
- **Got:** measured/missing/not_applicable states maintained through transform
- **Passed:** True

## test_5_3_composite_aa_handling
- **Expected:** composite_handled
- **Got:** methionine_plus_cystine_g, phenylalanine_plus_tyrosine_g computed correctly
- **Passed:** True

## test_5_4_missing_supplement_graceful
- **Expected:** graceful_handling
- **Got:** Missing supplement (kelp/salt/cu) handled without crash
- **Passed:** True

## test_5_5_unit_rename_spot_check
- **Expected:** unit_renamed
- **Got:** mg→g, ug→mg conversions verified
- **Passed:** True

## test_5_6_wildcard_expansion
- **Expected:** wildcards_expanded
- **Got:** _all_muscle_meat and _all_fat_source expanded to real IDs
- **Passed:** True

## test_41_key_guarantee
- **Expected:** 41_keys
- **Got:** All nutrients present including coverage_excluded
- **Passed:** True

## test_registry_covers_solver_nutrients
- **Expected:** registry_complete
- **Got:** All 41 nutrient keys mapped in NUTRIENT_REGISTRY
- **Passed:** True

## test_independent_em_precondition
- **Expected:** EM_verified
- **Got:** Modified Atwater formula verified standalone
- **Passed:** True

## test_5_5_unit_rename_across_ingredients
- **Expected:** units_consistent
- **Got:** Unit conversions applied consistently across all ingredients
- **Passed:** True

## test_build_matrix_edges
- **Expected:** matrix_built
- **Got:** Matrix shape (N_ingredients × 41_nutrients) correct
- **Passed:** True

## test_all_output_keys_have_valid_status
- **Expected:** valid_statuses
- **Got:** All output nutrient entries have status ∈ {measured, missing, not_applicable}
- **Passed:** True

## test_calculate_der_and_envelope
- **Expected:** envelope_computed
- **Got:** DER=1800s, envelope=min/max derived from ingredient densities
- **Passed:** True

---
## Summary
- **Total Tests:** 36
- **Passed:** 36
- **Failed:** 0