"""Rename templates: `{expr}` / `{expr:spec}` placeholders over book metadata. See docs/rename.md."""

import ast
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from simpleeval import InvalidExpression, SimpleEval

from efm.config import Preset
from efm.exceptions import MissingValueError, TemplateError
from efm.metadata import Metadata

FUNCTIONS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "min": min,
    "max": max,
    "round": round,
}
FILE_VARIABLES = ("ext", "stem", "name")
VARIABLES = frozenset(
    {*Metadata.model_fields, *FILE_VARIABLES} - {"schema_version", "error"}
)
# What evaluating an expression over book metadata can raise.
EVAL_ERRORS = (InvalidExpression, ArithmeticError, TypeError, ValueError, LookupError)
_OPEN = "([{"
_CLOSE = ")]}"


@dataclass(frozen=True)
class Expr:
    source: str
    names: frozenset[str]


@dataclass(frozen=True)
class Placeholder:
    expr: Expr
    spec: str


@dataclass(frozen=True)
class Template:
    text: str
    parts: tuple[str | Placeholder, ...]


@dataclass(frozen=True)
class Variant:
    condition: Expr | None
    template: Template


def parse_expr(source: str) -> Expr:
    source = source.strip()
    if not source:
        raise TemplateError("empty expression")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as e:
        raise TemplateError(f"{source!r}: {e.msg}") from e
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    if unknown := sorted(names - VARIABLES - FUNCTIONS.keys()):
        raise TemplateError(
            f"{source!r}: unknown variable {', '.join(unknown)} "
            + f"(known: {', '.join(sorted(VARIABLES))})"
        )
    return Expr(source, frozenset(names & VARIABLES))


def parse(text: str) -> Template:
    text = text.strip()
    parts: list[str | Placeholder] = []
    literal: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in "{}" and text[i + 1 : i + 2] == c:
            literal.append(c)
            i += 2
        elif c == "}":
            raise TemplateError(
                f"column {i + 1}: single '}}' (write '}}}}' for a literal one)"
            )
        elif c == "{":
            end, spec_start = _scan_placeholder(text, i)
            expr_end = spec_start if spec_start is not None else end
            spec = text[spec_start + 1 : end] if spec_start is not None else ""
            if literal:
                parts.append("".join(literal))
                literal = []
            try:
                parts.append(Placeholder(parse_expr(text[i + 1 : expr_end]), spec))
            except TemplateError as e:
                raise TemplateError(f"column {i + 1}: {e}") from e
            i = end + 1
        else:
            literal.append(c)
            i += 1
    if literal:
        parts.append("".join(literal))
    return Template(text, tuple(parts))


def _scan_placeholder(text: str, start: int) -> tuple[int, int | None]:
    """Index of the placeholder's closing brace, and of its format-spec colon if any.

    Brackets and quotes nest the same way they do in f-strings, so `{x[1:2]}` isn't a spec.
    """
    stack: list[str] = []
    quote: str | None = None
    spec_start: int | None = None
    i = start + 1
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif spec_start is not None:
            if c == "}":
                return i, spec_start
            if c == "{":
                raise TemplateError(
                    f"column {i + 1}: nested placeholders in a format spec aren't supported"
                )
        elif c in "'\"":
            quote = c
        elif c in _OPEN:
            stack.append(_CLOSE[_OPEN.index(c)])
        elif c in _CLOSE:
            if not stack:
                if c == "}":
                    return i, None
                raise TemplateError(f"column {i + 1}: unbalanced {c!r}")
            if stack.pop() != c:
                raise TemplateError(f"column {i + 1}: unbalanced {c!r}")
        elif c == ":" and not stack:
            spec_start = i
        i += 1
    raise TemplateError(
        f"column {start + 1}: '{{' is never closed (write '{{{{' for a literal one)"
    )


def compile_preset(preset: Preset) -> list[Variant]:
    if isinstance(preset, str):
        return [Variant(None, parse(preset))]
    variants: list[Variant] = []
    for item in preset:
        if isinstance(item, str):
            variants.append(Variant(None, parse(item)))
        else:
            condition = parse_expr(item.if_) if item.if_ else None
            variants.append(Variant(condition, parse(item.value)))
    if not variants:
        raise TemplateError("preset has no templates")
    return variants


def template_vars(book_file: Path, metadata: Metadata) -> dict[str, Any]:
    values = metadata.model_dump()
    values["series_index"] = _as_number(metadata.series_index)
    values |= {"ext": book_file.suffix, "stem": book_file.stem, "name": book_file.name}
    return {k: v for k, v in values.items() if k in VARIABLES}


def _as_number(value: str | None) -> int | float | str | None:
    if value is None:
        return None
    try:
        n = float(value)
    except ValueError:
        return value
    return int(n) if n.is_integer() else n


def _evaluate(expr: Expr, variables: Mapping[str, Any]) -> Any:
    evaluator = SimpleEval(names=dict(variables), functions=FUNCTIONS)
    try:
        return evaluator.eval(expr.source)
    except EVAL_ERRORS as e:
        if missing := _missing(expr, variables):
            raise MissingValueError(expr.source, missing) from e
        raise TemplateError(f"{{{expr.source}}}: {e}") from e


def _missing(expr: Expr, variables: Mapping[str, Any]) -> list[str]:
    return sorted(n for n in expr.names if variables.get(n) is None)


def choose(variants: Sequence[Variant], variables: Mapping[str, Any]) -> Template:
    """The first variant whose condition holds. Missing values in conditions are just None."""
    for v in variants:
        if v.condition is None:
            return v.template
        try:
            holds = SimpleEval(names=dict(variables), functions=FUNCTIONS).eval(
                v.condition.source
            )
        except EVAL_ERRORS as e:
            raise TemplateError(f"if {v.condition.source!r}: {e}") from e
        if holds:
            return v.template
    raise TemplateError("no variant's condition matched")


def render(template: Template, variables: Mapping[str, Any]) -> PurePosixPath:
    out: list[str] = []
    for part in template.parts:
        if isinstance(part, str):
            out.append(part)
            continue
        value = _evaluate(part.expr, variables)
        if value is None:
            raise MissingValueError(part.expr.source, _missing(part.expr, variables))
        if isinstance(value, str):
            # Newlines and tabs from metadata; done before format() so spec padding survives.
            value = " ".join(value.split())
        try:
            formatted = format(value, part.spec)
        except (TypeError, ValueError) as e:
            raise TemplateError(f"{{{part.expr.source}:{part.spec}}}: {e}") from e
        # A value is never a path separator: "AC/DC" is one name.
        out.append(formatted.replace("/", "_").replace("\0", "_"))
    return _to_relative_path("".join(out))


def _to_relative_path(rendered: str) -> PurePosixPath:
    if rendered.startswith("/"):
        raise TemplateError(
            f"{rendered!r} is absolute; templates are relative to the root"
        )
    components = rendered.split("/")
    for c in components:
        if c in ("", ".", ".."):
            raise TemplateError(f"{rendered!r} has an empty, '.', or '..' component")
    return PurePosixPath(*components)
