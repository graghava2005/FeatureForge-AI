# FeatureForge AI — Hackathon Presentation (8 Slides)

---

## Slide 1: FeatureForge AI — Project Introduction
- **Title:** FeatureForge AI
- **Subtitle:** Self-Auditing AI Coding Benchmark Factory
- **Track:** Track 1 — Coding Task Factory (Innodata AI Hackathon)
- **Target Repository:** `pallets/click` @ `08b803cf32ceb2ae6a772c62d5da42757a897d44`
- **Core Goal:** Automatically analyze a clean open-source repository, generate **5 substantively different feature-development Harbor `0.25.0` task packages**, and objectively verify quality, mutation detection, and NOP/Oracle rewards.

---

## Slide 2: Existing Problem in AI Coding Benchmarks
- **Repetitive & Narrow Tasks:** Heavy skew toward small bug fixes instead of multi-file feature engineering.
- **Manual Authoring Bottleneck:** Writing specs, reference patches, and tests by hand is slow and inconsistent.
- **Weak Test & Novelty Guarantees:**
  - Tests may pass trivially on the base commit (`NOP != 0.0`).
  - Proposals may unknowingly duplicate existing repo functionality.
  - Tests may mirror implementation internals or miss edge cases.
  - Refactors can silently break existing regression tests.

---

## Slide 3: Proposed Solution & Innovation
- **Deterministic-First Factory (`Modules A–H`):** Reproducible core pipeline with optional `OPENAI_API_KEY` specification enrichment and zero hardcoded secrets.
- **Programmatic Novelty Gate (Non-LLM):** Verifies candidate ideas directly against `src/click/*.py` ASTs and Git history—demonstrated by rejecting an existing `deprecated` flag candidate.
- **Self-Auditing Verification Loop:**
  - Six-dimension Quality Auditor (consistency, coverage, regression, mutation, isolation, determinism).
  - Targeted deliberate code mutation testing (`15/15` mutants killed).
  - Harbor `0.25.0` `nop` (`0.0`) & `oracle` (`1.0`) execution.

---

## Slide 4: System Architecture & Workflow
1. **Module A (`RepositoryAnalyzer`):** Verifies clean 40-char base commit, parses 17 source modules (`12,823` lines) & 58 test files (`629` test defs).
2. **Modules B & C (`FeatureGenerator` + `NoveltyChecker`):** Emits 6 candidates -> rejects `candidate_existing` -> approves 5 distinct subsystem features.
3. **Modules D & E (`OracleGenerator` + `TestGenerator`):** Generates unified `feature.patch`, `solve.sh`, behavioral `pytest` suites, `fail_to_pass.json`, `pass_to_pass.json`, and `test.sh`.
4. **Module F (`QualityAuditor` + `MutationTester`):** Runs 6 checks + 15 code mutations in isolated temp worktrees.
5. **Modules G & H (`HarborRunner` + `Streamlit`):** Executes Harbor `0.25.0` trials and compiles reports + 6-page white/orange UI.

---

## Slide 5: Five Different Generated Feature-Development Tasks
| Task | Subsystem | Feature | Target Files |
|---|---|---|---|
| `task_01` | `parameter-validation` | `Option` `conflicts_with` & `requires` constraints | `src/click/core.py` |
| `task_02` | `command-routing` | `Command` & `Group` `aliases` + help & collision checks | `src/click/core.py` |
| `task_03` | `parameter-types` | Human-readable `click.ByteSize` (`IEC`/`SI`, `min`/`max`) | `src/click/types.py`, `__init__.py` |
| `task_04` | `terminal-color` | Standard `NO_COLOR` & `FORCE_COLOR` resolution | `src/click/_compat.py`, `globals.py` |
| `task_05` | `terminal-ui` | ANSI-aware `click.format_table` & `click.echo_table` | `src/click/termui.py`, `__init__.py` |

---

## Slide 6: Quality Auditing, Mutation Testing & Harbor Validation
- **Six-Dimension Quality Gate:**
  1. Requirement-test consistency & Harbor `TaskConfig` schema validation
  2. Base-commit failure vs Oracle-patched pass (`fail_to_pass`)
  3. Subsystem regression safety (`pass_to_pass`: `104`–`795` existing Click tests per task)
  4. Deliberate code mutation testing (`3` mutants per task = `15` total)
  5. Reversed-order test isolation
  6. Repeated-run determinism
- **Harbor `0.25.0` Harness:** Standardized `instruction.md`, `task.toml`, `environment/Dockerfile`, `solution/solve.sh`, and `tests/test.sh` emitting `reward.txt` / `reward.json`.

---

## Slide 7: Actual Results, Achievements & Limitations
| Metric | Verified Result |
|---|---|
| Task packages | `5/5` complete & schema-valid |
| Click baseline tests | `2,543` passed (pre-generation) |
| Quality audit | `5/5` valid (0 failed checks) |
| Mutation detection | `15/15` killed (`100.0%`) |
| Harbor `0.25.0` NOP (`LocalWorktreeEnvironment`) | `5/5` rewards = `0.0` |
| Harbor `0.25.0` Oracle (`LocalWorktreeEnvironment`) | `5/5` rewards = `1.0` |
| Streamlit dashboard | `6/6` pages verified, HTTP `200` |
| **Docker validation** | **Not executed (Incomplete)** |

- **Honest Limitation:** Docker/WSL2 is unavailable on this non-admin Windows host (`docker CLI not found`, `WSL is not installed`). `LocalWorktreeEnvironment` validates tasks under Harbor `0.25.0` locally, **not** inside Docker containers.

---

## Slide 8: Future Scope & Conclusion
- **Immediate Next Step:** Run `harbor run -p tasks/task_0X -a nop/oracle` on a Linux Docker host using the included `environment/Dockerfile`s.
- **Future Extensions:**
  - Multi-repository factories (`colinhacks/zod`, `open-source-parsers/jsoncpp`).
  - Automated AST mutation operators for deeper test-suite hardening.
  - Multi-agent benchmark evaluation (`claude-code`, `codex`, `gemini-cli`) via Harbor.
- **Conclusion:** FeatureForge AI delivers an inspectable, reproducible, self-auditing coding task factory with five genuinely diverse `pallets/click` feature benchmarks ready for evaluation.
