#!/usr/bin/env python3
"""
Update audit_provenance.json with correct FDC refs for chicken ingredients.

Changes:
1. Add REF_USDA_FDC_171469 (back) — CONFIRMED, applies_to chicken_back_raw
2. Update REF_USDA_FDC_172382 (neck) — CONFIRMED, now applies_to chicken_neck_raw
3. Update REF_USDA_FDC_171047 (giblets+neck) — no longer used, mark as COPY_PASTE_ERROR_CORRECTED
"""

import json
import sys
from pathlib import Path


def main():
    prov_path = Path(__file__).resolve().parent.parent.parent / "data" / "audit_provenance.json"
    with open(prov_path, "r", encoding="utf-8") as f:
        prov = json.load(f)
    
    refs = prov["references"]
    
    # 1. Add REF_USDA_FDC_171469 (correct FDC for chicken_back_raw)
    refs["REF_USDA_FDC_171469"] = {
        "text": "USDA FoodData Central ID 171469 — 'Chicken, broilers or fryers, back, meat and skin, raw' (SR Legacy, NDB #5048). Fonte primaria para micronutrientes de chicken_back_raw (meat+skin, sem osso). Valores escalados pela fracao de carne (56%) para bone-in RMB.",
        "doc_ids": [],
        "quality_flag": "CONFIRMED",
        "line_references": [],
        "applies_to": ["chicken_back_raw"],
        "nutrient_count": 31,
        "note": "Verificado via FDC API em 2026-07-22. Descricao confere: back, meat and skin, raw. Dados SR Legacy, NDB #5048."
    }
    
    # 2. Update REF_USDA_FDC_172382 (now correct for chicken_neck_raw)
    refs["REF_USDA_FDC_172382"] = {
        "text": "USDA FoodData Central ID 172382 — 'Chicken, broilers or fryers, neck, meat and skin, raw' (SR Legacy, NDB #5084). Fonte primaria para micronutrientes de chicken_neck_raw (meat+skin, sem osso). Valores escalados pela fracao de carne (64%) para bone-in RMB. Anteriormente atribuido incorretamente a chicken_back_raw — corrigido em 2026-07-22.",
        "doc_ids": [],
        "quality_flag": "CONFIRMED",
        "line_references": [],
        "applies_to": ["chicken_neck_raw"],
        "nutrient_count": 31,
        "note": "Verificado via FDC API em 2026-07-22. Descricao confere: neck, meat and skin, raw. Dados SR Legacy, NDB #5084. Corrigido de chicken_back_raw (atribuicao incorreta anterior)."
    }
    
    # 3. Update REF_USDA_FDC_171047 (no longer used — was giblets+neck composite)
    refs["REF_USDA_FDC_171047"] = {
        "text": "USDA FoodData Central ID 171047 — 'Chicken, broilers or fryers, meat and skin and giblets and neck, raw' (SR Legacy). CORRECAO DE ERRO: este FDC ID e um corte composto (giblets+neck), nao puro chicken neck. Anteriormente atribuido incorretamente a chicken_neck_raw — corrigido em 2026-07-22. chicken_neck_raw agora usa REF_USDA_FDC_172382 (neck puro).",
        "doc_ids": [],
        "quality_flag": "COPY_PASTE_ERROR_CORRECTED",
        "line_references": [],
        "applies_to": [],
        "nutrient_count": 0,
        "note": "FDC 171047 nao e mais usado por nenhum ingrediente no DB. Era um corte composto (giblets+inflava Vit A para 771 IU). Corrigido para REF_USDA_FDC_172382 (neck puro, 216 IU)."
    }
    
    # Save
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2, ensure_ascii=False)
    
    print(f"Updated audit_provenance.json:")
    print(f"  Added: REF_USDA_FDC_171469 (CONFIRMED, chicken_back_raw)")
    print(f"  Updated: REF_USDA_FDC_172382 (CONFIRMED, chicken_neck_raw)")
    print(f"  Updated: REF_USDA_FDC_171047 (COPY_PASTE_ERROR_CORRECTED, no longer used)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
