# FeatureForge AI — 3-Minute Hackathon Demo Script

**Total Runtime:** 3:00  
**Preparation Before Starting:**
1. Open a terminal in the project root (`FEATUREFORGE AI` or `FeatureForge_Submission/source`).
2. Start the Streamlit dashboard in advance (or at 2:25):
   ```bash
   streamlit run app.py
   ```
3. Keep `output/FINAL_VERIFICATION_REPORT.md` and `presentation/FeatureForge_AI_Presentation.html` open in tabs.

---

### 0:00 – 0:25 | Problem Statement & Solution Overview
**Show:** Dashboard **Page 1: Overview** (`http://localhost:8501`).  
**Narration:**
> "Existing AI coding benchmarks rely on manual task writing, repetitive bug fixes, and weak tests that often fail to verify real feature behavior. FeatureForge AI solves this as a self-auditing coding task factory for Track 1. From a single clean open-source repository—`pallets/click` pinned at base commit `08b803cf32ceb2ae6a772c62d5da42757a897d44`—it automatically analyzes the codebase, rejects non-novel ideas, generates five distinct feature-development packages, and validates every task with reference patches, regression tests, mutation testing, and Harbor `0.25.0`."

**Point to on screen:** The **Problem Statement Alignment** banner, the four summary cards (`5 / 5` tasks generated, `5 / 5` validated, `100.0%` mutation score, `5 NOP / 5 Oracle`), and the **Pipeline Status** table.

---

### 0:25 – 0:50 | Repository Selection & Automated Analysis
**Action:** Click **2. Repository Analysis** in the left sidebar.  
*(Optional live terminal command if showing CLI):*
```bash
python -c "from core.repository_analyzer import RepositoryAnalyzer; r = RepositoryAnalyzer().run(); print(r['git_verification']['head_sha'], r['capability_scan'])"
```
**Narration:**
> "Before generating tasks, we verified `pallets/click`'s unmodified baseline suite—`2,543` tests passed with zero failures. Module A parses all `17` Python modules (`12,823` lines) and `58` test files (`629` test definitions) using Python ASTs and Git history. Notice the Capability Scan: our Novelty Checker catches already-existing capabilities—like Click's `deprecated` parameter—with exact AST symbol evidence, while identifying five genuine feature gaps."

---

### 0:50 – 1:20 | Five Generated Harbor Task Packages
**Action:** Click **3. Task Factory** in the sidebar. Expand **View Novelty Auditor Rejections**, then expand `task_01` and `task_03` package inspectors (`task.toml`, `solution/feature.patch`, `tests/fail_to_pass.json`).  
*(CLI regeneration command):*
```bash
python scripts/generate_tasks.py
```
**Narration:**
> "Module B through E generate five substantively different feature tasks spanning five Click subsystems: `task_01` option `conflicts_with` and `requires` validation; `task_02` command and group `aliases`; `task_03` human-readable `ByteSize` parameter type; `task_04` `NO_COLOR` and `FORCE_COLOR` support; and `task_05` ANSI-aware `echo_table` formatting. Each package includes `instruction.md`, Harbor-validated `task.toml` with the 40-character base SHA, `environment/Dockerfile`, `solution/solve.sh` + `feature.patch`, and `fail_to_pass.json` + `pass_to_pass.json`."

---

### 1:20 – 1:50 | Quality Auditing & Mutation Testing
**Action:** Click **4. Quality Auditor** in the sidebar. Scroll through the **Quality Verification Matrix**, the orange **Mutation Detection Rate (%)** chart, and the **Deliberate Code Mutation Testing Results** table.  
*(CLI command):*
```bash
python scripts/run_benchmarks.py --skip-harbor
```
**Narration:**
> "Generating tasks isn't enough—we audit every task across six dimensions: requirement-test consistency, base-fail/patched-pass coverage, regression safety, deliberate code mutation testing, reversed-order isolation, and deterministic execution. All `5/5` tasks pass every check, zero regressions occur across hundreds of existing Click tests (`795` on `task_01`, `569` on `task_04`), and `15/15` deliberate mutations are killed (`100%` mutation score)."

---

### 1:50 – 2:25 | Harbor `0.25.0` NOP & Oracle Results
**Action:** Click **5. Harbor Benchmark** in the sidebar. Show the results table, the **NOP vs Oracle Rewards** chart, and inspect `task_04` NOP vs Oracle logs in the tabs below.  
*(CLI Harbor command used on this host):*
```bash
harbor run -p tasks/task_04 -a nop -k 1 -o output/harbor_jobs/nop --env core.harbor_local_env:LocalWorktreeEnvironment --no-delete -y
harbor run -p tasks/task_04 -a oracle -k 1 -o output/harbor_jobs/oracle --env core.harbor_local_env:LocalWorktreeEnvironment --no-delete -y
```
**Narration:**
> "Using Harbor `0.25.0`, we ran both `nop` and `oracle` trials across all five tasks. On `nop`, all five tasks score `0.0`—all new feature tests fail (including `7/7` on `task_04`) while existing regression tests pass. On `oracle`, all five tasks apply `solution/solve.sh` and score `1.0` with zero regression failures."

---

### 2:25 – 2:50 | Dashboard & Exportable Final Reports
**Action:** Click **6. Final Reports** in the sidebar. Show the four download buttons (`Markdown`, `generated_tasks.json`, `quality_report.json`, `benchmark_results.json`) and scroll through `FINAL_VERIFICATION_REPORT.md`.  
**Narration:**
> "Every button in this white-and-orange dashboard executes real backend operations, and the Final Reports page compiles `FINAL_VERIFICATION_REPORT.md` directly from observed JSON artifacts with one-click export."

---

### 2:50 – 3:00 | Impact & Honest Limitation Disclosure
**Show:** Section 5 (**Docker Limitations**) in **6. Final Reports** (or Slide 7).  
**Narration:**
> "To be transparent: because Docker Desktop and WSL2 are not installed on this non-administrator Windows machine, Docker container execution remains incomplete—we verified Harbor `0.25.0` locally via isolated git worktrees (`LocalWorktreeEnvironment`) and include ready-to-run `Dockerfile`s for Docker hosts. FeatureForge AI delivers five reproducible, self-audited feature tasks ready for benchmark evaluation. Thank you."
