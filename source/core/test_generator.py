"""Module E: Automated Feature & Regression Test Generator."""

from __future__ import annotations

import ast
import json
from typing import Any


def _extract_test_node_ids(test_filename: str, test_code: str) -> list[str]:
    tree = ast.parse(test_code)
    node_ids: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            node_ids.append(f"{test_filename}::{node.name}")
    return node_ids


def _feature_tests_by_task() -> dict[str, dict[str, Any]]:
    return {
        "task_01": {
            "filename": "test_feature_option_constraints.py",
            "regression_files": [
                "tests/test_options.py",
                "tests/test_defaults.py",
                "tests/test_info_dict.py",
            ],
            "code": '''from __future__ import annotations

import click
from click.testing import CliRunner


def test_conflicts_with_rejects_both_flags():
    @click.command()
    @click.option("--json", "as_json", is_flag=True, conflicts_with=["csv"])
    @click.option("--csv", is_flag=True, conflicts_with=["as_json"])
    def export(as_json, csv):
        click.echo(f"json={as_json},csv={csv}")

    runner = CliRunner()
    res_ok = runner.invoke(export, ["--json"])
    assert res_ok.exit_code == 0
    assert res_ok.output.strip() == "json=True,csv=False"

    res_conflict = runner.invoke(export, ["--json", "--csv"])
    assert res_conflict.exit_code == 2
    assert "mutually exclusive" in res_conflict.output.lower()


def test_conflicts_with_allows_defaults_without_false_positive():
    @click.command()
    @click.option("--verbose", is_flag=True, default=False, conflicts_with=["quiet"])
    @click.option("--quiet", is_flag=True, default=False, conflicts_with=["verbose"])
    def build(verbose, quiet):
        click.echo(f"v={verbose},q={quiet}")

    runner = CliRunner()
    res = runner.invoke(build, [])
    assert res.exit_code == 0
    assert res.output.strip() == "v=False,q=False"


def test_asymmetric_conflicts_with_works_regardless_of_order():
    @click.command()
    @click.option("--fast", is_flag=True, conflicts_with=["--dry-run"])
    @click.option("--dry-run", is_flag=True)
    def deploy(fast, dry_run):
        click.echo("ok")

    runner = CliRunner()
    r1 = runner.invoke(deploy, ["--fast", "--dry-run"])
    r2 = runner.invoke(deploy, ["--dry-run", "--fast"])
    assert r1.exit_code == 2
    assert r2.exit_code == 2
    assert "mutually exclusive" in r1.output.lower()
    assert "mutually exclusive" in r2.output.lower()


def test_requires_fails_when_dependency_missing_and_passes_when_given():
    @click.command()
    @click.option("--ssl", is_flag=True, requires=["ssl_cert", "ssl-key"])
    @click.option("--ssl-cert")
    @click.option("--ssl-key")
    def serve(ssl, ssl_cert, ssl_key):
        click.echo(f"{ssl}:{ssl_cert}:{ssl_key}")

    runner = CliRunner()
    res_missing = runner.invoke(serve, ["--ssl", "--ssl-cert", "cert.pem"])
    assert res_missing.exit_code == 2
    assert "requires" in res_missing.output.lower()

    res_ok = runner.invoke(
        serve, ["--ssl", "--ssl-cert", "cert.pem", "--ssl-key", "key.pem"]
    )
    assert res_ok.exit_code == 0
    assert res_ok.output.strip() == "True:cert.pem:key.pem"


def test_requires_satisfied_by_default_map_and_non_none_default():
    @click.command()
    @click.option("--tls", is_flag=True, requires=["ca_bundle", "token"])
    @click.option("--ca-bundle", default="/etc/ssl/certs/ca.pem")
    @click.option("--token")
    def connect(tls, ca_bundle, token):
        click.echo(f"{tls}:{ca_bundle}:{token}")

    runner = CliRunner()
    res_missing = runner.invoke(connect, ["--tls"])
    assert res_missing.exit_code == 2

    res_ok = runner.invoke(connect, ["--tls"], default_map={"token": "abc"})
    assert res_ok.exit_code == 0
    assert res_ok.output.strip() == "True:/etc/ssl/certs/ca.pem:abc"


def test_envvar_conflict_and_requires_detection():
    @click.command()
    @click.option("--local", is_flag=True, envvar="APP_LOCAL", conflicts_with=["remote"])
    @click.option("--remote", envvar="APP_REMOTE", requires=["token"])
    @click.option("--token", envvar="APP_TOKEN")
    def sync(local, remote, token):
        click.echo(f"{local}:{remote}:{token}")

    runner = CliRunner()
    res_conflict = runner.invoke(sync, ["--local"], env={"APP_REMOTE": "https://x"})
    assert res_conflict.exit_code == 2
    assert "mutually exclusive" in res_conflict.output.lower()

    res_missing_req = runner.invoke(sync, [], env={"APP_REMOTE": "https://x"})
    assert res_missing_req.exit_code == 2
    assert "requires" in res_missing_req.output.lower()

    res_ok = runner.invoke(
        sync, [], env={"APP_REMOTE": "https://x", "APP_TOKEN": "sec"}
    )
    assert res_ok.exit_code == 0
    assert res_ok.output.strip() == "False:https://x:sec"


def test_help_and_resilient_parsing_bypass_constraints():
    @click.command()
    @click.option("--a", is_flag=True, conflicts_with=["b"])
    @click.option("--b", is_flag=True, requires=["missing_partner"])
    @click.option("--missing-partner")
    def cli(a, b, missing_partner):
        click.echo("ran")

    runner = CliRunner()
    help_res = runner.invoke(cli, ["--a", "--b", "--help"])
    assert help_res.exit_code == 0
    assert "Usage:" in help_res.output

    with cli.make_context("cli", ["--a", "--b"], resilient_parsing=True) as ctx:
        assert ctx.params["a"] is True
        assert ctx.params["b"] is True


def test_option_to_info_dict_with_and_without_constraints():
    plain_opt = click.Option(["--plain"])
    assert "conflicts_with" not in plain_opt.to_info_dict()
    assert "requires" not in plain_opt.to_info_dict()

    constrained_opt = click.Option(
        ["--mode"], conflicts_with=["--raw-mode", "raw_mode"], requires=["--target"]
    )
    info = constrained_opt.to_info_dict()
    assert info["conflicts_with"] == ["raw_mode"]
    assert info["requires"] == ["target"]
''',
        },
        "task_02": {
            "filename": "test_feature_command_aliases.py",
            "regression_files": [
                "tests/test_commands.py",
                "tests/test_chain.py",
                "tests/test_normalization.py",
                "tests/test_info_dict.py",
            ],
            "code": '''from __future__ import annotations

import pytest

import click
from click.testing import CliRunner


def test_invoke_subcommand_via_aliases():
    @click.group()
    def cli():
        pass

    @cli.command(aliases=["co", "chk"])
    @click.argument("branch")
    @click.pass_context
    def checkout(ctx, branch):
        click.echo(f"cmd={ctx.info_name}|sub={ctx.parent.invoked_subcommand}|b={branch}")

    runner = CliRunner()
    for token in ("checkout", "co", "chk"):
        res = runner.invoke(cli, [token, "main"])
        assert res.exit_code == 0
        assert res.output.strip() == "cmd=checkout|sub=checkout|b=main"


def test_group_help_displays_aliases():
    @click.group()
    def cli():
        pass

    @cli.command(aliases=["d", "dep"])
    def deploy():
        """Deploy the application."""

    @cli.command()
    def status():
        """Show status."""

    runner = CliRunner()
    res = runner.invoke(cli, ["--help"])
    assert res.exit_code == 0
    assert "deploy (d, dep)" in res.output
    assert "Deploy the application." in res.output
    assert "status" in res.output


def test_alias_collision_raises_value_error():
    @click.group()
    def cli():
        pass

    @cli.command(aliases=["rm"])
    def remove():
        pass

    with pytest.raises(ValueError, match="collides"):
        @cli.command(name="rm")
        def rm_conflict():
            pass

    with pytest.raises(ValueError, match="collides"):
        @cli.command(aliases=["rm"])
        def delete():
            pass

    with pytest.raises(ValueError, match="collides"):
        @cli.command(aliases=["remove"])
        def purge():
            pass


def test_chained_group_resolves_aliases():
    @click.group(chain=True)
    def cli():
        pass

    @cli.command(aliases=["b"])
    def build():
        click.echo("building")

    @cli.command(aliases=["t"])
    def test():
        click.echo("testing")

    runner = CliRunner()
    res = runner.invoke(cli, ["b", "t"])
    assert res.exit_code == 0
    assert res.output.splitlines() == ["building", "testing"]


def test_token_normalize_func_applies_to_aliases():
    @click.group(context_settings={"token_normalize_func": str.lower})
    def cli():
        pass

    @cli.command(aliases=["LS"])
    def list_items():
        click.echo("listed")

    runner = CliRunner()
    res = runner.invoke(cli, ["ls"])
    assert res.exit_code == 0
    assert res.output.strip() == "listed"


def test_unknown_command_or_alias_still_fails():
    @click.group()
    def cli():
        pass

    @cli.command(aliases=["co"])
    def checkout():
        pass

    runner = CliRunner()
    res = runner.invoke(cli, ["unknown"])
    assert res.exit_code == 2
    assert "No such command" in res.output


def test_command_to_info_dict_aliases_backward_compatible():
    plain = click.Command("run")
    aliased = click.Command("run", aliases=["r", "exec"])
    ctx_plain = click.Context(plain)
    ctx_aliased = click.Context(aliased)

    assert "aliases" not in plain.to_info_dict(ctx_plain)
    assert aliased.to_info_dict(ctx_aliased)["aliases"] == ["r", "exec"]
''',
        },
        "task_03": {
            "filename": "test_feature_bytesize_type.py",
            "regression_files": [
                "tests/test_types/",
                "tests/test_info_dict.py",
            ],
            "code": '''from __future__ import annotations

import pytest

import click
from click.testing import CliRunner


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", 0),
        ("512", 512),
        ("512B", 512),
        ("2K", 2048),
        ("2KB", 2048),
        ("2KiB", 2048),
        ("1.5KiB", 1536),
        (" 4 mib ", 4 * 1024**2),
        ("1G", 1024**3),
        ("1.5 GiB", int(1.5 * 1024**3)),
        ("2TB", 2 * 1024**4),
        ("1PiB", 1024**5),
        (4096, 4096),
    ],
)
def test_bytesize_binary_conversions(raw, expected):
    bs = click.ByteSize()
    assert bs.convert(raw, None, None) == expected


def test_bytesize_decimal_si_mode_and_explicit_iec():
    bs = click.ByteSize(binary=False)
    assert bs.convert("2K", None, None) == 2000
    assert bs.convert("2KB", None, None) == 2000
    assert bs.convert("3MB", None, None) == 3_000_000
    assert bs.convert("1.5GB", None, None) == 1_500_000_000
    # Explicit IEC suffixes always remain powers of 1024
    assert bs.convert("2KiB", None, None) == 2048
    assert bs.convert("1MiB", None, None) == 1024**2


def test_bytesize_bounds_enforcement():
    bs = click.ByteSize(min=1024, max=10 * 1024)
    assert bs.convert("1KiB", None, None) == 1024
    assert bs.convert("10KiB", None, None) == 10 * 1024

    with pytest.raises(click.BadParameter, match="smaller than the minimum"):
        bs.convert("512B", None, None)

    with pytest.raises(click.BadParameter, match="larger than the maximum"):
        bs.convert("11KiB", None, None)

    with pytest.raises(click.BadParameter):
        bs.convert(500, None, None)


def test_bytesize_invalid_constructor_bounds():
    with pytest.raises(ValueError):
        click.ByteSize(min=-1)
    with pytest.raises(ValueError):
        click.ByteSize(max=-5)
    with pytest.raises(ValueError):
        click.ByteSize(min=200, max=100)


@pytest.mark.parametrize(
    "bad_val",
    ["", "   ", "-10MB", "NaN", "inf", "10XB", "MB", True, False, 12.5, object()],
)
def test_bytesize_rejects_invalid_inputs(bad_val):
    bs = click.ByteSize()
    with pytest.raises(click.BadParameter):
        bs.convert(bad_val, None, None)


def test_bytesize_cli_integration():
    @click.command()
    @click.option("--limit", type=click.ByteSize(min=1024, max=1024**3), required=True)
    def run(limit):
        click.echo(f"limit={limit}")

    runner = CliRunner()
    ok = runner.invoke(run, ["--limit", "2MiB"])
    assert ok.exit_code == 0
    assert ok.output.strip() == f"limit={2 * 1024**2}"

    bad = runner.invoke(run, ["--limit", "100B"])
    assert bad.exit_code == 2
    assert "Invalid value for '--limit'" in bad.output


def test_bytesize_metadata_and_metavar():
    bs = click.ByteSize(min=1024, max=2048, binary=False)
    info = bs.to_info_dict()
    assert info == {
        "param_type": "ByteSize",
        "name": "bytesize",
        "min": 1024,
        "max": 2048,
        "binary": False,
    }
    param = click.Option(["--size"], type=bs)
    ctx = click.Context(click.Command("cmd", params=[param]))
    assert bs.get_metavar(param, ctx) == "[BYTESIZE:1024..2048]"
    assert click.ByteSize().get_metavar(param, ctx) == "[BYTESIZE]"
''',
        },
        "task_04": {
            "filename": "test_feature_no_color_env.py",
            "regression_files": [
                "tests/test_basic.py",
                "tests/test_termui.py",
                "tests/test_compat.py",
                "tests/test_context.py",
            ],
            "code": '''from __future__ import annotations

import io

import click
from click._compat import should_strip_ansi
from click.globals import resolve_color_default
from click.testing import CliRunner


class _FakeTTYStream(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_no_color_disables_color_even_on_tty(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)

    assert resolve_color_default() is False
    tty = _FakeTTYStream()
    assert should_strip_ansi(tty, resolve_color_default(None)) is True

    click.secho("hello", fg="red", file=tty)
    assert tty.getvalue() == "hello\\n"


def test_empty_no_color_has_no_effect(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "")
    monkeypatch.delenv("FORCE_COLOR", raising=False)

    assert resolve_color_default() is None
    tty = _FakeTTYStream()
    assert should_strip_ansi(tty, resolve_color_default(None)) is False

    click.secho("hello", fg="red", file=tty)
    assert "\\033[" in tty.getvalue()

    # Empty NO_COLOR must not block FORCE_COLOR
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert resolve_color_default() is True
    buf = io.StringIO()
    click.secho("hello", fg="red", file=buf)
    assert "\\033[" in buf.getvalue()


def test_force_color_enables_color_on_non_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert resolve_color_default() is True
    buf = io.StringIO()
    assert should_strip_ansi(buf, resolve_color_default(None)) is False

    click.secho("forced", fg="green", file=buf)
    assert "\\033[" in buf.getvalue()


def test_force_color_zero_or_false_does_not_force(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    for val in ("0", "false", "FALSE"):
        monkeypatch.setenv("FORCE_COLOR", val)
        assert resolve_color_default() is None
        buf = io.StringIO()
        click.secho("plain", fg="green", file=buf)
        assert "\\033[" not in buf.getvalue()

    monkeypatch.setenv("FORCE_COLOR", "always")
    assert resolve_color_default() is True
    buf_active = io.StringIO()
    click.secho("colored", fg="green", file=buf_active)
    assert "\\033[" in buf_active.getvalue()


def test_no_color_overrides_force_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "true")
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert resolve_color_default() is False
    tty = _FakeTTYStream()
    click.secho("muted", fg="yellow", file=tty)
    assert tty.getvalue() == "muted\\n"


def test_explicit_color_argument_overrides_env_vars(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert resolve_color_default() is False
    buf1 = io.StringIO()
    click.secho("forced-explicit", fg="blue", file=buf1, color=True)
    assert "\\033[" in buf1.getvalue()

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert resolve_color_default() is True
    buf2 = _FakeTTYStream()
    click.secho("stripped-explicit", fg="blue", file=buf2, color=False)
    assert buf2.getvalue() == "stripped-explicit\\n"


def test_context_color_overrides_env_vars(monkeypatch):
    cli = click.Command("cli")

    monkeypatch.setenv("NO_COLOR", "1")
    with click.Context(cli):
        assert resolve_color_default() is False
    buf_true = io.StringIO()
    with click.Context(cli, color=True):
        assert resolve_color_default() is True
        click.secho("msg", fg="cyan", file=buf_true)
    assert "\\033[" in buf_true.getvalue()

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    with click.Context(cli):
        assert resolve_color_default() is True
    tty_false = _FakeTTYStream()
    with click.Context(cli, color=False):
        assert resolve_color_default() is False
        click.secho("msg", fg="cyan", file=tty_false)
    assert "\\033[" not in tty_false.getvalue()
    assert tty_false.getvalue().strip() == "msg"
''',
        },
        "task_05": {
            "filename": "test_feature_echo_table.py",
            "regression_files": [
                "tests/test_termui.py",
                "tests/test_imports.py",
            ],
            "code": '''from __future__ import annotations

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
    assert "\\033[" not in buf.getvalue()
    assert "UP" in buf.getvalue()

    @click.command()
    def status():
        click.echo_table([["api", "ready"]], headers=["Service", "State"], border="grid")

    runner = CliRunner()
    res = runner.invoke(status, [])
    assert res.exit_code == 0
    assert "+---------+-------+" in res.output
    assert "| api     | ready |" in res.output
''',
        },
    }


class TestGenerator:
    """Module E: Generates feature tests, regression test manifests, and Harbor test.sh."""

    def generate_tests(self, task_id: str) -> dict[str, Any]:
        specs = _feature_tests_by_task()
        if task_id not in specs:
            raise KeyError(f"No test spec for {task_id!r}")

        spec = specs[task_id]
        filename = spec["filename"]
        test_code = spec["code"]
        fail_to_pass = _extract_test_node_ids(filename, test_code)
        pass_to_pass = spec["regression_files"]

        test_sh = f'''#!/usr/bin/env bash
set -uo pipefail

APP_DIR="${{APP_DIR:-/app}}"
TESTS_DIR="${{TESTS_DIR:-/tests}}"
VERIFIER_DIR="${{VERIFIER_DIR:-/logs/verifier}}"
PYTHON_BIN="${{PYTHON_BIN:-python}}"

mkdir -p "$VERIFIER_DIR"
cd "$APP_DIR"

export PYTHONPATH="$APP_DIR/src${{PYTHONPATH:+:$PYTHONPATH}}"

"$PYTHON_BIN" - "$APP_DIR" "$TESTS_DIR" "$VERIFIER_DIR" "{filename}" <<'PY'
import json
import os
import pathlib
import shutil
import subprocess
import sys

app_dir = pathlib.Path(sys.argv[1])
tests_dir = pathlib.Path(sys.argv[2])
verifier_dir = pathlib.Path(sys.argv[3])
feature_test_file = tests_dir / sys.argv[4]
pass_to_pass_file = tests_dir / "pass_to_pass.json"

regression_targets = json.loads(pass_to_pass_file.read_text(encoding="utf-8"))

local_feat = app_dir / "tests" / feature_test_file.name
shutil.copy2(feature_test_file, local_feat)
env = dict(os.environ)
env["PYTHONPATH"] = str((app_dir / "src").resolve())
env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

try:
    feat_proc = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/{{feature_test_file.name}}", "-v", "--tb=short"],
        cwd=str(app_dir),
        env=env,
        capture_output=True,
        text=True,
    )
finally:
    local_feat.unlink(missing_ok=True)
print("=== FEATURE TESTS ===")
print(feat_proc.stdout)
if feat_proc.stderr:
    print(feat_proc.stderr, file=sys.stderr)

reg_proc = subprocess.run(
    [sys.executable, "-m", "pytest", *regression_targets, "-q", "--tb=short"],
    cwd=str(app_dir),
    env=env,
    capture_output=True,
    text=True,
)
print("=== REGRESSION TESTS ===")
print(reg_proc.stdout)
if reg_proc.stderr:
    print(reg_proc.stderr, file=sys.stderr)

reward = 1.0 if (feat_proc.returncode == 0 and reg_proc.returncode == 0) else 0.0

(verifier_dir / "reward.txt").write_text(
    "1\\n" if reward == 1.0 else "0\\n", encoding="utf-8"
)
(verifier_dir / "reward.json").write_text(
    json.dumps({{"reward": reward}}, indent=2), encoding="utf-8"
)
(verifier_dir / "verifier_details.json").write_text(
    json.dumps(
        {{
            "feature_returncode": feat_proc.returncode,
            "regression_returncode": reg_proc.returncode,
            "reward": reward,
            "feature_test_file": sys.argv[4],
            "regression_targets": regression_targets,
        }},
        indent=2,
    ),
    encoding="utf-8",
)
sys.exit(0 if reward == 1.0 else 1)
PY
'''
        return {
            "task_id": task_id,
            "feature_test_filename": filename,
            "feature_test_code": test_code,
            "fail_to_pass": fail_to_pass,
            "pass_to_pass": pass_to_pass,
            "test_sh": test_sh,
        }
