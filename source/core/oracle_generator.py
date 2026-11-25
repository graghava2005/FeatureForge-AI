"""Module D: Reference Implementation Patch Generator for pallets/click tasks."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from config.settings import TARGET_REPO_DIR


def _replace_once(content: str, target: str, replacement: str, label: str) -> str:
    count = content.count(target)
    if count != 1:
        raise ValueError(f"Expected exactly 1 occurrence of anchor {label!r}, found {count}.")
    return content.replace(target, replacement, 1)


def _unified_diff(rel_path: str, old_text: str, new_text: str) -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
        lineterm="\n",
    )
    return "".join(diff)


class OracleGenerator:
    """Builds clean, isolated unified git diffs and solve.sh for each approved task."""

    def __init__(self, repo_dir: Path = TARGET_REPO_DIR) -> None:
        self.repo_dir = Path(repo_dir)

    def _read_repo_file(self, rel_path: str) -> str:
        return (self.repo_dir / rel_path).read_text(encoding="utf-8")

    def _patch_task_01_option_constraints(self) -> tuple[str, list[str]]:
        rel = "src/click/core.py"
        orig = self._read_repo_file(rel)
        updated = orig

        # 1. Add constraint validation call in Command.parse_args
        updated = _replace_once(
            updated,
            "        ctx.args = args\n        ctx._opt_prefixes.update(parser._opt_prefixes)\n        return args",
            "        if not ctx.resilient_parsing:\n"
            "            self._validate_option_constraints(ctx)\n\n"
            "        ctx.args = args\n        ctx._opt_prefixes.update(parser._opt_prefixes)\n        return args",
            "Command.parse_args constraint validation hook",
        )

        # 2. Add _validate_option_constraints method on Command right after parse_args
        updated = _replace_once(
            updated,
            "        ctx.args = args\n        ctx._opt_prefixes.update(parser._opt_prefixes)\n        return args\n\n    def invoke(self, ctx: Context) -> t.Any:",
            "        ctx.args = args\n        ctx._opt_prefixes.update(parser._opt_prefixes)\n        return args\n\n"
            "    def _validate_option_constraints(self, ctx: Context) -> None:\n"
            "        params_by_name: dict[str, Parameter] = {\n"
            "            param.name: param\n"
            "            for param in self.get_params(ctx)\n"
            "            if param.name is not None\n"
            "        }\n"
            "        explicit_sources = {\n"
            "            ParameterSource.COMMANDLINE,\n"
            "            ParameterSource.ENVIRONMENT,\n"
            "        }\n\n"
            "        def _is_explicit(param_name: str) -> bool:\n"
            "            return ctx.get_parameter_source(param_name) in explicit_sources\n\n"
            "        def _is_satisfied(param_name: str) -> bool:\n"
            "            source = ctx.get_parameter_source(param_name)\n"
            "            if source in (\n"
            "                ParameterSource.COMMANDLINE,\n"
            "                ParameterSource.ENVIRONMENT,\n"
            "                ParameterSource.DEFAULT_MAP,\n"
            "            ):\n"
            "                return True\n"
            "            if source == ParameterSource.DEFAULT:\n"
            "                val = ctx.params.get(param_name)\n"
            "                return val is not None and val is not False and val != () and val != []\n"
            "            return False\n\n"
            "        for param in self.get_params(ctx):\n"
            "            if not isinstance(param, Option) or param.name is None:\n"
            "                continue\n"
            "            if not _is_explicit(param.name):\n"
            "                continue\n\n"
            "            for other_name in param.conflicts_with:\n"
            "                if other_name != param.name and _is_explicit(other_name):\n"
            "                    other_param = params_by_name.get(other_name)\n"
            "                    other_hint = (\n"
            "                        other_param.get_error_hint(ctx)\n"
            "                        if other_param is not None\n"
            "                        else f\"'{other_name}'\"\n"
            "                    )\n"
            "                    raise UsageError(\n"
            "                        _(\"Illegal usage: {opt} is mutually exclusive with {other}.\").format(\n"
            "                            opt=param.get_error_hint(ctx),\n"
            "                            other=other_hint,\n"
            "                        ),\n"
            "                        ctx=ctx,\n"
            "                    )\n\n"
            "            for req_name in param.requires:\n"
            "                if req_name != param.name and not _is_satisfied(req_name):\n"
            "                    req_param = params_by_name.get(req_name)\n"
            "                    req_hint = (\n"
            "                        req_param.get_error_hint(ctx)\n"
            "                        if req_param is not None\n"
            "                        else f\"'{req_name}'\"\n"
            "                    )\n"
            "                    raise UsageError(\n"
            "                        _(\"Illegal usage: {opt} requires {req}.\").format(\n"
            "                            opt=param.get_error_hint(ctx),\n"
            "                            req=req_hint,\n"
            "                        ),\n"
            "                        ctx=ctx,\n"
            "                    )\n\n"
            "    def invoke(self, ctx: Context) -> t.Any:",
            "Command._validate_option_constraints method",
        )

        # 3. Extend Option attributes & __init__
        updated = _replace_once(
            updated,
            "    show_choices: bool\n    show_envvar: bool\n\n    def __init__(",
            "    show_choices: bool\n    show_envvar: bool\n    conflicts_with: tuple[str, ...]\n    requires: tuple[str, ...]\n\n    def __init__(",
            "Option class annotations",
        )

        updated = _replace_once(
            updated,
            "        show_envvar: bool = False,\n        deprecated: bool | str = False,\n        **attrs: t.Any,",
            "        show_envvar: bool = False,\n        deprecated: bool | str = False,\n        conflicts_with: cabc.Sequence[str] | None = None,\n        requires: cabc.Sequence[str] | None = None,\n        **attrs: t.Any,",
            "Option.__init__ signature",
        )

        updated = _replace_once(
            updated,
            "        self.show_choices = show_choices\n        self.show_envvar = show_envvar\n\n        # Phase 5: validate. Raises on illegal kwarg combinations.",
            "        self.show_choices = show_choices\n        self.show_envvar = show_envvar\n"
            "        self.conflicts_with = tuple(\n"
            "            dict.fromkeys(self._normalize_constraint_name(n) for n in (conflicts_with or ()))\n"
            "        )\n"
            "        self.requires = tuple(\n"
            "            dict.fromkeys(self._normalize_constraint_name(n) for n in (requires or ()))\n"
            "        )\n\n"
            "        # Phase 5: validate. Raises on illegal kwarg combinations.",
            "Option.__init__ assign constraints",
        )

        # 4. Add _normalize_constraint_name and conditional to_info_dict fields
        updated = _replace_once(
            updated,
            "            count=self.count,\n            hidden=self.hidden,\n        )\n        return info_dict",
            "            count=self.count,\n            hidden=self.hidden,\n        )\n"
            "        if self.conflicts_with:\n"
            "            info_dict[\"conflicts_with\"] = list(self.conflicts_with)\n"
            "        if self.requires:\n"
            "            info_dict[\"requires\"] = list(self.requires)\n"
            "        return info_dict\n\n"
            "    @staticmethod\n"
            "    def _normalize_constraint_name(name: str) -> str:\n"
            "        return name.strip().lstrip(\"-\").replace(\"-\", \"_\")",
            "Option.to_info_dict and constraint normalizer",
        )

        return _unified_diff(rel, orig, updated), [rel]

    def _patch_task_02_command_aliases(self) -> tuple[str, list[str]]:
        rel = "src/click/core.py"
        orig = self._read_repo_file(rel)
        updated = orig

        # 1. Command annotations, __init__, to_info_dict
        updated = _replace_once(
            updated,
            "    hidden: bool\n    deprecated: bool | str\n\n    def __init__(",
            "    hidden: bool\n    deprecated: bool | str\n    aliases: tuple[str, ...]\n\n    def __init__(",
            "Command annotations aliases",
        )

        updated = _replace_once(
            updated,
            "        hidden: bool = False,\n        deprecated: bool | str = False,\n    ) -> None:",
            "        hidden: bool = False,\n        deprecated: bool | str = False,\n        aliases: cabc.Sequence[str] | None = None,\n    ) -> None:",
            "Command.__init__ aliases arg",
        )

        updated = _replace_once(
            updated,
            "        self.hidden = hidden\n        self.deprecated = deprecated\n\n    def to_info_dict(self, ctx: Context) -> dict[str, t.Any]:",
            "        self.hidden = hidden\n        self.deprecated = deprecated\n"
            "        self.aliases = tuple(\n"
            "            dict.fromkeys(a for a in (aliases or ()) if a and a != name)\n"
            "        )\n\n"
            "    def to_info_dict(self, ctx: Context) -> dict[str, t.Any]:",
            "Command.__init__ set aliases",
        )

        updated = _replace_once(
            updated,
            "            \"hidden\": self.hidden,\n            \"deprecated\": self.deprecated,\n        }",
            "            \"hidden\": self.hidden,\n            \"deprecated\": self.deprecated,\n"
            "            **({\"aliases\": list(self.aliases)} if self.aliases else {}),\n        }",
            "Command.to_info_dict aliases",
        )

        # 2. Group.add_command alias collision checks
        updated = _replace_once(
            updated,
            "        _check_nested_chain(self, name, cmd, register=True)\n        self.commands[name] = cmd",
            "        _check_nested_chain(self, name, cmd, register=True)\n"
            "        for existing_name, existing_cmd in self.commands.items():\n"
            "            if existing_name == name:\n"
            "                continue\n"
            "            if name in existing_cmd.aliases:\n"
            "                raise ValueError(\n"
            "                    f\"Command name {name!r} collides with alias of {existing_name!r}.\"\n"
            "                )\n"
            "            for alias in cmd.aliases:\n"
            "                if alias == existing_name or alias in existing_cmd.aliases:\n"
            "                    raise ValueError(\n"
            "                        f\"Alias {alias!r} for command {name!r} collides with {existing_name!r}.\"\n"
            "                    )\n"
            "        self.commands[name] = cmd",
            "Group.add_command alias collision check",
        )

        # 3. Group.format_commands displays aliases in parentheses
        updated = _replace_once(
            updated,
            "            commands.append((subcommand, cmd))\n\n        # allow for 3 times the default spacing\n        if len(commands):\n            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)\n\n            rows = []\n            for subcommand, cmd in commands:\n                help = cmd.get_short_help_str(limit)\n                rows.append((subcommand, help))",
            "            display_name = subcommand\n"
            "            if cmd.aliases:\n"
            "                display_name = f\"{subcommand} ({', '.join(cmd.aliases)})\"\n"
            "            commands.append((display_name, cmd))\n\n"
            "        # allow for 3 times the default spacing\n"
            "        if len(commands):\n"
            "            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)\n\n"
            "            rows = []\n"
            "            for subcommand, cmd in commands:\n"
            "                help = cmd.get_short_help_str(limit)\n"
            "                rows.append((subcommand, help))",
            "Group.format_commands show aliases",
        )

        # 4. Group.resolve_command resolves aliases to canonical command name
        updated = _replace_once(
            updated,
            "        # If we can't find the command but there is a normalization\n"
            "        # function available, we try with that one.\n"
            "        if cmd is None and ctx.token_normalize_func is not None:\n"
            "            cmd_name = ctx.token_normalize_func(cmd_name)\n"
            "            cmd = self.get_command(ctx, cmd_name)",
            "        # If we can't find the command directly, try alias resolution.\n"
            "        if cmd is None:\n"
            "            resolved = self._resolve_alias(ctx, cmd_name, normalize=False)\n"
            "            if resolved is not None:\n"
            "                cmd_name, cmd = resolved\n\n"
            "        # If we can't find the command but there is a normalization\n"
            "        # function available, we try with that one (including aliases).\n"
            "        if cmd is None and ctx.token_normalize_func is not None:\n"
            "            norm_name = ctx.token_normalize_func(cmd_name)\n"
            "            cmd = self.get_command(ctx, norm_name)\n"
            "            if cmd is not None:\n"
            "                cmd_name = norm_name\n"
            "            else:\n"
            "                resolved = self._resolve_alias(ctx, norm_name, normalize=True)\n"
            "                if resolved is not None:\n"
            "                    cmd_name, cmd = resolved",
            "Group.resolve_command alias lookup",
        )

        # Add helper _resolve_alias right before resolve_command
        updated = _replace_once(
            updated,
            "    def resolve_command(",
            "    def _resolve_alias(\n"
            "        self, ctx: Context, candidate: str, *, normalize: bool\n"
            "    ) -> tuple[str, Command] | None:\n"
            "        for sub_name in self.list_commands(ctx):\n"
            "            sub_cmd = self.get_command(ctx, sub_name)\n"
            "            if sub_cmd is None:\n"
            "                continue\n"
            "            for alias in sub_cmd.aliases:\n"
            "                target = (\n"
            "                    ctx.token_normalize_func(alias)\n"
            "                    if normalize and ctx.token_normalize_func is not None\n"
            "                    else alias\n"
            "                )\n"
            "                if target == candidate:\n"
            "                    return sub_name, sub_cmd\n"
            "        return None\n\n"
            "    def resolve_command(",
            "Group._resolve_alias helper",
        )

        return _unified_diff(rel, orig, updated), [rel]

    def _patch_task_03_bytesize_type(self) -> tuple[str, list[str]]:
        rel_types = "src/click/types.py"
        rel_init = "src/click/__init__.py"
        orig_types = self._read_repo_file(rel_types)
        orig_init = self._read_repo_file(rel_init)

        # Add re, math imports in types.py
        updated_types = _replace_once(
            orig_types,
            "import enum\nimport os\nimport stat\nimport sys",
            "import enum\nimport math\nimport os\nimport re\nimport stat\nimport sys",
            "types.py imports math and re",
        )

        bytesize_code = '''

class ByteSizeInfoDict(ParamTypeInfoDict):
    min: int | None
    max: int | None
    binary: bool


class ByteSize(ParamType[int]):
    """Parse human-readable byte sizes such as ``512B``, ``10MiB``, or ``2.5 GB``
    into an integer number of bytes.

    :param min: Optional inclusive minimum size in bytes.
    :param max: Optional inclusive maximum size in bytes.
    :param binary: When ``True`` (default), short suffixes like ``KB`` and
        ``MB`` use powers of 1024. When ``False``, short/SI suffixes use powers
        of 1000 while explicit IEC suffixes (``KiB``, ``MiB``, ...) always use
        powers of 1024.
    """

    name = "bytesize"

    _PATTERN = re.compile(
        r"^\\s*([+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?)\\s*([a-zA-Z]*)\\s*$"
    )
    _IEC_MULTIPLIERS: dict[str, int] = {
        "": 1,
        "b": 1,
        "kib": 1024,
        "mib": 1024**2,
        "gib": 1024**3,
        "tib": 1024**4,
        "pib": 1024**5,
    }
    _SHORT_PREFIX_POWER: dict[str, int] = {
        "k": 1,
        "kb": 1,
        "m": 2,
        "mb": 2,
        "g": 3,
        "gb": 3,
        "t": 4,
        "tb": 4,
        "p": 5,
        "pb": 5,
    }

    def __init__(
        self,
        *,
        min: int | None = None,
        max: int | None = None,
        binary: bool = True,
    ) -> None:
        if min is not None and min < 0:
            raise ValueError("'min' must be non-negative.")
        if max is not None and max < 0:
            raise ValueError("'max' must be non-negative.")
        if min is not None and max is not None and min > max:
            raise ValueError("'min' cannot be greater than 'max'.")
        self.min = min
        self.max = max
        self.binary = binary

    def to_info_dict(self) -> ByteSizeInfoDict:
        return {
            "min": self.min,
            "max": self.max,
            "binary": self.binary,
            **super().to_info_dict(),
        }

    def get_metavar(self, param: Parameter, ctx: Context) -> str | None:
        if self.min is None and self.max is None:
            return "[BYTESIZE]"
        bounds = f"{self.min if self.min is not None else 0}..{self.max if self.max is not None else ''}"
        return f"[BYTESIZE:{bounds}]"

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> int:
        if isinstance(value, bool):
            self.fail(
                _("{value!r} is not a valid byte size.").format(value=value),
                param=param,
                ctx=ctx,
            )

        if isinstance(value, int):
            result = value
        elif isinstance(value, str):
            match = self._PATTERN.match(value)
            if match is None:
                self.fail(
                    _("{value!r} is not a valid byte size.").format(value=value),
                    param=param,
                    ctx=ctx,
                )
            num_str, unit_raw = match.groups()
            try:
                num = float(num_str)
            except ValueError:
                self.fail(
                    _("{value!r} is not a valid byte size.").format(value=value),
                    param=param,
                    ctx=ctx,
                )
            if not math.isfinite(num) or num < 0:
                self.fail(
                    _("{value!r} must be a non-negative finite byte size.").format(
                        value=value
                    ),
                    param=param,
                    ctx=ctx,
                )

            unit = unit_raw.lower()
            if unit in self._IEC_MULTIPLIERS:
                factor = self._IEC_MULTIPLIERS[unit]
            elif unit in self._SHORT_PREFIX_POWER:
                base = 1024 if self.binary else 1000
                factor = base ** self._SHORT_PREFIX_POWER[unit]
            else:
                self.fail(
                    _("Unknown byte size unit {unit!r} in {value!r}.").format(
                        unit=unit_raw, value=value
                    ),
                    param=param,
                    ctx=ctx,
                )

            result = int(num * factor)
        else:
            self.fail(
                _("{value!r} is not a valid byte size.").format(value=value),
                param=param,
                ctx=ctx,
            )

        if result < 0:
            self.fail(
                _("{value!r} must be a non-negative byte size.").format(value=value),
                param=param,
                ctx=ctx,
            )
        if self.min is not None and result < self.min:
            self.fail(
                _("{result} bytes is smaller than the minimum of {min} bytes.").format(
                    result=result, min=self.min
                ),
                param=param,
                ctx=ctx,
            )
        if self.max is not None and result > self.max:
            self.fail(
                _("{result} bytes is larger than the maximum of {max} bytes.").format(
                    result=result, max=self.max
                ),
                param=param,
                ctx=ctx,
            )
        return result

    def __repr__(self) -> str:
        return f"ByteSize(min={self.min!r}, max={self.max!r}, binary={self.binary!r})"
'''

        updated_types = _replace_once(
            updated_types,
            "class OptionHelpExtra(t.TypedDict, total=False):",
            bytesize_code.lstrip("\n") + "\n\nclass OptionHelpExtra(t.TypedDict, total=False):",
            "types.py add ByteSize",
        )

        updated_init = _replace_once(
            orig_init,
            "from .types import BOOL as BOOL\nfrom .types import Choice as Choice",
            "from .types import BOOL as BOOL\nfrom .types import ByteSize as ByteSize\nfrom .types import Choice as Choice",
            "__init__.py export ByteSize",
        )

        patch = _unified_diff(rel_types, orig_types, updated_types) + _unified_diff(
            rel_init, orig_init, updated_init
        )
        return patch, [rel_types, rel_init]

    def _patch_task_04_no_color_env(self) -> tuple[str, list[str]]:
        rel_compat = "src/click/_compat.py"
        rel_globals = "src/click/globals.py"
        orig_compat = self._read_repo_file(rel_compat)
        orig_globals = self._read_repo_file(rel_globals)

        # Add _resolve_env_color in _compat.py and integrate into should_strip_ansi
        updated_compat = _replace_once(
            orig_compat,
            "def should_strip_ansi(\n"
            "    stream: t.IO[t.Any] | None = None, color: bool | None = None\n"
            ") -> bool:\n"
            "    if color is None:\n"
            "        if stream is None:\n"
            "            stream = sys.stdin\n"
            "        elif hasattr(stream, \"color\"):\n"
            "            # ._termui_impl._PagerWriter handles stripping ansi itself,\n"
            "            # so we don't need to strip it here\n"
            "            return False\n"
            "        return not isatty(stream) and not _is_jupyter_kernel_output(stream)\n"
            "    return not color",
            "def _resolve_env_color() -> bool | None:\n"
            "    \"\"\"Return ``False`` when ``NO_COLOR`` is non-empty, ``True`` when\n"
            "    ``FORCE_COLOR`` is active, or ``None`` to defer to TTY detection.\n"
            "    \"\"\"\n"
            "    if os.environ.get(\"NO_COLOR\", \"\"):\n"
            "        return False\n"
            "    force_color = os.environ.get(\"FORCE_COLOR\", \"\")\n"
            "    if force_color and force_color.strip().lower() not in {\"0\", \"false\"}:\n"
            "        return True\n"
            "    return None\n\n\n"
            "def should_strip_ansi(\n"
            "    stream: t.IO[t.Any] | None = None, color: bool | None = None\n"
            ") -> bool:\n"
            "    if color is None:\n"
            "        if stream is not None and hasattr(stream, \"color\"):\n"
            "            # ._termui_impl._PagerWriter handles stripping ansi itself,\n"
            "            # so we don't need to strip it here\n"
            "            return False\n"
            "        env_color = _resolve_env_color()\n"
            "        if env_color is not None:\n"
            "            return not env_color\n"
            "        if stream is None:\n"
            "            stream = sys.stdin\n"
            "        return not isatty(stream) and not _is_jupyter_kernel_output(stream)\n"
            "    return not color",
            "_compat.py NO_COLOR/FORCE_COLOR",
        )

        # Update globals.py resolve_color_default
        updated_globals = _replace_once(
            orig_globals,
            "from threading import local\n",
            "from threading import local\n\nfrom ._compat import _resolve_env_color\n",
            "globals.py import _resolve_env_color",
        )

        updated_globals = _replace_once(
            updated_globals,
            "    ctx = get_current_context(silent=True)\n\n    if ctx is not None:\n        return ctx.color\n\n    return None",
            "    ctx = get_current_context(silent=True)\n\n    if ctx is not None and ctx.color is not None:\n        return ctx.color\n\n    return _resolve_env_color()",
            "globals.py resolve_color_default env fallback",
        )

        patch = _unified_diff(rel_compat, orig_compat, updated_compat) + _unified_diff(
            rel_globals, orig_globals, updated_globals
        )
        return patch, [rel_compat, rel_globals]

    def _patch_task_05_echo_table(self) -> tuple[str, list[str]]:
        rel_termui = "src/click/termui.py"
        rel_init = "src/click/__init__.py"
        orig_termui = self._read_repo_file(rel_termui)
        orig_init = self._read_repo_file(rel_init)

        updated_termui = _replace_once(
            orig_termui,
            "from ._compat import isatty\nfrom ._compat import strip_ansi",
            "from ._compat import isatty\nfrom ._compat import strip_ansi\nfrom ._compat import term_len",
            "termui.py import term_len",
        )

        table_code = '''

def _align_cell(text: str, width: int, alignment: str) -> str:
    visible = term_len(text)
    pad = max(0, width - visible)
    if alignment == "left":
        return text + (" " * pad)
    if alignment == "right":
        return (" " * pad) + text
    if alignment == "center":
        left_pad = pad // 2
        right_pad = pad - left_pad
        return (" " * left_pad) + text + (" " * right_pad)
    raise ValueError(
        f"Invalid alignment {alignment!r}; expected 'left', 'right', or 'center'."
    )


def _truncate_cell(text: str, max_col_width: int | None) -> str:
    if max_col_width is None:
        return text
    if term_len(text) <= max_col_width:
        return text
    plain = strip_ansi(text)
    if max_col_width <= 3:
        return plain[:max_col_width]
    return plain[: max_col_width - 3] + "..."


def format_table(
    rows: cabc.Iterable[cabc.Sequence[t.Any]],
    headers: cabc.Sequence[str] | None = None,
    *,
    align: cabc.Sequence[t.Literal["left", "right", "center"]]
    | t.Literal["left", "right", "center"] = "left",
    border: t.Literal["plain", "simple", "grid"] = "simple",
    max_col_width: int | None = None,
    padding: int = 1,
) -> str:
    """Format tabular data with ANSI-aware column alignment and optional borders.

    :param rows: Iterable of row sequences. ``None`` cells render as ``""``.
    :param headers: Optional column header sequence.
    :param align: Alignment string (``'left'``, ``'right'``, ``'center'``) or
        per-column sequence of alignments.
    :param border: Border style: ``'plain'``, ``'simple'`` (default), or ``'grid'``.
    :param max_col_width: Optional maximum visible column width; longer values
        are truncated with ``'...'``.
    :param padding: Number of spaces around cell content in ``'grid'`` style
        and minimum gap multiplier between columns.
    """
    if border not in {"plain", "simple", "grid"}:
        raise ValueError(
            f"Invalid border style {border!r}; expected 'plain', 'simple', or 'grid'."
        )
    if max_col_width is not None and max_col_width < 1:
        raise ValueError("'max_col_width' must be at least 1.")
    if padding < 0:
        raise ValueError("'padding' must be non-negative.")

    raw_rows = [["" if cell is None else str(cell) for cell in row] for row in rows]
    header_row = ["" if h is None else str(h) for h in headers] if headers is not None else None

    col_count = max(
        [len(header_row) if header_row is not None else 0, *(len(r) for r in raw_rows)]
    )
    if col_count == 0:
        return ""

    if header_row is not None:
        header_row = [
            _truncate_cell(c, max_col_width)
            for c in header_row + [""] * (col_count - len(header_row))
        ]

    norm_rows = [
        [_truncate_cell(c, max_col_width) for c in row + [""] * (col_count - len(row))]
        for row in raw_rows
    ]

    if isinstance(align, str):
        alignments = [align] * col_count
    else:
        alignments = list(align)
        if len(alignments) < col_count:
            alignments.extend(["left"] * (col_count - len(alignments)))
        elif len(alignments) > col_count:
            alignments = alignments[:col_count]

    for a in alignments:
        if a not in {"left", "right", "center"}:
            raise ValueError(
                f"Invalid alignment {a!r}; expected 'left', 'right', or 'center'."
            )

    all_rows = ([header_row] if header_row is not None else []) + norm_rows
    widths = [
        max((term_len(row[i]) for row in all_rows), default=0)
        for i in range(col_count)
    ]

    pad_str = " " * padding
    lines: list[str] = []

    if border == "grid":
        sep = "+" + "+".join("-" * (w + 2 * padding) for w in widths) + "+"
        lines.append(sep)
        if header_row is not None:
            cells = [
                f"{pad_str}{_align_cell(header_row[i], widths[i], alignments[i])}{pad_str}"
                for i in range(col_count)
            ]
            lines.append("|" + "|".join(cells) + "|")
            lines.append(sep)
        for row in norm_rows:
            cells = [
                f"{pad_str}{_align_cell(row[i], widths[i], alignments[i])}{pad_str}"
                for i in range(col_count)
            ]
            lines.append("|" + "|".join(cells) + "|")
        lines.append(sep)
        return "\\n".join(lines)

    col_gap = " " * max(2, padding * 2)
    if header_row is not None:
        lines.append(
            col_gap.join(
                _align_cell(header_row[i], widths[i], alignments[i])
                for i in range(col_count)
            ).rstrip()
        )
        if border == "simple":
            lines.append(
                col_gap.join("-" * max(1, widths[i]) for i in range(col_count)).rstrip()
            )
    for row in norm_rows:
        lines.append(
            col_gap.join(
                _align_cell(row[i], widths[i], alignments[i]) for i in range(col_count)
            ).rstrip()
        )

    return "\\n".join(lines)


def echo_table(
    rows: cabc.Iterable[cabc.Sequence[t.Any]],
    headers: cabc.Sequence[str] | None = None,
    *,
    align: cabc.Sequence[t.Literal["left", "right", "center"]]
    | t.Literal["left", "right", "center"] = "left",
    border: t.Literal["plain", "simple", "grid"] = "simple",
    max_col_width: int | None = None,
    padding: int = 1,
    file: t.IO[t.Any] | None = None,
    nl: bool = True,
    err: bool = False,
    color: bool | None = None,
) -> None:
    """Format a table with :func:`format_table` and output it via :func:`echo`."""
    rendered = format_table(
        rows,
        headers=headers,
        align=align,
        border=border,
        max_col_width=max_col_width,
        padding=padding,
    )
    echo(rendered, file=file, nl=nl, err=err, color=color)
'''

        updated_termui = updated_termui.rstrip("\n") + "\n\n\n" + table_code.lstrip("\n")

        updated_init = _replace_once(
            orig_init,
            "from .termui import echo_via_pager as echo_via_pager\nfrom .termui import edit as edit",
            "from .termui import echo_table as echo_table\nfrom .termui import echo_via_pager as echo_via_pager\nfrom .termui import edit as edit\nfrom .termui import format_table as format_table",
            "__init__.py export echo_table and format_table",
        )

        patch = _unified_diff(rel_termui, orig_termui, updated_termui) + _unified_diff(
            rel_init, orig_init, updated_init
        )
        return patch, [rel_termui, rel_init]

    def generate_solution(self, task_id: str) -> dict[str, Any]:
        dispatch = {
            "task_01": self._patch_task_01_option_constraints,
            "task_02": self._patch_task_02_command_aliases,
            "task_03": self._patch_task_03_bytesize_type,
            "task_04": self._patch_task_04_no_color_env,
            "task_05": self._patch_task_05_echo_table,
        }
        if task_id not in dispatch:
            raise KeyError(f"No oracle generator registered for {task_id!r}")

        patch_text, modified_files = dispatch[task_id]()
        solve_sh = (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n\n"
            'APP_DIR="${APP_DIR:-/app}"\n'
            'SOLUTION_DIR="${SOLUTION_DIR:-/solution}"\n\n'
            'cd "$APP_DIR"\n'
            'git -c safe.directory="*" apply --check "$SOLUTION_DIR/feature.patch"\n'
            'git -c safe.directory="*" apply "$SOLUTION_DIR/feature.patch"\n'
            'echo "Applied reference feature patch cleanly."\n'
        )
        return {
            "task_id": task_id,
            "modified_files": modified_files,
            "patch_text": patch_text,
            "solve_sh": solve_sh,
        }
