from __future__ import annotations

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
