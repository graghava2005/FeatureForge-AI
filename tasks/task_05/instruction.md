# Feature Development Task: ANSI-Aware Terminal Table Formatting and Output (format_table / echo_table)

**Repository:** `pallets/click`  
**Base Commit:** `08b803cf32ceb2ae6a772c62d5da42757a897d44`  
**Subsystem:** `terminal-ui`  
**Primary Target File(s):** `src/click/termui.py`, `src/click/__init__.py`

## Problem Description

Click provides HelpFormatter.write_dl for two-column option lists, echo, style, and progressbar, but lacks a general-purpose tabular formatter for multi-column CLI output that respects ANSI escape widths, column alignments, borders, and truncation.

## Requirements

- Implement `format_table` and `echo_table` in `src/click/termui.py` and export both in `src/click/__init__.py`.
- Support `rows`, optional `headers`, `align` (`'left'`, `'right'`, `'center'`, or a per-column sequence), `border` (`'plain'`, `'simple'`, `'grid'`), `max_col_width: int | None = None`, and `padding: int = 1`.
- Use `click._compat.term_len` for width calculation so ANSI-styled cells align properly.
- Render `None` cells as empty strings `''` and normalize ragged rows to the maximum column count.
- Truncate unstyled text exceeding `max_col_width` with `'...'` (or exact slice when `max_col_width <= 3`), preserving ANSI-safe truncation via `unstyle` if needed.
- Validate `border`, `align`, `max_col_width` (< 1 raises `ValueError`), and `padding` (< 0 raises `ValueError`).
- `echo_table` forwards formatted text to `click.echo(..., file=file, nl=nl, err=err, color=color)`.

## Expected Behaviour

`click.format_table` returns deterministically aligned multi-column tables across `plain`, `simple`, and `grid` border styles, handles ANSI escape codes without misaligning columns, handles empty inputs cleanly, and `click.echo_table` prints the table through Click's echo pipeline (honoring `color` and streams).

## Acceptance Criteria

- AC1: `format_table` renders `'simple'` (default) with header, dashed separator line, and aligned data rows.
- AC2: `format_table` renders `'plain'` without separator lines and `'grid'` with `+---+` borders and `| cell |` pipes.
- AC3: `align` supports single string and per-column sequences (`['left', 'right', 'center']`).
- AC4: Cells containing `click.style(...)` ANSI codes align visually with unstyled cells using `term_len`.
- AC5: Ragged rows and `None` cells pad cleanly without raising IndexError.
- AC6: `max_col_width` truncates overly long cell values with `'...'` and raises `ValueError` if `< 1`.
- AC7: Invalid `border`, invalid `align`, or `padding < 0` raises `ValueError`.
- AC8: `click.echo_table` prints to `CliRunner` / custom `StringIO` stream and strips ANSI when `color=False`.

## Feature Test Scenarios to Satisfy

- Simple, plain, and grid border rendering.
- Left, right, center, and mixed per-column alignment.
- ANSI-styled cells alignment and echo_table color=False stripping.
- Ragged rows, None cells, empty rows with headers, empty rows without headers.
- max_col_width truncation and validation errors for invalid args.
- CliRunner integration test for CLI command using click.echo_table.

## Regression Constraints

- All existing tests in tests/test_termui.py and tests/test_imports.py must pass.
- Keep all changes clean, typed, and isolated to the feature scope.
- Do not modify existing test files unless required; preserve backward compatibility.
