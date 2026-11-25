from __future__ import annotations

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
