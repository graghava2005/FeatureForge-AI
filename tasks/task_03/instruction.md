# Feature Development Task: Human-Readable ByteSize Parameter Type (click.ByteSize)

**Repository:** `pallets/click`  
**Base Commit:** `08b803cf32ceb2ae6a772c62d5da42757a897d44`  
**Subsystem:** `parameter-types`  
**Primary Target File(s):** `src/click/types.py`, `src/click/__init__.py`

## Problem Description

CLIs often accept memory limits, cache quotas, or file size thresholds such as '512MB', '1.5GiB', or '64K'. Click provides IntRange and FloatRange, but has no built-in ParamType to parse human-readable byte-size strings into integer byte counts.

## Requirements

- Implement `ByteSize(ParamType[int])` in `src/click/types.py` and export `ByteSize` in `src/click/__init__.py`.
- Support `min: int | None = None`, `max: int | None = None`, and `binary: bool = True` constructor arguments (validating that `min` and `max` are non-negative and `min <= max` when both set).
- Parse integer and decimal values with optional whitespace and case-insensitive suffixes: `B`, `K`/`KB`/`KiB`, `M`/`MB`/`MiB`, `G`/`GB`/`GiB`, `T`/`TB`/`TiB`, `P`/`PB`/`PiB`.
- When `binary=True`, use powers of 1024 for both short/SI-style (`KB`, `MB`, `GB`, ...) and IEC (`KiB`, `MiB`, `GiB`, ...) suffixes. When `binary=False`, use powers of 1000 for `K`/`KB`/`M`/`MB`... while always using powers of 1024 for explicit IEC (`KiB`, `MiB`, ...).
- Accept pre-converted non-bool `int` values directly while rejecting `bool`, negative numbers, NaN/Inf, empty strings, or invalid units via `self.fail(...)`.
- Enforce inclusive `min` and `max` bounds and implement `get_metavar` and `to_info_dict`.

## Expected Behaviour

CLI options and arguments typed with `click.ByteSize()` convert strings like `'10MiB'`, `'2.5 GB'`, or `'4096'` into exact integer byte counts, reject out-of-range or malformed inputs with `BadParameter`, and expose clean metadata via `to_info_dict()` and `get_metavar()`.

## Acceptance Criteria

- AC1: Plain integers ('1024', 2048) and byte suffix ('512B') convert to exact integer byte counts.
- AC2: Binary mode (`binary=True`) converts `'2K'`, `'2KB'`, `'2KiB'` to 2048 and `'1.5MiB'` to 1572864.
- AC3: Decimal SI mode (`binary=False`) converts `'2KB'` to 2000 and `'2MB'` to 2000000 while `'2KiB'` stays 2048.
- AC4: Whitespace and mixed casing (`' 4 gib '`, `'10m'`) are parsed accurately.
- AC5: `min` and `max` bounds reject values outside range with `BadParameter`.
- AC6: Booleans, negative numbers, `'NaN'`, `'inf'`, empty strings, and unknown units like `'10XB'` fail with `BadParameter`.
- AC7: `click.ByteSize` is exported from top-level `click` and implements `to_info_dict()` and `get_metavar()`.

## Feature Test Scenarios to Satisfy

- IEC binary parsing for B, K/KB/KiB, M/MB/MiB, G/GB/GiB, T/TB/TiB, P/PB/PiB.
- SI decimal parsing with binary=False vs explicit IEC suffix.
- Fractional sizes like '1.5KiB' and '0.5MB' with whitespace and case-insensitivity.
- min and max boundary enforcement on both string and int inputs.
- Rejection of booleans, negative values, empty strings, NaN/inf, and invalid suffixes.
- Full CLI integration with @click.command and @click.option(type=click.ByteSize(...)).
- to_info_dict and get_metavar output validation.

## Regression Constraints

- All existing tests in tests/test_types/ and tests/test_info_dict.py must pass.
- Keep all changes clean, typed, and isolated to the feature scope.
- Do not modify existing test files unless required; preserve backward compatibility.
