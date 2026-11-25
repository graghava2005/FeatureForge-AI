# FeatureForge AI — Self-Auditing AI Coding Benchmark Factory

**Hackathon Track:** Track 1 — Coding Task Factory  
**Tagline:** Self-Auditing AI Coding Benchmark Factory  
**Target Repository:** [`pallets/click`](https://github.com/pallets/click)  
**Base Commit (40-char SHA):** `08b803cf32ceb2ae6a772c62d5da42757a897d44`  
**Evaluation Framework:** Harbor `0.25.0` + `pytest`

---

## 1. Project Overview

FeatureForge AI is an automated benchmark-factory pipeline that analyzes an open-source repository (`pallets/click`), discovers genuinely new feature-development opportunities, audits novelty against actual source ASTs and Git history, synthesizes isolated reference patches and behavioral test suites, validates task quality with six automated checks plus deliberate code mutation testing, packages five independent Harbor `0.25.0` tasks, and exposes all controls and evidence in a white-and-orange Streamlit control plane.

## 2. Problem Statement

Existing AI coding benchmarks suffer from:
- Repetitive or bug-fix-heavy tasks rather than realistic feature engineering.
- Manual, slow requirement and test authoring.
- Insufficient test coverage and weak regression guarantees.
- Task duplication or proposals that unknowingly already exist in the target repository.
- Unverified evaluation harnesses where NOP/Oracle behavior is not systematically checked.

## 3. Proposed Solution

FeatureForge AI replaces ad-hoc manual benchmark creation with an auditable 8-module factory (`Modules A–H`) that:
1. Inspects the clean repository state, AST symbol tables, test files, and Git commit log.
2. Generates candidate feature proposals across distinct subsystems and programmatically rejects already-existing or duplicate ideas.
3. Produces isolated unified `git diff` reference patches (`solution/feature.patch` + `solution/solve.sh`) and behavioral + regression pytest suites (`fail_to_pass.json`, `pass_to_pass.json`, `tests/test.sh`).
4. Runs six-dimension quality auditing and deliberate code mutation testing.
5. Executes Harbor `0.25.0` NOP (`0.0`) and Oracle (`1.0`) evaluations and compiles reproducible Markdown/JSON verification reports.

## 4. Why FeatureForge AI Is Needed

Without automated self-auditing, benchmark tasks frequently pass trivially on the base commit, break existing functionality, miss edge cases, or test internal implementation details instead of requirements. FeatureForge AI verifies **both directions** (`fail_to_pass` fails on base and passes on Oracle; `pass_to_pass` passes on both) and confirms via mutation testing (`15/15` mutants killed) that tests actively catch faulty implementations.

## 5. System Architecture

```text
pallets/click (@ 08b803cf32ceb2ae6a772c62d5da42757a897d44)
   │
   ▼
[Module A] RepositoryAnalyzer (Git + AST + Test Scanner)
   │
   ▼
[Module B] FeatureGenerator (OpenAI optional + Deterministic Baseline)
   │
   ▼
[Module C] NoveltyChecker (AST Symbol Check + Similarity + Completeness)
   │   └── Rejects existing/duplicate candidates (e.g. deprecated flag)
   ▼
[Modules D & E] OracleGenerator + TestGenerator ──► tasks/task_01..task_05/
   │
   ▼
[Module F] QualityAuditor + MutationTester (6 checks + 15 mutants)
   │
   ▼
[Module G] HarborRunner (Harbor 0.25.0: --dry-run, -a nop, -a oracle)
   │
   ▼
[Module H] Reports & Streamlit Dashboard (app.py, FINAL_VERIFICATION_REPORT.md)
```

## 6. Core Features

- **Clean Base Commit Enforcement:** Verifies exact 40-char SHA and unmodified Git working tree before generating tasks.
- **Non-LLM Programmatic Novelty Gate:** Rejects candidate features whose symbols or implementations already exist in source ASTs or Git history.
- **Five Substantively Different Feature Tasks:** Spans five distinct subsystems (`parameter-validation`, `command-routing`, `parameter-types`, `terminal-color`, `terminal-ui`).
- **Automated Reference Patches & Behavioral Tests:** Clean unified `git diff`s and isolated `pytest` suites testing observable CLI/API contracts.
- **Six-Dimension Quality Audit & Mutation Testing:** Checks requirement-test consistency, feature coverage, regression safety, deliberate code mutations, reversed-order isolation, and deterministic execution.
- **Harbor `0.25.0` Integration:** Validates `task.toml` via `TaskConfig.model_validate_toml()` and executes `harbor run` trials.
- **White-and-Orange Streamlit Dashboard:** Six interactive pages wired directly to backend modules and real JSON/Markdown artifacts.

## 7. Technology Stack

- **Language:** Python 3.11+ (verified on Python 3.14.0 on Windows 11)
- **Target Repo & Test Runner:** `pallets/click`, `pytest` (`9.2.0`)
- **Benchmark Harness:** `harbor` (`0.25.0`)
- **UI & Visualization:** `streamlit` (`1.67.0`), `pandas`
- **Similarity & Optional LLM:** `RapidFuzz`, `openai` (env-var `OPENAI_API_KEY`, deterministic fallback when unset/disabled)

## 8. Repository Selection and Base Commit

- **Approved Repository:** `pallets/click`
- **Pinned Base Commit:** `08b803cf32ceb2ae6a772c62d5da42757a897d44`
- **Baseline Test Suite:** `2543 passed, 109 skipped, 31000 deselected, 1 xfailed in 35.15s`

## 9. Five Generated Feature Tasks

| Task ID | Subsystem | Feature Title | Modified File(s) |
|---|---|---|---|
| `task_01` | `parameter-validation` | Option Mutual Exclusivity and Dependency Constraints (`conflicts_with` / `requires`) | `src/click/core.py` |
| `task_02` | `command-routing` | Command and Subcommand Aliases in Group Dispatch and Help Output | `src/click/core.py` |
| `task_03` | `parameter-types` | Human-Readable `ByteSize` Parameter Type (`click.ByteSize`) | `src/click/types.py`, `src/click/__init__.py` |
| `task_04` | `terminal-color` | Standard `NO_COLOR` and `FORCE_COLOR` Environment Variable Resolution | `src/click/_compat.py`, `src/click/globals.py` |
| `task_05` | `terminal-ui` | ANSI-Aware Terminal Table Formatting and Output (`format_table` / `echo_table`) | `src/click/termui.py`, `src/click/__init__.py` |

*(Additionally, `candidate_existing` proposing `deprecated` on `Command`/`Parameter` was evaluated and rejected by Module C because `deprecated` already exists in `src/click/core.py`.)*

## 10. Harbor Integration

Every task under `tasks/task_01/`–`tasks/task_05/` includes:
- `instruction.md`
- `task.toml` (validated with Harbor `0.25.0` `TaskConfig`)
- `environment/Dockerfile` (Linux `python:3.11-slim` image pinned to `08b803cf32ceb2ae6a772c62d5da42757a897d44`)
- `solution/solve.sh` and `solution/feature.patch`
- `tests/test.sh`, `tests/test_feature_*.py`, `tests/fail_to_pass.json`, `tests/pass_to_pass.json`

## 11. Quality Auditing and Mutation Testing

Module F executes six checks per task:
1. Requirement-test consistency & Harbor metadata check
2. Feature coverage (fail on base commit, pass on patched commit)
3. Regression safety (`pass_to_pass` passes on both base and patched)
4. Deliberate code mutation testing (3 targeted mutations per task = 15 mutants total)
5. Test isolation (reversed node order execution)
6. Deterministic execution (repeated run comparison)

## 12. Installation Instructions

```bash
pip install -r requirements.txt
```

Optional LLM specification enrichment reads `OPENAI_API_KEY` from the environment; no API key is required for the core deterministic pipeline.

## 13. Execution Commands

Clone/verify `pallets/click` and run the original baseline test suite:
```bash
python scripts/setup.py
```

Generate all five Harbor task packages (`Modules A–E`):
```bash
python scripts/generate_tasks.py
```

Run Quality Audit, Mutation Testing, Harbor `0.25.0` NOP/Oracle, and Final Report (`Modules F–H`):
```bash
python scripts/run_benchmarks.py
```

## 14. Dashboard Startup Instructions

```bash
streamlit run app.py
```

*(Inside restricted sandboxes where reading `$HOME/.streamlit/secrets.toml` is blocked, run with `USERPROFILE=.` / `HOME=.`.)*

## 15. Benchmark Execution Instructions

Official Docker Harbor commands (for Docker-enabled hosts):
```bash
harbor run -p tasks/task_01 -a nop -k 1 -o output/harbor_jobs/nop --no-delete -y
harbor run -p tasks/task_01 -a oracle -k 1 -o output/harbor_jobs/oracle --no-delete -y
```

Non-Docker Harbor `0.25.0` CLI command used on this Windows host (isolated git worktrees):
```bash
harbor run -p tasks/task_01 -a nop -k 1 -o output/harbor_jobs/nop --env core.harbor_local_env:LocalWorktreeEnvironment --no-delete -y
harbor run -p tasks/task_01 -a oracle -k 1 -o output/harbor_jobs/oracle --env core.harbor_local_env:LocalWorktreeEnvironment --no-delete -y
```

## 16. Validation Results

| Metric | Verified Result | Notes |
|---|---|---|
| Task packages | 5/5 | Validated with Harbor `0.25.0` `TaskConfig` |
| Quality audit | 5/5 valid | 0 failed checks across 6 dimensions |
| Mutation detection | 15/15 (100.0%) | 3/3 mutants killed per task |
| NOP (`LocalWorktreeEnvironment`) | 5/5 rewards = `0.0` | Feature tests fail; regression tests pass |
| Oracle (`LocalWorktreeEnvironment`) | 5/5 rewards = `1.0` | Feature tests pass; regression tests pass |
| Dashboard pages | 6/6 | Verified via `AppTest` + HTTP `200` health probe |
| Click baseline tests | 2,543 passed | 109 skipped, 31,000 deselected, 1 xfailed |
| Docker validation | Not executed | Host lacks Docker/WSL2 and admin privileges |

## 17. Known Limitations

- **Docker Validation Incomplete:** Docker Desktop / Podman / WSL2 is not installed on this Windows host (`WSL is not installed`), and the active user session is non-elevated (`IsInRole(Administrator) == False`), so Docker containers could not be built or executed locally. `LocalWorktreeEnvironment` results are **not** Docker validation.
- **OS & Python Runtime Difference:** Local checks ran on Windows 11 / Python 3.14.0 (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to bypass offline `langsmith` pytest plugin stalls), while task `Dockerfile`s target Linux `python:3.11-slim`.
- **Subsystem Regression Scope in Trials:** Each task's `pass_to_pass.json` targets the relevant subsystem test files (104–795 tests) rather than all 2,543 tests per trial.

## 18. Future Improvements

- Execute `harbor run` with native Docker on a Linux/Docker-enabled CI runner to verify `environment/Dockerfile` builds end-to-end.
- Support additional approved repositories (`colinhacks/zod` with Vitest/Jest, `open-source-parsers/jsoncpp` with CMake/CTest).
- Add automated AST-based mutant synthesis (MutPy/cosmic-ray style operators) beyond curated per-feature mutants.
- Integrate external LLM agent evaluation runs (e.g., `claude-code`, `codex`, `gemini-cli`) via Harbor against the five validated tasks.
