# Feature Development Task: Standard NO_COLOR and FORCE_COLOR Environment Variable Resolution

**Repository:** `pallets/click`  
**Base Commit:** `08b803cf32ceb2ae6a772c62d5da42757a897d44`  
**Subsystem:** `terminal-color`  
**Primary Target File(s):** `src/click/globals.py`, `src/click/_compat.py`

## Problem Description

Modern CLI tools are expected to honor the cross-tool NO_COLOR (no-color.org) and FORCE_COLOR standards automatically. Currently Click only checks stream.isatty() when color=None, ignoring NO_COLOR and FORCE_COLOR environment variables.

## Requirements

- Update `resolve_color_default(color: bool | None = None)` in `src/click/globals.py` and `should_strip_ansi` in `src/click/_compat.py` to honor `NO_COLOR` and `FORCE_COLOR`.
- Preserve precedence: explicit `color=True`/`color=False` argument > explicit `ctx.color` (`True`/`False`) > `NO_COLOR` > `FORCE_COLOR` > TTY auto-detection.
- Per no-color.org, any non-empty `NO_COLOR` environment variable (`os.environ.get('NO_COLOR', '') != ''`) disables ANSI color when `color` and `ctx.color` are `None`.
- When `NO_COLOR` is unset or empty, a non-empty `FORCE_COLOR` value other than `'0'` (case-insensitive `'false'` also treated as off) enables ANSI color even on non-TTY streams.
- Ensure `NO_COLOR` takes precedence over `FORCE_COLOR` if both are set.

## Expected Behaviour

When `NO_COLOR=1` is present in the environment and neither `color` nor `ctx.color` is explicitly set, `click.echo` / `click.secho` strip ANSI codes even for TTY streams. When `FORCE_COLOR=1` is set (and `NO_COLOR` is empty/unset), `click.echo` / `click.secho` preserve ANSI codes even when writing to non-TTY streams like `StringIO` or `CliRunner`. Explicit `color=True` or `color=False` always wins.

## Acceptance Criteria

- AC1: With `NO_COLOR=1`, `resolve_color_default()` returns `False` and `should_strip_ansi(tty_stream)` returns `True`.
- AC2: With `NO_COLOR=''` (empty string), `NO_COLOR` has no effect per the no-color.org spec.
- AC3: With `FORCE_COLOR=1` and no `NO_COLOR`, `resolve_color_default()` returns `True` and `click.secho` preserves ANSI escapes on non-TTY streams.
- AC4: With `FORCE_COLOR='0'` or `FORCE_COLOR='false'`, color is not forced.
- AC5: When both `NO_COLOR=1` and `FORCE_COLOR=1` are set, `NO_COLOR` wins and strips ANSI codes.
- AC6: Explicit `color=True` overrides `NO_COLOR=1`, and explicit `color=False` overrides `FORCE_COLOR=1`.
- AC7: Explicit `ctx.color=True` / `ctx.color=False` overrides environment variables.

## Feature Test Scenarios to Satisfy

- NO_COLOR=1 strips ANSI output in echo/secho and CliRunner(color=None) or TTY mock.
- Empty NO_COLOR='' leaves TTY auto-detection intact.
- FORCE_COLOR=1 preserves ANSI codes in StringIO and CliRunner.
- FORCE_COLOR='0' does not force color.
- NO_COLOR overrides FORCE_COLOR when both set.
- Explicit color=True/False and ctx.color=True/False override env vars.

## Regression Constraints

- All existing tests in tests/test_basic.py, tests/test_termui.py, tests/test_compat.py, and tests/test_context.py must pass.
- Keep all changes clean, typed, and isolated to the feature scope.
- Do not modify existing test files unless required; preserve backward compatibility.
