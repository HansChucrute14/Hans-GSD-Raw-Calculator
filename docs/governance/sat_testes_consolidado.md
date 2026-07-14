# sat_testes_consolidado — Regra de Ouro para Testes (Metodologia AAA+A)

**v10.4** · ← `../architecture/indice_plano_central.md` (canônico) · `../../README.md`

**Responsibility:** Cross-cutting test methodology (§11.5): Arrange-Act-Assert-Audit pattern. Specific tests (cascade, data, recipes) live as §A in their thematic satellites.

**Depends on:** sat_princípios:§3.1 · **Referenced by:** Any test session

**Load when:** writing new test · reviewing QA methodology

> **Context:** Contains only §11.5. §11.1 is in `../architecture/indice_plano_central.md`. §11.2 (Cascade Tests) is in `../architecture/sat_solver_contrato.md:§A`. §11.3 (Data Tests) is in `../architecture/sat_dados_schema.md:§A`. §11.4 (Recipes Tests) is in `../architecture/sat_pipeline_fluxo.md:§A`.

---

## 11. Mandatory Integrity Tests (Anti-Gamification) — V10 (partial — §11.5 only)

> **Scope note:** indice_plano_central:§11.1 is in the index. sat_solver_contrato:§11.2-§11.4 are §A in their thematic satellites. This file is only the cross-cutting methodology.

### 11.5 Golden Rule for Testing the Coding AI Agent

**Every test must follow the AAA + A pattern (Arrange-Act-Assert + Audit):**

1. **Arrange:** Load real JSONs, mount real data.
2. **Act:** Execute the real function (no stub).
3. **Assert:** Verify the result with assertions that distinguish real result from placeholder.
4. **Audit:** Log the complete result (not just pass/fail) for human inspection — the AI cannot self-certify.

AAA+A integration tests use real JSONs. They do not replace deterministic unit/property tests with minimal controlled fixtures: those tests are required for unit conversion, dimensional consistency, tolerance boundaries, and infeasibility classification. A fixture may never be the sole evidence that the production cascade works.

```python
# Mandatory audit example in every test
def audit_test_result(test_name, result, expected):
    with open("test_audit_log.md", "a") as f:
        f.write(f"## {test_name}\n")
        f.write(f"- **Expected:** {expected}\n")
        # allocations may be None (Level 3) — handle safely
        allocs = result.get('allocations')
        allocs_desc = "null (Level 3 — mechanical barrier)" if allocs is None else f"{len(allocs)} items"
        f.write(f"- **Got:** solver_status={result.get('solver_status')}, "
                f"level={result.get('cascade_level_used')}, "
                f"gaps={len(result.get('gaps', []))}, "
                f"allocations={allocs_desc}\n")
        f.write(f"- **Passed:** {result.get('solver_status') == expected}\n\n")
```

---

## ✅ Definition of Done — sat_testes_consolidado

Test methodology is being followed when:

- [ ] Every new test follows AAA+A pattern (Arrange-Act-Assert-Audit).
- [ ] `Arrange` loads real JSONs (no fixtures/mocks).
- [ ] `Act` executes real function (no stub).
- [ ] `Assert` verifies result that distinguishes real implementation from placeholder (not just `assert result is not None`).
- [ ] `Audit` writes log to `test_audit_log.md` with expected/received/passed.
- [ ] Test never asserts "field exists" without also validating "field has correct value".
- [ ] Cascade test validates REAL descent between levels (not just `solver_status` in output).
- [ ] Test output is pasted (evidence), not claimed.
- [ ] Unit/property tests cover dimensional consistency, DER scaling, and conversion round-trips; real-JSON integration tests cover the production pipeline.
- [ ] Every infeasibility test distinguishes `unsafe_diagnostic`, `structurally_infeasible`, and `data_incomplete`.

**Rejected anti-pattern:** `assert "allocations" in result` without verifying `result["allocations"] is None` in Level 3.

---
