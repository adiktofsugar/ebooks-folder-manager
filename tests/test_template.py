from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from efm.config import RenameVariant
from efm.exceptions import MissingValueError, TemplateError
from efm.metadata import Metadata
from efm.template import choose, compile_preset, parse, render, template_vars


def _vars(**fields: Any) -> dict[str, Any]:
    name = fields.pop("name", "old.epub")
    return template_vars(Path("/books") / name, Metadata(size=1, **fields))


def _render(text: str, **fields: Any) -> str:
    return str(render(parse(text), _vars(**fields)))


def test_simple_fields():
    assert _render("{author}/{title}{ext}", title="T", author="A") == "A/T.epub"


def test_file_variables():
    assert _render("{stem}-{name}", name="My Book.EPUB") == "My Book-My Book.EPUB"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("{{draft}} {title}", "{draft} T"),
        ("a}}b{title}", "a}bT"),
    ],
)
def test_doubled_braces_are_literal(text: str, expected: str):
    assert _render(text, title="T") == expected


def test_format_spec_and_series_index_number():
    out = _render(
        "{series}/{series_index:02} {title:>4}", series="S", series_index="3", title="T"
    )
    assert out == "S/03    T"


def test_fractional_series_index():
    assert _render("{series_index}", series="S", series_index="1.5") == "1.5"


def test_expressions():
    out = _render(
        "{author.split(', ')[0]}/{title[:3]}{' (' + subject + ')' if subject else ''}",
        author="Pratchett, Terry",
        title="Interesting Times",
    )
    assert out == "Pratchett/Int"


def test_colon_inside_brackets_is_not_a_spec():
    assert _render("{title[1:3]}", title="abcd") == "bc"


def test_colon_inside_string_is_not_a_spec():
    assert _render("{title + ':x'}", title="a") == "a:x"


def test_missing_value_names_the_variable():
    with pytest.raises(MissingValueError) as e:
        _render("{series}/{title}", title="T")
    assert e.value.missing == ["series"]


def test_missing_value_inside_expression():
    with pytest.raises(MissingValueError) as e:
        _render("{author.upper()}", title="T")
    assert e.value.missing == ["author"]


def test_slash_in_value_is_not_a_folder():
    assert render(parse("{title}{ext}"), _vars(title="AC/DC")) == PurePosixPath(
        "AC_DC.epub"
    )


def test_whitespace_in_values_collapses():
    assert _render("{title}", title="a\n  b") == "a b"


def test_multiline_template_is_stripped():
    assert _render("\n  {title}\n", title="T") == "T"


@pytest.mark.parametrize(
    "text",
    ["/{title}", "{title}//x", "../{title}", "{title}/./x", "{title}/"],
)
def test_bad_paths_rejected(text: str):
    with pytest.raises(TemplateError):
        _render(text, title="T")


@pytest.mark.parametrize(
    "text",
    ["{title", "title}", "{}", "{titel}", "{title:{x}}", "{(title}", "{title +}"],
)
def test_parse_errors(text: str):
    with pytest.raises(TemplateError):
        parse(text)


@pytest.mark.parametrize(
    "text",
    ["{title.__class__}", "{__import__('os')}", "{open('x')}", "{title.format(1)}"],
)
def test_unsafe_expressions_rejected(text: str):
    with pytest.raises(TemplateError):
        _render(text, title="T")


def test_variants_first_match_wins():
    variants = compile_preset(
        [
            RenameVariant.model_validate({"if": "series", "value": "{series}/{title}"}),
            RenameVariant.model_validate({"if": "author", "value": "{author}/{title}"}),
            "{title}",
        ]
    )

    def pick(**fields: Any) -> str:
        variables = _vars(**fields)
        return str(render(choose(variants, variables), variables))

    assert pick(title="T", series="S", author="A") == "S/T"
    assert pick(title="T", author="A") == "A/T"
    assert pick(title="T") == "T"


def test_variant_condition_expression():
    variants = compile_preset(
        [
            RenameVariant.model_validate(
                {"if": "title.startswith('T')", "value": "t/{title}"}
            ),
            "{title}",
        ]
    )
    assert choose(variants, _vars(title="Tea")).text == "t/{title}"
    assert choose(variants, _vars(title="Cat")).text == "{title}"


def test_no_variant_matches():
    variants = compile_preset(
        [RenameVariant.model_validate({"if": "series", "value": "x"})]
    )
    with pytest.raises(TemplateError):
        choose(variants, _vars(title="T"))


def test_error_in_condition_is_an_error():
    variants = compile_preset(
        [RenameVariant.model_validate({"if": "series.lower()", "value": "x"}), "y"]
    )
    with pytest.raises(TemplateError):
        choose(variants, _vars(title="T"))


def test_bad_variant_template_fails_at_compile():
    with pytest.raises(TemplateError):
        compile_preset(["{title", "ok"])
