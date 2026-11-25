# Feature Development Task: Command and Subcommand Aliases in Group Dispatch and Help Output

**Repository:** `pallets/click`  
**Base Commit:** `08b803cf32ceb2ae6a772c62d5da42757a897d44`  
**Subsystem:** `command-routing`  
**Primary Target File(s):** `src/click/core.py`

## Problem Description

In multi-command CLIs built with `click.Group`, developers frequently want short aliases for common subcommands (for example `co` for `checkout` or `rm` for `remove`) without subclassing `Group` or duplicating command registrations.

## Requirements

- Add an optional `aliases: cabc.Sequence[str] | None = None` parameter to `click.Command.__init__` (inherited by `Group` and forwarded automatically by `@click.command` and `@group.command`).
- Store normalized unique aliases as a tuple on `cmd.aliases`.
- Extend `Group.add_command` to reject alias collisions against existing command names or aliases in the group with `ValueError`.
- Update `Group.resolve_command` so invoking an alias resolves to the canonical command and sets `cmd_name` to the canonical registered command name (respecting `ctx.token_normalize_func`).
- Update `Group.format_commands` so commands with aliases display as `name (alias1, alias2)` in the `--help` Commands section.
- Include `aliases` in `Command.to_info_dict()` only when `self.aliases` is non-empty.

## Expected Behaviour

Subcommands registered with `aliases=['co', 'chk']` can be invoked by their canonical name or any alias, executing with `ctx.info_name` / `ctx.invoked_subcommand` set to the canonical name. `--help` lists aliases next to the command name, and duplicate/colliding aliases raise `ValueError` at registration.

## Acceptance Criteria

- AC1: `@group.command(aliases=['d', 'dep'])` allows invoking the command via `cli d` and `cli dep`.
- AC2: Invoking via an alias sets `ctx.invoked_subcommand` and `ctx.info_name` to the canonical command name.
- AC3: `Group --help` renders aliases in parentheses next to the canonical command name.
- AC4: Registering a command whose alias collides with an existing command name or alias raises `ValueError`.
- AC5: Chained groups (`chain=True`) resolve aliased subcommands in sequence.
- AC6: `token_normalize_func` applies cleanly when matching aliases case-insensitively.
- AC7: `Command.to_info_dict()` remains backward-compatible when aliases are unset and includes `aliases` when set.

## Feature Test Scenarios to Satisfy

- Invoke subcommand using multiple aliases and canonical name.
- Verify ctx.invoked_subcommand and ctx.info_name resolve to canonical command name.
- Verify Group --help output formats aliases and accounts for column width.
- Verify ValueError on alias collision with existing command or alias.
- Verify chained group invocation with aliases.
- Verify case-insensitive alias matching via token_normalize_func.
- Verify unknown command still raises NoSuchCommand.

## Regression Constraints

- All existing tests in tests/test_commands.py, tests/test_chain.py, tests/test_normalization.py, and tests/test_info_dict.py must pass.
- Keep all changes clean, typed, and isolated to the feature scope.
- Do not modify existing test files unless required; preserve backward compatibility.
