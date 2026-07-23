# Hardened Remediation Plan: Provenance Resolution for Orphan References in `DB_ingredientes.json`
*Version: 3.0.1-HARDENED-VERIFIED | Status: PARTIALLY_EXECUTED (mechanical patch ready) | Target Agent: 9B Ornith Local Model + human review*

This supersedes `provenance_remediation_plan.md` v2.0.0-HARDENED. That version was a well-structured **template** written without access to the actual data files — its example patch commands, schema assumptions, and task counts don't match what's really in the repo. This version was built by running deterministic scripts against the real `DB_ingredientes.json` and `audit_provenance.json`, and by verifying a sample of claimed external sources against the live web. It ships with working code, not just prose.

---

## 1. Executive Summary — what changed from the v2.0.0 draft

| # | Draft assumed | Reality (verified 2026-07-22) |
|---|---|---|
| 1 | New `references` entries look like `{"status": "INFERRED", "source": "...", "confidence": "HIGH"}` | Real schema is `{text, doc_ids, quality_flag, line_references, [applies_to, risk_type, nutrient_count, parsed_data, note]}`. The draft's own example `jq` patch command would have written schema-inconsistent data into the file. See §3. |
| 2 | 451 orphan refs, one task each | **453 orphan occurrences, but only 284 unique `source_ref`/`anomaly_ref` values.** Registering one ref resolves every occurrence that shares it — the real atomic-task count is 284, not 451, and 5 of those 284 alone account for 174 occurrences (38%). See §2. |
| 3 | The orphan preflight script (`v.get('source_ref','')`) is correct | It has a blind spot: it only checks the `source_ref` field, so it silently misses orphans on `anomaly_ref` (used by `missing`/`not_applicable` status entries). Found 2 such orphans it would never report. See §2.3 and the corrected script in §6. |
| 4 | All 451(→284) refs need the same treatment | **202 of 284 are mechanically resolvable** from data already declared in the DB (internal estimates/computations/domain rules) — no external lookup needed, and a ready-to-apply patch already exists for them (§4). **82 genuinely require checking an external database or publication** before they can be marked `CONFIRMED` (§5) — fabricating that confirmation would be the exact hallucination this whole effort exists to prevent. |
| 5 | (not considered) | Spot-checking the highest-leverage external refs against USDA FoodData Central found a **real data-integrity bug**: `REF_USDA_FDC_172382` is assigned to `chicken_back_raw` in the DB, but FDC ID 172382 is actually "Chicken, broilers or fryers, neck, meat, and skin, raw" — chicken **neck**, not back. See §5.2. |

---

## 2. Corrected Audit

Produced by `audit_orphans.py` (included in deliverables, §8) walking every `nutrients.*.source_ref`, `nutrients.*.anomaly_ref`, and `safety_alerts[].source_ref` in `DB_ingredientes.json` and checking membership against `audit_provenance.json['references']`. No LLM judgment involved — plain dict lookups.

### 2.1 Headline numbers

- **453** total orphan occurrences across the DB
- **451** of those are on `measured`-status entries via `source_ref` (this matches the original plan's reported figure exactly — confirms that number was real, not fabricated)
- **2** are on `not_applicable`-status entries via `anomaly_ref` — invisible to the original plan's own preflight script (§2.3)
- **284** unique `ref` *values* need a registry entry. Because many occurrences share a ref, registering 284 values resolves all 453 occurrences.

### 2.2 Breakdown by prefix (unique refs / occurrences / resolution class)

| Prefix | Unique | Occurrences | Class |
|---|---:|---:|---|
| `REF_USDA` | 30 | 199 | Mixed — 18 unique are `MECHANICAL` (`_COMPUTED` suffix), 12 are `EXTERNAL` |
| `REF_ESTIMATED` | 154 | 154 | MECHANICAL |
| `REF_COFID` | 46 | 46 | EXTERNAL |
| `REF_COMPUTED` | 14 | 14 | MECHANICAL |
| `REF_NA` | 13 | 13 | MECHANICAL |
| `REF_MILAGRES2020` | 11 | 11 | EXTERNAL |
| `REF_LITERATURE` | 4 | 4 | EXTERNAL |
| `REF_INFERRED` | 3 | 3 | MECHANICAL |
| `REF_SCHWEIGERT1943` | 3 | 3 | EXTERNAL |
| `REF_WHOLEFOODCATALOG` | 2 | 2 | EXTERNAL |
| `REF_FRIDA708` / `REF_FRIDA712` / `REF_FRIDA` | 3 | 3 | EXTERNAL |
| `REF_MATVARETABELLEN` | 1 | 1 | EXTERNAL |
| **Total** | **284** | **453** | 202 MECHANICAL / 82 EXTERNAL |

**Classification rule** (deterministic, in `audit_orphans.py::classify`): `REF_ESTIMATED`, `REF_COMPUTED`, `REF_INFERRED`, `REF_NA`, and any `REF_USDA_*_COMPUTED` are **MECHANICAL** — they assert an internal estimation/computation, not a specific external source, so a provenance record can be generated from data the DB already carries. Everything else names a specific external database or publication as its source (`REF_COFID`, bare `REF_USDA_FDC_<id>`, `REF_MILAGRES2020`, etc.) and is **EXTERNAL_VERIFICATION_REQUIRED** — it doesn't get marked `CONFIRMED` until someone (human or tool-using agent) actually checks that source.

### 2.3 The blocker example, verified

```
AssertionError: beef_muscle_raw.chloride_mg: orphan source_ref REF_COFID_CHLORIDE_BEEF_MUSCLE
```
Confirmed real: `beef_muscle_raw.chloride_mg` = 66.0 mg, `source_ref = "REF_COFID_CHLORIDE_BEEF_MUSCLE"`, not present in `audit_provenance.json`. It's one of the 46 `REF_COFID` refs — **EXTERNAL**, occurrence_count 1. It cannot be resolved by the mechanical patch; it needs an actual CoFID lookup (§5).

### 2.4 The preflight script's blind spot

The original plan's guardrail script:
```python
orphans=[(i,k) for g in db['protein_sources'].values() for i in g['ingredients']
         for k,v in i.get('bromatological_profile',{}).get('nutrients',{}).items()
         if v.get('source_ref','') and v.get('source_ref','') not in p]
```
only reads `v.get('source_ref','')`. Entries with `status: "not_applicable"` don't have a `source_ref` key at all — they have `anomaly_ref` — so this check silently returns `0` for them even when orphaned. Two real orphans exist there today: `beef_blood_raw.epa_plus_dha_g` and `beef_blood_raw.ala_alpha_linolenic_acid_g`, both pointing to unregistered `anomaly_ref`s. The corrected check ships as `audit_orphans.py` (§8) — it covers both `source_ref` and `anomaly_ref`, plus `safety_alerts[].source_ref`, which the fix above alone doesn't.

---

## 3. The real provenance-entry contract

No JSON Schema for `audit_provenance.json`'s `references` registry existed before this pass — `db_ingredientes_schema.json` only constrains the **key format** (`^REF_[A-Z0-9_]+$`) via `SourceRef`, not the **registered value's shape**. That's exactly the gap that let the v2.0.0 draft assume a plausible-but-wrong structure. I reverse-engineered the real contract from all 154 existing entries and wrote it as `audit_provenance_references.schema.json` (deliverable, §8). Summary:

```jsonc
{
  "text": "string OR object",      // required. 148/154 existing entries: string. 6/154 (growth/anthropometric refs): object — a legacy inconsistency, don't copy it for new entries.
  "doc_ids": ["DOC1"],             // required, array. MAY be [] — 11/154 existing entries use [] for sources cited by name only in `text` (e.g. REF_NRC_2006, REF_DOGSFIRST_IE) rather than tracked in source_documents.
  "quality_flag": "CONFIRMED",     // required. One of: CONFIRMED, INFERRED, LITERATURE_COMPOSITE, COPY_PASTE_ERROR_CORRECTED, UNIT_INCONSISTENCY_RESOLVED, AUTHORITATIVE_DATABASE
  "line_references": ["lines 1-2"],// required, array. MAY be [] alongside empty doc_ids.
  "applies_to": ["ingredient_id"], // optional, 58/154 existing entries
  "risk_type": "...",              // optional, 50/154 — only seen on nutrient-antagonism/algorithm refs
  "nutrient_count": 12,            // optional, 8/154
  "parsed_data": {...},            // optional, 6/154 — duplicates the object-shaped `text` entries
  "note": "..."                    // optional, 1/154 (used for a downgrade history note)
}
```

**Rule of thumb for the 9B model or any downstream agent:** `quality_flag: CONFIRMED` or `AUTHORITATIVE_DATABASE` means someone actually checked the cited source. Never set either without verification — set `INFERRED` instead and flag for human follow-up. This is the single most important guardrail in this document; the whole point of a provenance registry is that `CONFIRMED` means something.

---

## 4. MECHANICAL category — ready to apply (202 refs, 202 occurrences)

These assert an internal estimate, computation, or domain rule already recorded in the DB (value + `confidence` +, where present, a declared `reason`) — not a specific external source. A provenance record for them is a **formalization of data that already exists**, not a new claim, so it can be generated safely by script.

**Deliverable:** `mechanical_provenance_patch.json` — 202 entries, each schema-valid per §3, generated by `generate_mechanical_patch.py`. Text is written in pt-BR to match the existing corpus. Example (one of the 14 `REF_COMPUTED` entries):

```json
"REF_COMPUTED_MET_CYS_BEEF_TAIL": {
  "text": "Valor de 'methionine_plus_cystine_g' = 0.6 g para 'beef_tail_raw' computado internamente combinando componente medido com estimativa complementar (ex.: razao tipica de tecido para par aminoacidico). Confidence declarada: 'inferred'.",
  "doc_ids": [],
  "quality_flag": "INFERRED",
  "line_references": [],
  "applies_to": ["beef_tail_raw"],
  "nutrient_count": 1,
  "note": "Gerado automaticamente por generate_mechanical_patch.py a partir de valores ja declarados em DB_ingredientes.json. Nao envolve verificacao de fonte externa."
}
```

`doc_ids: []` / `line_references: []` deliberately mirrors the existing convention for internally-derived entries (`REF_ESTIMATED_ZERO_BONE`, `REF_BONE_NA`) rather than inventing a new tracked document — no fabricated citation.

**11 of the 202** (the `REF_NA_*` entries on `measured`-status zero-value nutrients, e.g. `REF_NA_VITD_CONNECTIVE`) had no declared `reason` in the source data to cite, so their generated `note` field flags `REVISAO HUMANA RECOMENDADA`. They're still schema-valid and safe to merge, but worth a quick human glance — list in `mechanical_needs_human_review.json`.

**Verified round-trip:** merging this patch into a copy of `audit_provenance.json` and re-running the audit script drops unique orphans from 284 → 82 and occurrences from 453 → 251, with `unique_by_classification` showing `MECHANICAL: 0` remaining — the patch fully resolves its category, nothing left over, nothing double-counted.

**To apply:**
```bash
set -e
cp data/audit_provenance.json data/audit_provenance.json.backup || exit 1
python3 -c "
import json
with open('data/audit_provenance.json') as f: prov = json.load(f)
with open('data/mechanical_provenance_patch.json') as f: patch = json.load(f)
prov['references'].update(patch)
with open('data/audit_provenance.json', 'w') as f: json.dump(prov, f, indent=2, ensure_ascii=False)
"
python3 audit_orphans.py || { echo "APPLY FAILED validation — restoring backup"; cp data/audit_provenance.json.backup data/audit_provenance.json; exit 1; }
```
`set -e` plus the explicit backup-then-validate-then-restore-on-failure sequence means a failed apply can't leave the file in a half-written state.

---

## 5. EXTERNAL_VERIFICATION_REQUIRED category — 82 refs, 251 occurrences

These claim a specific external database or publication as their source. Registering them as `CONFIRMED` without checking is exactly the failure mode this whole remediation exists to prevent, so this plan does **not** auto-generate confirmed entries for them. Instead: `external_verification_checklist.json`, sorted by leverage (`occurrence_count` descending), with a `suggested_source_to_check` per prefix and `verification_status` pre-filled where this session actually checked.

### 5.1 Where the leverage is

```
REF_USDA_FDC_171047   35 occurrences
REF_USDA_FDC_171086   35 occurrences
REF_USDA_FDC_172382   35 occurrences
REF_USDA_FDC_175225   35 occurrences
REF_USDA_FDC_100088   34 occurrences
                     ----
                      174 occurrences from just 5 refs (69% of the remaining 251)
```
Each of these 5 numeric FDC-ID refs backs ~34 nutrient fields for a single ingredient (one USDA food record = one ingredient's whole nutrient panel). Verify these 5 first — they dwarf everything else in the category, including all 46 `REF_COFID` refs combined (46 occurrences total, 1 each).

### 5.2 What this session actually verified (real web lookups, not fabricated)

| Ref | Ingredient in DB | Finding |
|---|---|---|
| `REF_USDA_FDC_171086` | `turkey_neck_raw` | **Match.** FDC 171086 = "Chicken, turkey, neck, meat only, raw" per foodstruct.com, confirmed across multiple independent comparison pages. Food-identity checks out; nutrient values themselves weren't individually re-verified. |
| `REF_USDA_FDC_172382` | `chicken_back_raw` | **Mismatch — real bug.** FDC 172382 = "Chicken, broilers or fryers, neck, meat, and skin, raw" (chicken **neck**), confirmed across 3 independent foodstruct.com pages. The DB has this ID assigned to `chicken_back_raw`, not a neck ingredient. Either the FDC ID is wrong, or the copied nutrient values belong to the wrong ingredient. This needs a human decision, not a provenance entry — registering it as `CONFIRMED` would formalize an incorrect citation. |
| `REF_USDA_FDC_171047` | `chicken_neck_raw` | **Inconclusive.** One weak third-party signal suggests this may be "Chicken, meat and skin and giblets and neck, raw," not independently confirmed. Check together with 172382 above — the two ingredient assignments may need to be swapped. |
| `REF_USDA_FDC_175225`, `REF_USDA_FDC_100088` | `chicken_wing_raw`, `pork_rib_raw` | Not checked this session — same verification approach applies. |

General web search can't reliably resolve FDC IDs at scale (the FDC site is a JS search app, not per-ID crawlable pages, and the API needs a real key — `DEMO_KEY` is capped at 30 requests/hour). **Recommendation: get a free FDC API key** (signup at the api.data.gov page linked from `fdc.nal.usda.gov/api-guide`) and batch-verify all 30 `REF_USDA` refs — at 30 nutrients/ingredient in one record, 5-6 real API calls with a key would settle the whole top-leverage tier.

### 5.3 The other 77 refs

- **46 `REF_COFID`** — all on `beef_blood_raw` and a handful of other ingredients, occurrence_count 1 each (no dedup leverage, but low individual cost — CoFID is UK government open data). Includes the original blocker example (§2.3).
- **11 `REF_MILAGRES2020`, 4 `REF_LITERATURE`, 3 `REF_SCHWEIGERT1943`, 2 `REF_WHOLEFOODCATALOG`, 3 `REF_FRIDA*`, 1 `REF_MATVARETABELLEN`** — smaller literature/database citations. `REF_LITERATURE` is the vaguest (doesn't name a specific source in the ref itself) and should be prioritized for the team to identify the actual citation before anyone tries to "verify" it.

None of these were fabricated a "CONFIRMED" status in this pass. That would defeat the purpose.

---

## 6. Hardened task template for remaining work (9B-safe)

Only the 82 EXTERNAL refs are genuine open tasks now (the 202 MECHANICAL refs are resolved by the patch in §4).

**Why this is two steps, not one.** The original single-block template asked the executing model to hold ~10 simultaneous rules in one generation: branch on match/no-match, choose between two `quality_flag` enum values based on unstated precedent, get 4 required JSON keys right, decide `doc_ids` conditionally, write pt-BR text, and honor a standing "never fabricate" constraint throughout. Controlled measurement of instruction-following decay (Eliav 2026, arXiv:2607.19257; independently replicated at larger scale by Jaroslawicz et al. 2025 and Harada et al. 2025) shows perfect-compliance rate is already measurably degrading by 20-40 simultaneous instructions on every model tested — and the weakest models in that study (27B/35B) are still larger than the 9B executing this plan. Splitting the decision from the write cuts what any single generation has to hold correctly, at the cost of one extra round-trip.

```markdown
<task>
### Task ID: EXT-{ref}-DECIDE
- Input: external_verification_checklist.json entry for {ref}
- Ask: does suggested_source_to_check confirm the value(s) in nutrient_keys_affected for ingredients_affected, within a sane tolerance?
- Output (exactly one line): MATCH: <one-sentence citation> — or — NO_MATCH: <one-sentence reason>
- Max Tokens: 500 | Max Retries: 1 | Timeout: 60s
</task>

<task>
### Task ID: EXT-{ref}-WRITE
- Prerequisite: EXT-{ref}-DECIDE output
- Pre-task snapshot: `cp data/audit_provenance.json data/audit_provenance.json.backup || exit 1`
- Fill this exact template (do not add, remove, or rename keys):
  ```json
  {{
    "text": "<from DECIDE step, in pt-BR>",
    "doc_ids": [],
    "quality_flag": "<CONFIRMED if MATCH, else INFERRED>",
    "line_references": []
  }}
  ```
  If NO_MATCH, also append {ref} to `human_review_needed.json`.
- Validation: `python3 -c "import json; p=json.load(open('data/audit_provenance.json'))['references']; assert '{ref}' in p; e=p['{ref}']; assert {{'text','doc_ids','quality_flag','line_references'}} <= e.keys(); print('OK')"`
- Rollback: `cp data/audit_provenance.json.backup data/audit_provenance.json`
- Max Tokens: 1000 | Max Retries: 1 (escalate to human on failure, never retry-guess) | Timeout: 60s
</task>
```

Two simplifications beyond the split: (1) `AUTHORITATIVE_DATABASE` is dropped from the per-task decision — every MATCH now writes `CONFIRMED`; upgrading specific refs to `AUTHORITATIVE_DATABASE` by precedent (e.g. matching `REF_MC_MONICA_SEGAL`) is a pattern a script can apply in one deterministic pass afterward, not a judgment call worth adding to 82 individual agent decisions. (2) The write step is now fill-the-template rather than compose-the-schema — Ornith is choosing 2 values, not authoring 4 keys from a description of their constraints.

The one property that must survive the split: the "don't fabricate CONFIRMED" rule stays in the DECIDE step, not the WRITE step. WRITE never re-evaluates truth, it only transcribes DECIDE's answer — so there's no point in the pipeline where a token-budget-pressured model can shortcut straight to writing a plausible `CONFIRMED` without having gone through a step whose entire output is the match/no-match judgment.

---

## 7. Validation & rollback

**Corrected orphan check** (catches `anomaly_ref` too, unlike the original):
```bash
python3 audit_orphans.py
# summary.total_unique_refs_to_register must be 0 for validate_inputs() to pass
```

**Solver check** (unchanged from original, not re-verified here — `build_pipeline.py` wasn't provided):
```bash
timeout 300 python build_pipeline.py --runtime && echo "SOLVER OK" || echo "SOLVER FAILED"
```

**Rollback:**
```bash
cp data/audit_provenance.json.backup data/audit_provenance.json   # per-task
git checkout data/audit_provenance.json                            # full, if under version control
```

---

## 8. Deliverables from this pass

| File | What it is |
|---|---|
| `audit_orphans.py` | Deterministic audit script — regenerates the manifest from current file state, includes the `anomaly_ref` fix |
| `orphan_refs_manifest.json` | All 284 unique orphan refs, classified, with affected ingredients/nutrients/values |
| `generate_mechanical_patch.py` | Generates the 202-entry MECHANICAL patch from the manifest |
| `mechanical_provenance_patch.json` | The 202 ready-to-merge, schema-valid entries (§4) |
| `mechanical_needs_human_review.json` | 11 of those 202 flagged for a quick reason-check |
| `build_external_checklist.py` | Generates the prioritized EXTERNAL checklist |
| `external_verification_checklist.json` | All 82 EXTERNAL refs, sorted by leverage, with real findings pre-filled where checked |
| `audit_provenance_references.schema.json` | The real, reverse-engineered contract for `references` entries (§3) |

## 9. Recommended next steps

1. Apply the MECHANICAL patch (§4) — closes 202 of 284 unique refs / 202 of 453 occurrences immediately, no further verification needed.
2. Resolve the `172382` / `171047` chicken neck/back mix-up (§5.2) as a data-correctness fix, separately from provenance registration — don't paper over a wrong ingredient assignment with a provenance record.
3. Get a real USDA FDC API key and batch-verify the remaining 4 numeric-ID refs (`171047`, `175225`, `100088`, plus re-confirming `172382`/`171086` at the nutrient-value level, not just food-identity) — highest remaining leverage for lowest effort.
4. Work through the 46 `REF_COFID` refs against CoFID (UK open data, no key needed) — no dedup leverage but straightforward.
5. Identify the actual source behind the 4 unnamed `REF_LITERATURE` refs before attempting to verify them.
6. Re-run `audit_orphans.py` after each batch; `total_unique_refs_to_register: 0` is the exit condition for `nutrition.validate_inputs()`.

---

## 10. Review of proposed "9B hardening" additions (2026-07-22)

A batch of 10 generic hardening requirements was proposed against this plan (framed as gaps for a "9B Ornith" execution target). Evaluated against v3.0.0's actual task structure — not the discarded v2.0.0 template the batch appears to assume — 2 were real and applied; 8 were rejected as misapplied, redundant, or actively contradicting a deliberate design choice made earlier in this document.

**Applied:**

| Requirement | Change |
|---|---|
| Fail-Fast Enforcement | §4 apply script now has `set -e`, an `\|\| exit 1` on the backup step, and a post-write `audit_orphans.py` check that restores the backup on failure instead of leaving a half-applied patch. §6 step 1 backup now fails fast too. |
| — | §2.4's cross-reference to "the corrected script in §6" was wrong — §6 has no script, only the EXT task template. Corrected to point at `audit_orphans.py` (§8), and noted that it also covers `safety_alerts[].source_ref`, which §2.2's audit scope includes but no proposed replacement script did. |

**Rejected:**

| Requirement | Why |
|---|---|
| Static Lookup Tables for INFERRED refs | Circular — `usda_nutrient_ranges.json` "pre-approved ranges" would themselves need external sourcing, which is the exact problem this plan's EXTERNAL category exists to handle case-by-case. Doesn't apply to MECHANICAL (values already declared internally, §4) or EXTERNAL (needs a real FDC/CoFID lookup per ref, not a static range, §5). |
| Token Overflow Protection | Misdiagnosed for this plan. §6 tasks take one `external_verification_checklist.json` entry as input, not the full `DB_ingredientes.json`. No task here reads the whole DB file. |
| Dependency Hardening (jq prerequisite checks) | Contradicts §6's explicit "Prerequisites: None (each EXTERNAL ref is independent)". A prerequisite-validation step for tasks that have no prerequisites is dead code. |
| Full Directory Snapshots | Wrong blast radius. Every task here writes only `audit_provenance.json`; `DB_ingredientes.json` is never touched. A `tar -czf` of all of `data/` before each of 82 independent tasks is unneeded I/O with no safety gain over the existing targeted `.backup` copy. |
| 9B Execution Headers / Bookending | Not evaluated against this plan's actual constraint: `Max Tokens: 3000` per task (§6). Repeating the task spec 3x eats into that budget on single, independent lookup tasks with no long-context loss to guard against. |
| Schema-Consistent Patch Commands | The proposed `jq` snippet is invalid — `.references."REF_*"` is a literal key lookup in jq, not a wildcard; it would never match. Also redundant: §6 step 4 already validates the same schema keys correctly, in Python, against a real ref. |
| Corrected Orphan Preflight Script | Redundant and a regression. `audit_orphans.py` (§8) already fixes the `anomaly_ref` blind spot *and* checks `safety_alerts[].source_ref` (§2.2). The proposed replacement checks only `nutrients.*.{source_ref,anomaly_ref}` and would silently drop `safety_alerts` coverage that already exists. |
| Circuit Breakers (`max_retries: 3`) | Directly contradicts §6's deliberate `Max Retries: 1` — retrying a failed external-source lookup invites converging on a plausible-but-unverified match to close the task, which is the exact hallucinated-`CONFIRMED` failure mode this whole plan (§3, §6) exists to prevent. 3 retries reopens that risk for no stated benefit. |
