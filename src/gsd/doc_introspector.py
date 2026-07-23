"""doc_introspector — Live implementation introspection for build_pipeline.py."""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union


# ── §D: IMPLEMENTATION_SPEC ──────────────────────────────────────────────────
# Each entry declares what the architecture docs say should exist.
# The ImplIntrospector checks the real build_pipeline.py against this spec.
# Strategies:
#   toplevel_func   → AST top-level FunctionDef matching spec.target
#   class_exists    → AST top-level ClassDef matching spec.target
#   missing         → searches entire module AST; returns MISSING if not found
#   cli_stub        → CLI mode in main() whose body prints "not implemented"
#   cli_stub_absent → CLI mode in main() whose body is REAL (not a stub)
#   file_exists     → checks if spec.target file exists on disk


@dataclass
class ImplCheck:
    name: str
    strategy: str  # toplevel_func | class_exists | missing | cli_stub | cli_stub_absent | file_exists
    target: str
    priority: str  # P0 | P1 | P2
    spec_ref: str  # e.g. "sat_solver_contrato:§8"
    parent: Optional[str] = None  # kept for backward compat; unused by missing strategy


IMPLEMENTATION_SPEC: list[ImplCheck] = [
    ImplCheck(
        name="call_lp_solver",
        strategy="toplevel_func",
        target="call_lp_solver",
        priority="P0",
        spec_ref="sat_solver_contrato:§8",
    ),
    ImplCheck(
        name="DerEnvelope",
        strategy="class_exists",
        target="DerEnvelope",
        priority="P0",
        spec_ref="sat_princípios:§3.3",
    ),
    ImplCheck(
        name="build_diagnostic_analysis",
        strategy="toplevel_func",
        target="build_diagnostic_analysis",
        priority="P0",
        spec_ref="sat_solver_contrato:§7.2",
    ),
    ImplCheck(
        name="build_lp_problem",
        strategy="toplevel_func",
        target="build_lp_problem",
        priority="P0",
        spec_ref="sat_solver_contrato:§8.1",
    ),
    ImplCheck(
        name="--runtime mode",
        strategy="cli_stub_absent",
        target="--runtime",
        priority="P0",
        spec_ref="sat_pipeline_codigo:§6.4",
    ),
    ImplCheck(
        name="--build-recipes mode",
        strategy="cli_stub",
        target="--build-recipes",
        priority="P1",
        spec_ref="sat_pipeline_fluxo:§6.3",
    ),
    ImplCheck(
        name="recipes_precomputed.json",
        strategy="file_exists",
        target="recipes_precomputed.json",
        priority="P1",
        spec_ref="sat_pipeline_fluxo:§5.2",
    ),
    ImplCheck(
        name="format_allocations",
        strategy="missing",
        target="format_allocations",
        priority="P2",
        spec_ref="sat_pipeline_codigo:§6.4a",
    ),
    ImplCheck(
        name="expand_category_wildcards",
        strategy="missing",
        target="expand_category_wildcards",
        priority="P2",
        spec_ref="sat_pipeline_codigo:§6.4a",
    ),
    ImplCheck(
name="run_pipeline",
        strategy="missing",
        target="run_pipeline",
        priority="P2",
        spec_ref="sat_pipeline_codigo:§6.4",
    ),
]


# ── ImplIntrospector ─────────────────────────────────────────────────────────


class ImplIntrospector:
    """Parses build_pipeline.py AST and checks IMPLEMENTATION_SPEC against it.

    D7 (v1.2): Dispatch style detected — simple if/elif chain in main():
        mode = sys.argv[1]
        if mode == "--X": ... elif mode == "--Y": ...
    """

    def __init__(self, source_path: Union[Path, list[Path]]) -> None:
        paths = [source_path] if isinstance(source_path, Path) else list(source_path)
        self.units = []  # list of (path, source_text, tree)
        for p in paths:
            text = p.read_text(encoding="utf-8")
            self.units.append((p, text, ast.parse(text)))
        self.source_path = paths[0]
        self.source_text = self.units[0][1]
        self.tree = self.units[0][2]
        self.toplevel_funcs: dict[str, ast.FunctionDef] = {}
        self.toplevel_classes: dict[str, ast.ClassDef] = {}
        self._func_origin: dict[str, tuple] = {}   # name -> (path, source_text)
        self._class_origin: dict[str, tuple] = {}
        self._walk_toplevel()
        self._cli_modes: dict[str, bool] | None = None
        self._main_stmts: list[ast.stmt] | None = None
        self._main_source_text: str | None = None

    def _walk_toplevel(self) -> None:
        for path, text, tree in self.units:
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    self.toplevel_funcs[node.name] = node
                    self._func_origin[node.name] = (path, text)
                    if node.name == "main":
                        self._main_source_text = text
                elif isinstance(node, ast.ClassDef):
                    self.toplevel_classes[node.name] = node
                    self._class_origin[node.name] = (path, text)

    def extract_cli_modes(self) -> dict[str, bool]:
        """Return {mode_str: is_stub} for each mode detected in main()."""
        if self._cli_modes is not None:
            return dict(self._cli_modes)

        result: dict[str, bool] = {}
        main_node = self.toplevel_funcs.get("main")
        if main_node is None:
            self._cli_modes = result
            return result

        stmts = main_node.body
        self._main_stmts = list(stmts)
        for node in ast.walk(main_node):
            if isinstance(node, ast.If):
                self._extract_mode_from_if(node, result)
            elif isinstance(node, (ast.Match,)):
                pass  # not used — detected as if/elif per D7

        self._cli_modes = result
        return result

    def _extract_mode_from_if(self, if_node: ast.If, result: dict[str, bool]) -> None:
        """Walk if/elif branches looking for 'mode == \"--X\"' patterns."""
        current: ast.If | None = if_node
        while current is not None:
            test_str = ast.dump(current.test)
            m = re.search(r"'--([a-z-]+)'", test_str)
            if m:
                mode_str = "--" + m.group(1)
                is_stub = self._branch_is_stub(current.body)
                result[mode_str] = is_stub
            current = next(
                (n for n in getattr(current, "orelse", []) if isinstance(n, ast.If)),
                None,
            )

    def _branch_is_stub(self, body: list[ast.stmt]) -> bool:
        """Return True if the branch prints 'not implemented' (case-insensitive)."""
        src = self._main_source_text if self._main_source_text is not None else self.source_text
        body_text = ast.get_source_segment(src, body[0]) if body else ""
        return bool(body_text and "not implemented" in body_text.lower())

    def is_stub(self, mode: str) -> bool | None:
        """Return True if mode is a stub, False if real, None if not found."""
        modes = self.extract_cli_modes()
        return modes.get(mode)

    def _search_all_funcs(self, name: str) -> tuple[bool, int | None]:
        """Search every unit's AST for any FunctionDef named `name`."""
        for _path, _text, tree in self.units:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == name:
                    return True, node.lineno
        return False, None

    def check(self, spec: ImplCheck, base_dir: Path, cli_stub_strings: dict | None = None) -> dict:
        """Dispatch by strategy, return {name, priority, spec_ref, status, line, note}."""
        status = "UNKNOWN"
        line: int | None = None
        note = ""

        if spec.strategy == "toplevel_func":
            func = self.toplevel_funcs.get(spec.target)
            if func is not None:
                status = "IMPLEMENTED"
                line = func.lineno
                fname = self._func_origin[spec.target][0].name
                note = f"toplevel function at {fname}:L{line}"
            else:
                status = "NOT_FOUND"
                note = "not found in module top-level"

        elif spec.strategy == "class_exists":
            cls = self.toplevel_classes.get(spec.target)
            if cls is not None:
                status = "IMPLEMENTED"
                line = cls.lineno
                fname = self._class_origin[spec.target][0].name
                note = f"toplevel class at {fname}:L{line}"
            else:
                status = "NOT_FOUND"
                note = "not found in module top-level"

        elif spec.strategy == "missing":
            found, fline = self._search_all_funcs(spec.target)
            if found:
                status = "FOUND"  # unexpected — spec said it should be missing
                line = fline
                note = "found in module AST (contradicts expectation of MISSING)"
            else:
                status = "MISSING"
                note = "not found in module AST"

        elif spec.strategy == "cli_stub":
            is_stub = self.is_stub(spec.target)
            if is_stub is True:
                status = "IMPLEMENTED"
                note = "CLI mode is a stub (as expected)"
            elif is_stub is False:
                status = "DRIFT"
                note = "CLI mode exists but is NOT a stub — SPEC_DRIFT"
            else:
                status = "NOT_FOUND"
                note = "CLI mode not found in main()"

        elif spec.strategy == "cli_stub_absent":
            is_stub = self.is_stub(spec.target)
            if is_stub is True:
                status = "DRIFT"
                note = "CLI mode exists as stub — expected fully implemented"
            elif is_stub is False:
                status = "IMPLEMENTED"
                note = "CLI mode exists and is fully implemented"
            else:
                status = "NOT_FOUND"
                note = "CLI mode not found in main()"

        elif spec.strategy == "file_exists":
            target_path = base_dir / spec.target
            if target_path.exists():
                status = "IMPLEMENTED"
                note = f"file exists ({target_path.stat().st_size:,} bytes)"
            else:
                status = "NOT IMPLEMENTED"
                note = "file does not exist"

        return {
            "name": spec.name,
            "priority": spec.priority,
            "spec_ref": spec.spec_ref,
            "status": status,
            "line": line,
            "note": note,
        }

    def detect_spec_drift(self, spec: list[ImplCheck]) -> list[str]:
        """Inverse check: CLI modes in main() NOT present in IMPLEMENTATION_SPEC."""
        modes = self.extract_cli_modes()
        spec_modes = {s.target for s in spec if s.strategy in ("cli_stub", "cli_stub_absent")}
        drift: list[str] = []
        for mode, is_stub in modes.items():
            if mode not in spec_modes:
                tag = "stub" if is_stub else "real"
                drift.append(f"CLI mode '{mode}' ({tag}) in main() but not in IMPLEMENTATION_SPEC")
        # Also detect cli_stub entries whose status flipped
        for s in spec:
            if s.strategy == "cli_stub":
                actual = self.is_stub(s.target)
                if actual is False:
                    drift.append(f"SPEC_DRIFT: '{s.target}' expected stub but is now real")
            elif s.strategy == "cli_stub_absent":
                actual = self.is_stub(s.target)
                if actual is True:
                    drift.append(f"SPEC_DRIFT: '{s.target}' expected real but is now stub")
        return drift


# ── §D: scrub_volatile (Task 4-2) ────────────────────────────────────────────
# D4 v1.2: LP solver is already pinned (randomSeed=12345, threads=1 in
# build_pipeline.py:2271-2276), so solver output is bit-identical across runs
# on the same machine. The actual non-determinism sources in captured stdout
# are: (1) timestamps, (2) absolute Windows/Linux paths, (3) PIDs and memory
# addresses in error tracebacks. Idempotent: applying twice = applying once.

_WIN_PATH = re.compile(r"[A-Z]:\\[^\s\n]+")
_LINUX_PATH = re.compile(r"/home/[^\s\n]+")
_ISO_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?")
_PID = re.compile(r"PID:\s*\d+")
_MEM_ADDR = re.compile(r"0x[0-9a-fA-F]+")
# Set representation: {'item1', 'item2'} with single-quoted strings
_SET_REPR = re.compile(r"\{('[^']*'(?:,\s*'[^']*')*)\}")


def _normalize_set_repr(match: re.Match) -> str:
    """Sort items in a set repr for deterministic output."""
    inner = match.group(1)
    items = [item.strip().strip("'") for item in inner.split(",")]
    items.sort()
    return "{" + ", ".join(f"'{item}'" for item in items) + "}"


def scrub_volatile(content: str) -> str:
    """Strip non-deterministic content from captured stdout before MAPA embedding.

    Order matters: paths first (they may contain timestamp-like substrings),
    then timestamps, then PIDs/memory addresses. Idempotent — applying twice
    produces the same output as applying once.
    """
    content = _WIN_PATH.sub("<repo>/", content)
    content = _LINUX_PATH.sub("<repo>/", content)
    content = _ISO_TIMESTAMP.sub("<timestamp>", content)
    content = _PID.sub("PID: <pid>", content)
    content = _MEM_ADDR.sub("0x<addr>", content)
    # Normalize set representations: {'b', 'a'} → {'a', 'b'}
    content = _SET_REPR.sub(_normalize_set_repr, content)
    return content


# ── §D: capture_live_evidence (Task 4-1) ─────────────────────────────────────
# D9 v1.2: 4 smoke runs (was 3). Runtime-smoke entry populates 6 LP-specific
# fields: solver_status, cascade_level_used, lexicographic_stages_solved,
# clinical_floor_relaxed, solve_time_ms, nutrients_above_90pct_sul.
# Note on nutrients_above_90pct_sul threshold: contract uses percentage scale
# (pct_of_sul=100 means "at SUL", pct_of_sul=299 means "2.99x SUL"). The plan
# spec says `> 0.9` but that's the fraction scale; with the percentage scale
# in the actual contract, the equivalent is `> 90` to mean "above 90% of SUL".
# Using `> 90` to keep the audit signal precise — `> 0.9` would flag every
# nutrient with a SUL (since even 1% of SUL > 0.9), defeating the diagnostic.

import contextlib
import io
import json as _json
import sys as _sys


def _trunc_repr(obj: Any, limit: int = 2000) -> str:
    """Render object as indented JSON, truncating to `limit` chars with a tail note."""
    s = _json.dumps(obj, indent=2, default=str, sort_keys=True)
    if len(s) <= limit:
        return s
    return s[:limit] + f"... (truncated, {len(s) - limit} more chars)"


def _empty_lp_fields() -> dict:
    """LP-specific fields set to None for non-LP smoke entries."""
    return {
        "solver_status": None,
        "cascade_level_used": None,
        "lexicographic_stages_solved": None,
        "clinical_floor_relaxed": None,
        "solve_time_ms": None,
        "nutrients_above_90pct_sul": None,
    }


def _extract_lp_fields(result: dict) -> dict:
    """D9 v1.2: Extract 6 LP-specific signals from a solver_output dict."""
    meta = result.get("solver_metadata") or {}
    diag = result.get("diagnostic_analysis") or {}
    wwh = diag.get("what_would_happen") or {}

    # clinical_floor_relaxed: prefer what_would_happen (Level 3), fallback to
    # solver_metadata.clinical_floor_applied inverse (applied=True → relaxed=False)
    if "clinical_floor_relaxed" in wwh:
        clinical_floor_relaxed = bool(wwh["clinical_floor_relaxed"])
    elif "clinical_floor_applied" in meta:
        clinical_floor_relaxed = not bool(meta["clinical_floor_applied"])
    else:
        clinical_floor_relaxed = None

    lexicographic = meta.get("lexicographic_stages_used") or {}
    stages = lexicographic.get("stages") if isinstance(lexicographic, dict) else None

    # pct_of_sul is percentage scale (100 = at SUL per sat_solver_contrato:§7)
    nutrients_above_90pct_sul = [
        nr["nutrient_id"]
        for nr in result.get("nutrient_results", [])
        if nr.get("pct_of_sul") is not None and nr["pct_of_sul"] > 90
    ]

    return {
        "solver_status": result.get("solver_status"),
        "cascade_level_used": result.get("cascade_level_used"),
        "lexicographic_stages_solved": stages,
        "clinical_floor_relaxed": clinical_floor_relaxed,
        "solve_time_ms": 0,  # constant for idempotency (actual varies per run)
        "nutrients_above_90pct_sul": nutrients_above_90pct_sul,
    }


def capture_live_evidence(
    data: dict,
    reference_animal: dict,
    reference_selection: list,
) -> list:
    """Run 4 smoke tests against the production pipeline, return evidence list.

    D9 v1.2: 4 entries (was 3) — added solver_status_diagnostic.
    Each entry has: label, status (OK/FAILED/DEGRADED), severity (HARD/SOFT),
    output (scrubbed stdout), result_repr (JSON, truncated to 2000 chars),
    error (if FAILED), and 6 LP-specific fields (populated only for runtime-smoke).
    Pinned to DB_ingredientes.json — no USDA API calls during evidence capture.
    """
    # Import from gsd package (replaces build_pipeline import)
    from gsd import core as bp_core
    from gsd import nutrition as bp_nutrition
    from gsd import solver as bp_solver

    evidence: list = []
    # Reuse loaded data across smoke runs to avoid double-loading 11 JSONs
    if not data:
        data = bp_core.load_all_jsons()

    growth = data.get("growth_energy_skeletal.json", {})
    db = data.get("DB_ingredientes.json", {})
    fr = data.get("formulation_rules.json", {})
    fr["_db_ref"] = db
    scenario_id = "SCN_B_SLOW_GROWTH"

    animal = bp_core.AnimalInput(
        sex=reference_animal["sex"],
        weight_kg=reference_animal["weight_kg"],
        age_months=reference_animal["age_months"],
        gonadal_status=reference_animal["gonadal_status"],
        use_gompertz=reference_animal.get("use_gompertz", True),
    )

    # ── Smoke 1: calculate_der_and_envelope (HARD) ─────────────────────
    label = "calculate_der_and_envelope"
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            der_env = bp_nutrition.calculate_der_and_envelope(
                animal, growth, scenario_id, reference_selection, db,
            )
        result_obj = {
            "bw_kg": der_env.bw_kg,
            "ter_kcal": der_env.ter_kcal,
            "k_multiplier": der_env.k_multiplier,
            "der_kcal": der_env.der_kcal,
            "units_of_1000kcal": der_env.units_of_1000kcal,
            "min_total_g": der_env.min_total_g,
            "max_total_g": der_env.max_total_g,
            "strategy": der_env.strategy,
            "density_source": der_env.density_source,
        }
        evidence.append({
            "label": label,
            "status": "OK",
            "severity": "HARD",
            "output": buf.getvalue(),
            "result_repr": _trunc_repr(result_obj),
            "error": None,
            **_empty_lp_fields(),
        })
    except Exception as e:
        evidence.append({
            "label": label,
            "status": "FAILED",
            "severity": "HARD",
            "output": buf.getvalue(),
            "result_repr": None,
            "error": f"{type(e).__name__}: {e}",
            **_empty_lp_fields(),
        })

    # ── Smoke 2: --runtime smoke (solve_cascade end-to-end) (HARD) ────
    label = "--runtime smoke (solve_cascade)"
    buf = io.StringIO()
    runtime_result = None
    try:
        bp_nutrition.validate_inputs(data)
        with contextlib.redirect_stdout(buf):
            der_env = bp_nutrition.calculate_der_and_envelope(
                animal, growth, scenario_id, reference_selection, db,
            )
            matrix = bp_nutrition.build_matrix(reference_selection, db, fr)
            runtime_result = bp_solver.solve_cascade(
                reference_selection, data, der_env, scenario_id, animal,
            )
            bp_solver.validate_output(runtime_result, data, der_env)
        evidence.append({
            "label": label,
            "status": "OK",
            "severity": "HARD",
            "output": buf.getvalue(),
            "result_repr": _trunc_repr(runtime_result),
            "error": None,
            **_extract_lp_fields(runtime_result),
        })
    except Exception as e:
        # Capture whatever LP fields we can from a partial result
        lp_fields = _empty_lp_fields()
        if runtime_result is not None:
            lp_fields = _extract_lp_fields(runtime_result)
        evidence.append({
            "label": label,
            "status": "FAILED",
            "severity": "HARD",
            "output": buf.getvalue(),
            "result_repr": _trunc_repr(runtime_result) if runtime_result else None,
            "error": f"{type(e).__name__}: {e}",
            **lp_fields,
        })

    # ── Smoke 3: check_fat_source_adequacy (no fat_source) (SOFT) ──────
    label = "check_fat_source_adequacy (no fat_source)"
    buf = io.StringIO()
    try:
        # Rebuild matrix fresh (independent of smoke 2's run)
        der_env3 = bp_nutrition.calculate_der_and_envelope(
            animal, growth, scenario_id, reference_selection, db,
        )
        matrix3 = bp_nutrition.build_matrix(reference_selection, db, fr)
        with contextlib.redirect_stdout(buf):
            fat_gap = bp_solver.check_fat_source_adequacy(
                matrix3, reference_selection, fr, der_env3, db,
            )
        # fat_gap is None when no gap detected — that's OK; non-None is DEGRADED
        status = "DEGRADED" if fat_gap is not None else "OK"
        evidence.append({
            "label": label,
            "status": status,
            "severity": "SOFT",
            "output": buf.getvalue(),
            "result_repr": _trunc_repr({"fat_gap": fat_gap}),
            "error": None,
            **_empty_lp_fields(),
        })
    except Exception as e:
        evidence.append({
            "label": label,
            "status": "FAILED",
            "severity": "SOFT",
            "output": buf.getvalue(),
            "result_repr": None,
            "error": f"{type(e).__name__}: {e}",
            **_empty_lp_fields(),
        })

    # ── Smoke 4 (D9 NEW): solver_status_diagnostic (SOFT) ─────────────
    label = "solver_status_diagnostic"
    buf = io.StringIO()
    try:
        # If smoke 2 succeeded we already have runtime_result; otherwise re-run
        # the cascade here so we always have a result to diagnose.
        if runtime_result is None:
            with contextlib.redirect_stdout(buf):
                der_env4 = bp_nutrition.calculate_der_and_envelope(
                    animal, growth, scenario_id, reference_selection, db,
                )
                runtime_result = bp_solver.solve_cascade(
                    reference_selection, data, der_env4, scenario_id, animal,
                )
        solver_status = runtime_result.get("solver_status")
        # D9: capture a diagnostic entry whenever runtime returned suboptimal
        # or unsafe_diagnostic (in this codebase, "infeasible" maps to
        # unsafe_diagnostic — no separate "infeasible" status is emitted)
        if solver_status in ("suboptimal", "unsafe_diagnostic", "infeasible"):
            gaps = runtime_result.get("gaps", []) or []
            alerts = runtime_result.get("alerts", []) or []
            diag_info = {
                "solver_status": solver_status,
                "cascade_level_used": runtime_result.get("cascade_level_used"),
                "gaps_count": len(gaps),
                "alerts_count": len(alerts),
                "first_5_gap_nutrients": [g.get("nutrient_id") for g in gaps[:5]],
                "first_5_alert_severities": [a.get("severity") for a in alerts[:5]],
                "lexicographic_stages_used": (
                    (runtime_result.get("solver_metadata") or {})
                    .get("lexicographic_stages_used")
                ),
            }
            status = "DEGRADED"  # not a failure — diagnostic context
        else:
            diag_info = {
                "solver_status": solver_status,
                "note": "no fallback — optimal",
            }
            status = "OK"
        evidence.append({
            "label": label,
            "status": status,
            "severity": "SOFT",
            "output": buf.getvalue(),
            "result_repr": _trunc_repr(diag_info),
            "error": None,
            **_empty_lp_fields(),  # LP fields already captured in smoke 2
        })
    except Exception as e:
        evidence.append({
            "label": label,
            "status": "FAILED",
            "severity": "SOFT",
            "output": buf.getvalue(),
            "result_repr": None,
            "error": f"{type(e).__name__}: {e}",
            **_empty_lp_fields(),
        })

    return evidence


# ── §D: STRUCTURE_CONTRACTS (Phase 2) ───────────────────────────────────────
# Defines live JSON structure contracts that must hold against real data files.
# D8 v1.2 NEW: 9th contract — NUTRIENT_REGISTRY exactly 8 safety_hard entries with sul_value.
# Each contract: file, expected_type, predicate (callable returning bool), description, default.

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class StructureContract:
    file: str
    expected_type: type
    predicate: Callable[[Any], bool]
    description: str
    default: Any = None
    covers: set = field(default_factory=set)  # fields this predicate inspects (Patch 2-P1)


# Helper for NUTRIENT_REGISTRY safety_hard=8 contract
def _count_safety_hard_with_sul(nutrient_registry: dict) -> int:
    """Count safety_hard entries that have sul_value."""
    count = 0
    for v in nutrient_registry.values():
        if isinstance(v, dict) and v.get("constraint_tier") == "safety_hard":
            if "sul_value" in v:
                count += 1
    return count


STRUCTURE_CONTRACTS = [
    StructureContract(
        file="scenarios.json",
        expected_type=list,
        predicate=lambda d: len(d) > 0,
        description="scenarios.json is a non-empty list (Finding #16)",
        default=[],
        covers={"name", "scenario_id", "source_ref", "status", "targets"},
    ),
    StructureContract(
        file="constraints.json",
        expected_type=dict,
        predicate=lambda d: set(d.keys()) == {"mineral_antagonisms", "toxicological_limits", "inclusion_constraints", "nutrient_bounds"},
        description="constraints.json is a dict with exactly 4 keys (Finding #15)",
        default={},
        covers={"mineral_antagonisms", "toxicological_limits", "inclusion_constraints", "nutrient_bounds"},
    ),
    StructureContract(
        file="audit_provenance.json",
        expected_type=dict,
        predicate=lambda d: "references" in d and all(isinstance(v, dict) and "quality_flag" in v for v in d.get("references", {}).values()),
        description="audit_provenance.json refs use quality_flag not status (Finding #14)",
        default={},
        covers={"references", "quality_flag", "algorithm_logic", "data_quality_flags", "source_documents"},
    ),
    StructureContract(
        file="lp_parameters_data.json",
        expected_type=dict,
        predicate=lambda d: "NUTRIENT_REGISTRY" in d and "has_sul" not in next(iter(d.get("NUTRIENT_REGISTRY", {}).values()), {}),
        description="lp_parameters_data.json NUTRIENT_REGISTRY has no has_sul field (Finding #13)",
        default={},
        covers={"NUTRIENT_REGISTRY", "has_sul", "$schema", "description", "mineral_antagonisms", "schema_version", "solve_cascade", "solver_params"},
    ),
    StructureContract(
        file="toxicological_limits.json",
        expected_type=list,
        predicate=lambda d: len(d) == 8,
        description="toxicological_limits.json is a list of 8 entries (Finding #8 cross-check)",
        default=[],
        covers={"constraint_type", "note", "nutrient_id", "pathophysiology_ref", "regulatory_gap", "solver_variable", "source_ref", "sul"},
    ),
    StructureContract(
        file="objective_weights.json",
        expected_type=list,
        predicate=lambda d: len(d) == 29,
        description="objective_weights.json is a list of 29 entries",
        default=[],
        covers={"description", "direction", "note", "priority_tier", "solver_penalty_multiplier", "source_ref", "variable", "variable_note", "weight", "weight_id"},
    ),
    StructureContract(
        file="formulation_rules.json",
        expected_type=dict,
        predicate=lambda d: "nutrient_matrix" in d and isinstance(d["nutrient_matrix"], list) and len(d["nutrient_matrix"]) == 41,
        description="formulation_rules.json nutrient_matrix is a list of 41 entries (Findings #6/#7)",
        default={},
        covers={"nutrient_matrix", "_inclusion_semantics", "bioavailability_factors", "diet_templates", "digestibility", "inclusion_limits", "processing_loss_factors", "supplement_dosages"},
    ),
    StructureContract(
        file="DB_ingredientes.json",
        expected_type=dict,
        predicate=lambda d: "protein_sources" in d and isinstance(d["protein_sources"], dict),
        description="DB_ingredientes.json protein_sources is a dict",
        default={},
        covers={"protein_sources", "_db_metadata"},
    ),
    # D8 v1.2 NEW: NUTRIENT_REGISTRY exactly 8 safety_hard entries, each with sul_value
    StructureContract(
        file="lp_parameters_data.json",
        expected_type=dict,
        predicate=lambda d: _count_safety_hard_with_sul(d.get("NUTRIENT_REGISTRY", {})) == 8,
        description="NUTRIENT_REGISTRY has exactly 8 safety_hard entries, each with sul_value",
        default={},
        covers={"NUTRIENT_REGISTRY", "constraint_tier", "sul_value", "basis", "clinical_criticality", "critical_flags", "display_name", "unit"},
    ),
]


def check_structure_contracts(data: dict) -> list[dict]:
    """Evaluate all STRUCTURE_CONTRACTS against loaded data.

    Returns list of dicts: {file, description, holds: bool, actual_type, expected_type, note}
    """
    results = []
    for contract in STRUCTURE_CONTRACTS:
        value = data.get(contract.file, contract.default)
        holds = False
        actual_type = type(value).__name__
        expected_type = contract.expected_type.__name__
        note = ""

        if value is None:
            note = "file not found or failed to load"
        elif not isinstance(value, contract.expected_type):
            note = f"type mismatch: got {actual_type}, expected {expected_type}"
        else:
            try:
                holds = bool(contract.predicate(value))
                if not holds:
                    note = "predicate returned False"
            except Exception as e:
                note = f"predicate error: {e}"

        results.append({
            "file": contract.file,
            "description": contract.description,
            "holds": holds,
            "actual_type": actual_type,
            "expected_type": expected_type,
            "note": note,
        })
    return results


# ── §D: Satellite Stats (Task 3-1) ────────────────────────────────────────────
# Phase 3 of plan-full-mapa-fix.md — kills Findings #2, #9, #10, #19
# Uses exact line-counting method: len(text.splitlines()) per reviewer's manual method.

SATELLITE_BUNDLES = {
    "BUNDLE_CURADORIA":       ["indice_plano_central.md", "sat_dados_schema.md"],
    "BUNDLE_DESIGN_PIPELINE": ["indice_plano_central.md", "sat_pipeline_fluxo.md", "sat_princípios.md"],
    "BUNDLE_IMPL_PIPELINE":   ["indice_plano_central.md", "sat_pipeline_codigo.md", "sat_dados_schema.md"],
    "BUNDLE_SOLVER_DESIGN":   ["indice_plano_central.md", "sat_solver_contrato.md", "sat_princípios.md"],
    "BUNDLE_SOLVER_IMPL":     ["indice_plano_central.md", "sat_solver_contrato.md", "sat_dados_schema.md"],
    "BUNDLE_QA_SOLVER":       ["indice_plano_central.md", "sat_solver_contrato.md", "sat_testes_consolidado.md"],
    "BUNDLE_QA_DADOS":        ["indice_plano_central.md", "sat_dados_schema.md", "sat_testes_consolidado.md"],
    "BUNDLE_OPERACIONAL":     ["indice_plano_central.md", "sat_operacional.md"],
}

FILE_LOCATION_MAP = {
    "indice_plano_central.md":      "docs/architecture/",
    "sat_princípios.md":            "docs/architecture/",
    "sat_dados_schema.md":          "docs/architecture/",
    "sat_pipeline_fluxo.md":        "docs/architecture/",
    "sat_pipeline_codigo.md":       "docs/architecture/",
    "sat_solver_contrato.md":       "docs/architecture/",
    "sat_testes_consolidado.md":    "docs/governance/",
    "sat_operacional.md":           "docs/governance/",
}


def compute_satellite_stats(base_dir: Path) -> dict:
    """Count lines in each satellite file and sum per bundle.

    Uses len(text.splitlines()) — the exact method the reviewer used manually,
    so MAPA's numbers and any future auditor's numbers will always match.
    Returns dict with keys: files (dict[filename, line_count]), bundles (dict[bundle_name, total_lines]).
    """
    files = {}
    for fname, rel_dir in FILE_LOCATION_MAP.items():
        fpath = base_dir / rel_dir / fname
        if fpath.exists():
            text = fpath.read_text(encoding="utf-8")
            files[fname] = len(text.splitlines())
        else:
            files[fname] = 0

    bundles = {}
    for bundle_name, file_list in SATELLITE_BUNDLES.items():
        total = sum(files.get(f, 0) for f in file_list)
        bundles[bundle_name] = total

    return {"files": files, "bundles": bundles}


# ── §E.5: Coverage Drift Detection (Patch 1-P1) ────────────────────────────
def detect_coverage_drift(data: dict, contracts: list) -> list[str]:
    """Compare live JSON keys against STRUCTURE_CONTRACTS.covered fields.

    For each JSON file that has at least one contract, collects the union of
    all ``covers`` sets across all contracts for that file.  Any top-level key
    (or, for NUTRIENT_REGISTRY-shaped nested dicts, any per-entry field name)
    present in live data but absent from every contract's covers is returned as
    an early-warning string.

    This is deliberately **non-blocking** — it is an informational list, not a
    hard gate.  It is wired into MAPA Check 14 (informational, does not affect
    ``--gate-mapa`` exit code).
    """
    # Build per-file union of covers sets
    file_covers: dict[str, set[str]] = {}
    for contract in contracts:
        if contract.covers:
            file_covers.setdefault(contract.file, set()).update(contract.covers)

    # Nested-dict fields to introspect for union of per-entry keys
    NESTED_INTROSPECT = {"NUTRIENT_REGISTRY"}

    warnings: list[str] = []
    for fname, union_of_covers in sorted(file_covers.items()):
        live = data.get(fname)
        if live is None:
            continue  # file missing — handled by Spec Drift check

        if isinstance(live, dict):
            live_keys = set(live.keys())
            uncovered = live_keys - union_of_covers
            for key in sorted(uncovered):
                warnings.append(
                    f"{fname}: top-level key '{key}' not in any STRUCTURE_CONTRACT covers"
                )

            # Check nested dicts declared for introspection
            for nested_field in NESTED_INTROSPECT:
                nested = live.get(nested_field)
                if isinstance(nested, dict) and nested:
                    # Union of all entry-level field names across the nested dict
                    entry_keys: set[str] = set()
                    for entry in nested.values():
                        if isinstance(entry, dict):
                            entry_keys.update(entry.keys())
                    # For nested dicts, the contract covers are checked at entry level
                    # Any key in an entry not in the union is a drift signal
                    for key in sorted(entry_keys):
                        if key not in union_of_covers:
                            warnings.append(
                                f"{fname}.{nested_field}: entry field '{key}' not in any STRUCTURE_CONTRACT covers"
                            )
        elif isinstance(live, list):
            # List contracts: check entry-level keys against covers
            entry_keys = set()
            for entry in live:
                if isinstance(entry, dict):
                    entry_keys.update(entry.keys())
            for key in sorted(entry_keys):
                if key not in union_of_covers:
                    warnings.append(
                        f"{fname}: entry field '{key}' not in any STRUCTURE_CONTRACT covers"
                    )

    return warnings


# ── §E.6: Evidence Freshness (Patch 4-P1) ──────────────────────────────────
def check_evidence_freshness(worklog_path: Path, git_log_fallback: bool = True) -> dict:
    """Detect whether live-evidence has been degraded for >= 10 consecutive regenerations.

    Scans the last 10 MAPA-regeneration entries from ``worklog.md`` (if the
    convention was kept), otherwise falls back to
    ``git log --oneline -- MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md``.

    Returns ``{"consecutive_degraded": N, "warn": N >= 10}``.
    """
    DEGRADED_MARKERS = ["--no-live-evidence", "Live evidence skipped"]

    entries: list[str] = []

    # Try worklog.md first
    if worklog_path and worklog_path.is_file():
        try:
            lines = worklog_path.read_text(encoding="utf-8").splitlines()
            # Look for lines containing MAPA-regeneration keywords
            for line in reversed(lines):
                if any(kw in line.lower() for kw in ["mapa", "regeneration", "generate-mapa", "gate-mapa"]):
                    entries.append(line)
                    if len(entries) >= 10:
                        break
        except Exception:
            entries = []

    # Fallback to git log
    if not entries and git_log_fallback:
        import subprocess
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-10", "--", "MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md"],
                capture_output=True, text=True, timeout=10, cwd=str(worklog_path.parent) if worklog_path else ".",
            )
            if result.returncode == 0:
                entries = [l for l in result.stdout.splitlines() if l.strip()]
        except Exception:
            entries = []

    # Count consecutive degraded entries from most recent
    consecutive = 0
    for entry in entries:
        if any(marker in entry for marker in DEGRADED_MARKERS):
            consecutive += 1
        else:
            break  # streak broken

    return {
        "consecutive_degraded": consecutive,
        "warn": consecutive >= 10,
    }


# ── §E.7: State Hash for Idempotent Regeneration (Task 6-2) ────────────────
def compute_state_marker(base_dir: Path, json_files: list[str],
                         satellite_bundles: dict) -> str:
    """SHA-256 every file generate_mapa() reads; return 16-char hex fingerprint.

    Files hashed (sorted by path):
      - Each JSON in ``data/<json_files>``
      - ``build_pipeline.py`` itself
      - Every unique satellite ``.md`` resolved via ``FILE_LOCATION_MAP``
      - Every ``tests/test_*.py``

    Two runs against the same inputs produce the same 16-char marker.
    Any file change flips at least one bit → different marker.
    """
    import hashlib

    def _sha256_bytes(path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    # Collect unique satellite paths from FILE_LOCATION_MAP
    satellite_paths: list[Path] = []
    for fname in set().union(*satellite_bundles.values()):
        loc = FILE_LOCATION_MAP.get(fname, "docs/architecture/")
        satellite_paths.append(base_dir / loc / fname)

    # Collect test files
    tests_dir = base_dir / "tests"
    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.is_dir() else []

    # Build sorted list of (path_label, sha256_hex) for every source file
    entries: list[tuple[str, str]] = []

    # JSON files
    for jf in sorted(json_files):
        jp = base_dir / "data" / jf
        if jp.exists():
            entries.append((f"data/{jf}", _sha256_bytes(jp)))

    # gsd/core.py, gsd/nutrition.py, gsd/solver.py, gsd/mapa.py, gsd/cli.py — the
    # live package (src/gsd/). The pre-10.5 root-level core.py/solver.py/
    # nutrition_pipeline.py/mapa_docs.py/build_pipeline.py duplicates were dead
    # code (never imported by gsd.cli, the actual entry point) and were removed;
    # hashing them here previously meant this fingerprint never reflected the
    # code that actually runs.
    for src_name in ("core.py", "nutrition.py", "solver.py", "mapa.py", "cli.py"):
        sp = base_dir / "src" / "gsd" / src_name
        if sp.exists():
            entries.append((f"src/gsd/{src_name}", _sha256_bytes(sp)))

    # Satellite .md files
    for sp in sorted(satellite_paths):
        if sp.exists():
            entries.append((str(sp.relative_to(base_dir)), _sha256_bytes(sp)))

    # Test files
    for tf in sorted(test_files):
        entries.append((str(tf.relative_to(base_dir)), _sha256_bytes(tf)))

    # Concatenate all hashes and produce a single 16-char fingerprint
    combined = "".join(sha for _, sha in entries)
    marker = hashlib.sha256(combined.encode()).hexdigest()[:16]
    return marker


# ── §E: Test Integrity (Task 5-2 — D6 v1.2 REWRITTEN) ────────────────────────
# Phase 5 of plan-full-mapa-fix.md — kills Findings #17, #25
#
# CRITICAL HISTORY (D1 + D6 v1.2):
# - Original Finding #17 claimed tests use fixtures, not real JSONs. This was a
#   FALSE POSITIVE: the reviewer's `grep "json.load\|open("` returned nothing
#   because the tests call `bp.load_all_jsons()` (the production loader at
#   build_pipeline.py:86), which internally does the open/json.load calls.
# - Original v1.1.0 regex `r"\bjson\.load\(|open\("` would FALSE-POSITIVE on
#   audit-log writes (e.g., `with open("test_audit_log.md", "w") as f: ...`)
#   because those are write-side opens, not data loads.
# - The v1.2 regex recognizes two canonical ways tests load real data:
#   (1) `bp.load_all_jsons(...)` or `load_all_jsons(...)` — the production loader
#   (2) `open(("<path-inside-data/>")` — direct file access (rare, for debugging)
# Per plan Task 5-2: "the production loader IS the canonical way to load real
# data — direct json.load calls in tests are an anti-pattern (they bypass the
# loader's validation)."

import re as _re

# D6 v1.2 regex
_LOAD_ALL_JSONS_RE = _re.compile(r"\bload_all_jsons\s*\(")
_DIRECT_DATA_OPEN_RE = _re.compile(r"""open\s*\(\s*["'][^"']*data/""")

# Detect @pytest.mark.integration via AST (NOT docstring string matching)
def _has_integration_decorator(ast_module: ast.Module) -> bool:
    """Walk AST to detect @pytest.mark.integration decorators on def nodes."""
    for node in ast.walk(ast_module):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if node.decorator_list:
                for dec in node.decorator_list:
                    # Match forms: @pytest.mark.integration, @pytest.mark.integration("..."), @mark.integration
                    if isinstance(dec, ast.Attribute):
                        if dec.attr == "integration":
                            return True
                        if isinstance(dec.value, ast.Attribute) and dec.value.attr == "integration":
                            return True
                    if isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Attribute) and dec.func.attr == "integration":
                            return True
                        if isinstance(dec.func, ast.Attribute) and isinstance(dec.func.value, ast.Attribute):
                            if dec.func.value.attr == "integration":
                                return True
    return False


def check_test_integrity(tests_dir: Path) -> list[dict]:
    """Check every test_*.py file in tests_dir for AAA+A compliance.

    Per plan Task 5-2 (D6 v1.2 REWRITTEN):
    - Parses AST for @pytest.mark.integration decorators (NOT docstring matching)
    - Detects real I/O via textual regex:
      (1) r"\\bload_all_jsons\\s*\\(" — production loader (canonical way)
      (2) r'open\\s*\\(\\s*["\\'][^"\\']*data/' — direct data-file access
    - Returns one row per file: file, marked_integration (bool), loads_real_data (bool)

    Tests are AAA+A compliant if marked_integration=True → loads_real_data=True.
    Tests without @pytest.mark.integration decorators are not subject to the
    AAA+A mandate (they may be pure unit/property tests with controlled fixtures).

    D6 v1.2 IMMEDIATE VERIFICATION: every row should report loads_real_data=True
    for files that call bp.load_all_jsons(). If any row reports
    loads_real_data=False for a file that DOES call bp.load_all_jsons(), the
    regex is wrong; do not commit.
    """
    results: list = []
    if not tests_dir.is_dir():
        return results

    test_files = sorted(tests_dir.glob("test_*.py"))
    for tf in test_files:
        text = tf.read_text(encoding="utf-8")

        # Parse AST — syntax errors degrade gracefully to marked_integration=False
        marked_integration = False
        try:
            tree = ast.parse(text)
            marked_integration = _has_integration_decorator(tree)
        except SyntaxError:
            marked_integration = False

        # D6 v1.2 regex — detects production loader calls OR direct data opens.
        # IMPORTANT: a bare `r"open\("` would false-positive on audit-log writes.
        # The `data/` path guard excludes those false positives.
        loads_real_data = bool(_LOAD_ALL_JSONS_RE.search(text) or _DIRECT_DATA_OPEN_RE.search(text))

        results.append({
            "file": str(tf.name),
            "marked_integration": marked_integration,
            "loads_real_data": loads_real_data,
        })

    return results
