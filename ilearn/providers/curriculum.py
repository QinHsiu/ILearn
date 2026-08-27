"""Curriculum data access for the ILearn MVP pilot pack."""

from __future__ import annotations

import ast
import json
import math
import operator
import random
import re
from abc import ABC, abstractmethod
from fractions import Fraction
from pathlib import Path
from typing import Any

from ilearn.core.schemas import Difficulty, ItemTemplate, ItemType, KnowledgeNode

PILOT_LABEL = "北京·人教·小学数学"
PILOT_GRADES = frozenset({4, 5, 6})
_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


class CurriculumError(Exception):
    """Raised when curriculum data is unavailable for the requested context."""


def require_pilot_grade(grade: int) -> int:
    if grade not in PILOT_GRADES:
        raise CurriculumError(
            f"试点内容目前覆盖 4–6 年级数学，暂不支持 {grade} 年级"
        )
    return grade


def load_syllabus(pilot_dir: str | Path) -> list[dict[str, Any]]:
    """Load raw syllabus citation records from the pilot pack."""
    path = Path(pilot_dir) / "syllabus.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_example_bank(pilot_dir: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Load teacher-reviewed examples keyed by knowledge_id."""
    path = Path(pilot_dir) / "example_bank.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_multimodal_bank(pilot_dir: str | Path) -> list[dict[str, Any]]:
    """Load validated multimodal assessment items from the pilot pack."""
    path = Path(pilot_dir) / "multimodal_bank.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []

_SAFE_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_SAFE_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _lcm(a: Any, b: Any) -> int:
    x, y = int(a), int(b)
    return x * y // math.gcd(x, y)


def _frac(n: Any, d: Any) -> Fraction:
    """Build a simplified fraction from numerator and denominator."""
    return Fraction(int(n), int(d))


def _ratio(a: Any, b: Any) -> str:
    """Format an ordered ratio without converting it to a decimal."""
    return f"{int(a)}:{int(b)}"


_SAFE_FUNCS = {
    "round": round,
    "abs": abs,
    "min": min,
    "max": max,
    "gcd": math.gcd,
    "lcm": _lcm,
    "frac": _frac,
    "ratio": _ratio,
}


def _to_number(value: Any) -> int | float:
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("empty numeric slot value")
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    return float(text)


def _format_fraction(value: Fraction) -> str:
    simplified = Fraction(value.numerator, value.denominator)
    if simplified.denominator == 1:
        return str(simplified.numerator)
    return f"{simplified.numerator}/{simplified.denominator}"


def _format_answer(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Fraction):
        return _format_fraction(value)
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(round(value, 2))
    return str(value)


def parse_slot_spec(spec: str, rng: random.Random) -> int | str:
    """Resolve one slot spec such as ``int:1-8`` or ``choice:2,4,5,8``."""
    if spec.startswith("int:"):
        lo_s, hi_s = spec[4:].split("-", 1)
        return rng.randint(int(lo_s), int(hi_s))
    if spec.startswith("choice:"):
        options = [part.strip() for part in spec[7:].split(",") if part.strip()]
        if not options:
            raise ValueError(f"empty choice spec: {spec!r}")
        return rng.choice(options)
    raise ValueError(f"unsupported slot spec: {spec!r}")


def fill_slots(slot_specs: dict[str, str], rng: random.Random) -> dict[str, Any]:
    """Fill all slot specs deterministically for a given RNG."""
    return {name: parse_slot_spec(spec, rng) for name, spec in slot_specs.items()}


def fill_template_slots(record: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Fill slot specs and any ``derived_slots`` expressions for one template record."""
    values = fill_slots(record.get("slots") or {}, rng)
    for name, expr in (record.get("derived_slots") or {}).items():
        values[name] = _to_number(eval_answer_expr(expr, values))
    return values


def _build_render_env(values: dict[str, Any], answer: str | None = None) -> dict[str, Any]:
    env: dict[str, Any] = {}
    for key, val in values.items():
        try:
            env[key] = _to_number(val)
        except ValueError:
            env[key] = val
    if answer is not None:
        env["ans"] = answer
    return env


def _eval_ast(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ValueError(f"unknown variable in expression: {node.id}")
        return env[node.id]
    if isinstance(node, ast.BinOp):
        op = _SAFE_BINOPS.get(type(node.op))
        if op is None:
            raise ValueError("unsupported binary operator in expression")
        return op(_eval_ast(node.left, env), _eval_ast(node.right, env))
    if isinstance(node, ast.UnaryOp):
        op = _SAFE_UNARYOPS.get(type(node.op))
        if op is None:
            raise ValueError("unsupported unary operator in expression")
        return op(_eval_ast(node.operand, env))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("unsupported function call in expression")
        func = _SAFE_FUNCS.get(node.func.id)
        if func is None:
            raise ValueError(f"unsupported function in expression: {node.func.id}")
        args = [_eval_ast(arg, env) for arg in node.args]
        return func(*args)
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


def _eval_expression(expr: str, env: dict[str, Any]) -> Any:
    tree = ast.parse(expr.strip(), mode="eval")
    return _eval_ast(tree, env)


def eval_answer_expr(expr: str, values: dict[str, Any]) -> str:
    """Evaluate a restricted arithmetic expression against slot values."""
    expr = expr.strip()
    if not expr:
        raise ValueError("empty answer_expr")
    if (expr.startswith('"') and expr.endswith('"')) or (
        expr.startswith("'") and expr.endswith("'")
    ):
        return expr[1:-1]
    env = _build_render_env(values)
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return expr
    if isinstance(tree.body, ast.Name) and tree.body.id not in env:
        return expr
    try:
        result = _eval_ast(tree, env)
    except ValueError:
        return expr
    return _format_answer(result)


def render_template_text(
    template: str,
    values: dict[str, Any],
    *,
    answer: str | None = None,
) -> str:
    """Render a template, expanding slot names and expression placeholders safely."""
    env = _build_render_env(values, answer=answer)

    def _replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        if token == "ans":
            if answer is None:
                raise ValueError("{ans} requires answer= when rendering")
            return answer
        if token.isidentifier() and token in values:
            return str(values[token])
        return _format_answer(_eval_expression(token, env))

    return _PLACEHOLDER.sub(_replace, template)


def render_template(template: str, values: dict[str, Any]) -> str:
    """Format a template string with resolved slot values only (no expressions)."""
    return template.format(**values)


def render_choices(
    choices_template: list[str],
    values: dict[str, Any],
    *,
    answer: str | None = None,
) -> list[str]:
    """Render choice strings, including ``{ans}`` and expression distractors."""
    return [
        render_template_text(choice, values, answer=answer)
        for choice in choices_template
    ]


class CurriculumProvider(ABC):
    """Abstract curriculum source for knowledge nodes and item templates."""

    @property
    @abstractmethod
    def label(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_knowledge(self, grade: int) -> list[KnowledgeNode]:
        raise NotImplementedError

    @abstractmethod
    def list_templates(
        self,
        grade: int,
        difficulty: Difficulty | None = None,
        item_type: ItemType | None = None,
    ) -> list[ItemTemplate]:
        raise NotImplementedError

    def get_template_record(self, template_id: str) -> dict[str, Any]:
        """Return the raw template JSON record (includes slots and answer_expr)."""
        raise NotImplementedError


class PilotBeijingRenjiaoProvider(CurriculumProvider):
    """Fixed Beijing · Renjiao elementary math pilot pack (grades 4–6)."""

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)
        knowledge_path = self._data_dir / "knowledge.json"
        templates_path = self._data_dir / "templates.json"
        self._knowledge = [
            KnowledgeNode.model_validate(row)
            for row in json.loads(knowledge_path.read_text(encoding="utf-8"))
        ]
        self._raw_templates: list[dict[str, Any]] = json.loads(
            templates_path.read_text(encoding="utf-8")
        )
        self._templates_by_id = {row["id"]: row for row in self._raw_templates}

    @property
    def label(self) -> str:
        return PILOT_LABEL

    def list_knowledge(self, grade: int) -> list[KnowledgeNode]:
        require_pilot_grade(grade)
        return [node for node in self._knowledge if node.grade == grade]

    def list_templates(
        self,
        grade: int,
        difficulty: Difficulty | None = None,
        item_type: ItemType | None = None,
    ) -> list[ItemTemplate]:
        require_pilot_grade(grade)
        rows: list[ItemTemplate] = []
        for raw in self._raw_templates:
            grades = raw.get("grades") or [raw.get("grade")]
            if grade not in grades:
                continue
            if difficulty is not None and raw["difficulty"] != difficulty:
                continue
            if item_type is not None and raw["item_type"] != item_type:
                continue
            rows.append(self._to_item_template(raw, grade))
        return rows

    def get_template_record(self, template_id: str) -> dict[str, Any]:
        try:
            return self._templates_by_id[template_id]
        except KeyError as exc:
            raise KeyError(f"unknown template id: {template_id}") from exc

    @staticmethod
    def _to_item_template(raw: dict[str, Any], grade: int) -> ItemTemplate:
        slots = raw.get("slots") or {}
        situation_tag = raw.get("situation_tag")
        return ItemTemplate(
            id=raw["id"],
            knowledge_ids=list(raw["knowledge_ids"]),
            grade=grade,  # type: ignore[arg-type]
            item_type=raw["item_type"],
            difficulty=raw["difficulty"],
            stem_template=raw["stem_template"],
            answer_template=raw.get("answer_expr") or raw.get("answer_key_template"),
            rubric_steps=list(raw.get("rubric_steps") or []),
            choices_template=list(raw["choices_template"])
            if raw.get("choices_template")
            else None,
            slot_names=list(slots.keys()),
            situation_tag=situation_tag,
        )
