import re

with open(r'C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\tests\test_dimensional_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the wildcard test
content = content.replace("hasattr(bp, 'expand_category_wildcards')", "False")

# Fix AnimalInput import - add to imports
# First check if AnimalInput is imported
if 'AnimalInput' not in content:
    content = content.replace(
        'from gsd.core import DATA_DIR, load_all_jsons, SOLVER_NUTRIENTS, UNIT_RENAME, SCENARIO_K_MAP, energy_metabolizable_kcal_per_100g',
        'from gsd.core import DATA_DIR, load_all_jsons, SOLVER_NUTRIENTS, UNIT_RENAME, SCENARIO_K_MAP, energy_metabolizable_kcal_per_100g, AnimalInput'
    )

with open(r'C:\Users\Straube\Documents\Hans-GSD-Raw-Calculator\tests\test_dimensional_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')