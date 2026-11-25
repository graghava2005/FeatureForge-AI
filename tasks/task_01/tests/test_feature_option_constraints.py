from __future__ import annotations

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
