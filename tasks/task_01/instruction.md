# Feature Development Task: Option Mutual Exclusivity and Dependency Constraints (conflicts_with / requires)

**Repository:** `pallets/click`  
**Base Commit:** `08b803cf32ceb2ae6a772c62d5da42757a897d44`  
**Subsystem:** `parameter-validation`  
**Primary Target File(s):** `src/click/core.py`

## Problem Description

Click currently lacks declarative cross-option validation on click.Option. Developers must manually inspect ctx.params inside command callbacks to reject mutually exclusive flags (such as --json vs --csv or --quiet vs --verbose) or to enforce paired options (such as --ssl-cert requiring --ssl-key).

## Requirements

- Add optional `conflicts_with` and `requires` keyword arguments (sequences of parameter names) to `click.Option`.
- Validate option constraints in `Command.parse_args` after all parameters are parsed and resolved, skipping validation during `resilient_parsing`.
- Consider an option active/provided for `conflicts_with` only when its `ParameterSource` is `COMMANDLINE` or `ENVIRONMENT` (not `DEFAULT` or `DEFAULT_MAP`).
- For `requires`, when an option is provided via `COMMANDLINE` or `ENVIRONMENT`, raise `click.UsageError` if any required partner parameter was not supplied via `COMMANDLINE`, `ENVIRONMENT`, `DEFAULT_MAP`, or a truthy/non-None `DEFAULT`.
- Accept both Python parameter names (e.g. `'ssl_key'`) and CLI option spellings (e.g. `'--ssl-key'`), normalizing leading dashes and hyphens to underscores.
- Expose non-empty `conflicts_with` and `requires` lists in `Option.to_info_dict()` without altering existing keys when unset.

## Expected Behaviour

When mutually exclusive options are both explicitly supplied on the CLI or via environment variables, Click raises `click.UsageError` with a clear message naming the conflicting options. When an option with `requires` is supplied without its required dependency, Click raises `click.UsageError` naming the missing required parameter. Unprovided options with default values never trigger false conflicts.

## Acceptance Criteria

- AC1: Passing two options linked by `conflicts_with` on the command line fails with exit code 2 and `UsageError`.
- AC2: Passing only one of the mutually exclusive options succeeds even when the partner option has a default value (e.g., boolean flag default=False).
- AC3: Passing an option with `requires=[...]` without supplying all required partners raises `UsageError`.
- AC4: Passing an option with `requires=[...]` together with its required partner (via CLI, envvar, or default_map) succeeds.
- AC5: Constraint violations triggered via environment variables are detected using `ParameterSource.ENVIRONMENT`.
- AC6: `Option.to_info_dict()` includes `conflicts_with` and `requires` when configured and stays backward-compatible when omitted.
- AC7: `--help` and `resilient_parsing=True` bypass constraint errors.

## Feature Test Scenarios to Satisfy

- Mutually exclusive flags and value options raise UsageError when both passed.
- Asymmetric conflicts_with works regardless of option order on CLI.
- Default values do not trigger false mutual-exclusivity errors.
- requires raises UsageError when dependency missing and succeeds when dependency provided via CLI, envvar, or default_map.
- CLI-style '--foo-bar' constraint names normalize to 'foo_bar'.
- Envvar + CLI conflict detection.
- to_info_dict preserves default output and emits constraints when configured.
- --help works even if conflicting options are passed.

## Regression Constraints

- All existing tests in tests/test_options.py, tests/test_defaults.py, and tests/test_info_dict.py must pass.
- Keep all changes clean, typed, and isolated to the feature scope.
- Do not modify existing test files unless required; preserve backward compatibility.
