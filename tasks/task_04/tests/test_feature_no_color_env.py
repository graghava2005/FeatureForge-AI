from __future__ import annotations

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
    assert tty.getvalue() == "hello\n"


def test_empty_no_color_has_no_effect(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "")
    monkeypatch.delenv("FORCE_COLOR", raising=False)

    assert resolve_color_default() is None
    tty = _FakeTTYStream()
    assert should_strip_ansi(tty, resolve_color_default(None)) is False

    click.secho("hello", fg="red", file=tty)
    assert "\033[" in tty.getvalue()

    # Empty NO_COLOR must not block FORCE_COLOR
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert resolve_color_default() is True
    buf = io.StringIO()
    click.secho("hello", fg="red", file=buf)
    assert "\033[" in buf.getvalue()


def test_force_color_enables_color_on_non_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert resolve_color_default() is True
    buf = io.StringIO()
    assert should_strip_ansi(buf, resolve_color_default(None)) is False

    click.secho("forced", fg="green", file=buf)
    assert "\033[" in buf.getvalue()


def test_force_color_zero_or_false_does_not_force(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    for val in ("0", "false", "FALSE"):
        monkeypatch.setenv("FORCE_COLOR", val)
        assert resolve_color_default() is None
        buf = io.StringIO()
        click.secho("plain", fg="green", file=buf)
        assert "\033[" not in buf.getvalue()

    monkeypatch.setenv("FORCE_COLOR", "always")
    assert resolve_color_default() is True
    buf_active = io.StringIO()
    click.secho("colored", fg="green", file=buf_active)
    assert "\033[" in buf_active.getvalue()


def test_no_color_overrides_force_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "true")
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert resolve_color_default() is False
    tty = _FakeTTYStream()
    click.secho("muted", fg="yellow", file=tty)
    assert tty.getvalue() == "muted\n"


def test_explicit_color_argument_overrides_env_vars(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert resolve_color_default() is False
    buf1 = io.StringIO()
    click.secho("forced-explicit", fg="blue", file=buf1, color=True)
    assert "\033[" in buf1.getvalue()

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert resolve_color_default() is True
    buf2 = _FakeTTYStream()
    click.secho("stripped-explicit", fg="blue", file=buf2, color=False)
    assert buf2.getvalue() == "stripped-explicit\n"


def test_context_color_overrides_env_vars(monkeypatch):
    cli = click.Command("cli")

    monkeypatch.setenv("NO_COLOR", "1")
    with click.Context(cli):
        assert resolve_color_default() is False
    buf_true = io.StringIO()
    with click.Context(cli, color=True):
        assert resolve_color_default() is True
        click.secho("msg", fg="cyan", file=buf_true)
    assert "\033[" in buf_true.getvalue()

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    with click.Context(cli):
        assert resolve_color_default() is True
    tty_false = _FakeTTYStream()
    with click.Context(cli, color=False):
        assert resolve_color_default() is False
        click.secho("msg", fg="cyan", file=tty_false)
    assert "\033[" not in tty_false.getvalue()
    assert tty_false.getvalue().strip() == "msg"
