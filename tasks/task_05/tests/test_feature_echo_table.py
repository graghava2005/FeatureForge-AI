from __future__ import annotations

import io

import pytest

import click
from click.testing import CliRunner


def test_format_table_simple_default_and_alignment():
    out = click.format_table(
        rows=[["alpha", 42], ["beta", 7]],
        headers=["Name", "Count"],
        align=["left", "right"],
    )
    lines = out.splitlines()
    assert lines == [
        "Name   Count",
        "-----  -----",
        "alpha     42",
        "beta       7",
    ]


def test_format_table_plain_and_grid_borders():
    plain = click.format_table(
        rows=[["a", "b"], ["cc", "d"]],
        headers=["H1", "H2"],
        border="plain",
    )
    assert plain.splitlines() == [
        "H1  H2",
        "a   b",
        "cc  d",
    ]

    grid = click.format_table(
        rows=[["x", 1], ["yy", 22]],
        headers=["Key", "Val"],
        align=["center", "right"],
        border="grid",
    )
    assert grid.splitlines() == [
        "+-----+-----+",
        "| Key | Val |",
        "+-----+-----+",
        "|  x  |   1 |",
        "| yy  |  22 |",
        "+-----+-----+",
    ]


def test_format_table_ansi_aware_alignment():
    ok = click.style("OK", fg="green")
    fail = click.style("FAIL", fg="red")
    out = click.format_table(
        rows=[[ok, "svc-a"], [fail, "svc-b"]],
        headers=["State", "Service"],
        border="grid",
    )
    lines = out.splitlines()
    # Visible widths must match even though ANSI escape strings differ in raw length
    assert [click._compat.term_len(line) for line in lines] == [len(lines[0])] * len(lines)


def test_format_table_ragged_rows_none_and_empty():
    assert click.format_table([]) == ""

    headers_only = click.format_table([], headers=["A", "B"])
    assert headers_only.splitlines() == ["A  B", "-  -"]

    ragged = click.format_table(
        rows=[[None, "x"], ["long", None, 9]],
        headers=["C1", "C2"],
        border="plain",
    )
    assert ragged.splitlines() == [
        "C1    C2",
        "      x",
        "long      9",
    ]


def test_format_table_max_col_width_truncation():
    out = click.format_table(
        rows=[["abcdefghij", "xy"], ["123", "1234567"]],
        headers=["ColA", "ColB"],
        max_col_width=6,
        border="plain",
    )
    assert out.splitlines() == [
        "ColA    ColB",
        "abc...  xy",
        "123     123...",
    ]


def test_format_table_invalid_arguments():
    with pytest.raises(ValueError, match="border"):
        click.format_table([["a"]], border="markdown")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="alignment"):
        click.format_table([["a"]], align="justify")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="max_col_width"):
        click.format_table([["a"]], max_col_width=0)
    with pytest.raises(ValueError, match="padding"):
        click.format_table([["a"]], padding=-1)


def test_echo_table_stream_and_cli_runner():
    buf = io.StringIO()
    styled = click.style("UP", fg="green")
    click.echo_table([[styled, 10]], headers=["Status", "N"], file=buf, color=False)
    assert "\033[" not in buf.getvalue()
    assert "UP" in buf.getvalue()

    @click.command()
    def status():
        click.echo_table([["api", "ready"]], headers=["Service", "State"], border="grid")

    runner = CliRunner()
    res = runner.invoke(status, [])
    assert res.exit_code == 0
    assert "+---------+-------+" in res.output
    assert "| api     | ready |" in res.output
