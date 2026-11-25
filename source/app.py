"""FeatureForge AI — Self-Auditing AI Coding Benchmark Factory (Streamlit Dashboard)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config.settings import (
    BASE_COMMIT_SHA,
    FINAL_REPORT_PATH,
    GENERATED_TASKS_PATH,
    MUTATION_REPORT_PATH,
    QUALITY_REPORT_PATH,
    REPO_ANALYSIS_PATH,
    BENCHMARK_RESULTS_PATH,
    TARGET_REPO_DIR,
    TARGET_REPO_NAME,
    TASKS_DIR,
)
from core.harbor_runner import HarborRunner
from core.quality_auditor import QualityAuditor
from core.repository_analyzer import RepositoryAnalyzer
from core.task_generator import TaskGenerator
from dashboard.components import inject_theme_css, metric_card, status_badge
from dashboard.reports import generate_final_report, load_all_artifacts

st.set_page_config(
    page_title="FeatureForge AI — Benchmark Factory",
    page_icon="⚒️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme_css()

with st.sidebar:
    st.markdown("## FeatureForge AI")
    st.caption("Self-Auditing AI Coding Benchmark Factory • Track 1")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        [
            "1. Overview",
            "2. Repository Analysis",
            "3. Task Factory",
            "4. Quality Auditor",
            "5. Harbor Benchmark",
            "6. Final Reports",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(f"**Target Repo:** `{TARGET_REPO_NAME}`")
    st.markdown(f"**Base SHA:** `{BASE_COMMIT_SHA[:12]}...`")
    st.markdown("**Harbor Target:** `0.25.x`")

artifacts = load_all_artifacts()
ra = artifacts["repository_analysis"]
gt = artifacts["generated_tasks"]
qr = artifacts["quality_report"]
mr = artifacts["mutation_report"]
br = artifacts["benchmark_results"]


# ==============================================================================
# PAGE 1: Overview
# ==============================================================================
if page == "1. Overview":
    st.title("FeatureForge AI")
    st.markdown(
        '<div class="ff-subtitle">Self-Auditing AI Coding Benchmark Factory — Automated Task Generation, Mutation Auditing, and Harbor 0.25.x Verification</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="ff-card-accent">
            <strong>Problem Statement Alignment</strong><br/>
            <span style="color:#444444;">
            <strong>Problem:</strong> Manual benchmark creation is expensive, tasks lack diversity, and test quality is difficult to guarantee.<br/>
            <strong>Solution:</strong> Automated repository analysis and generation of five genuinely different feature-development tasks from <code>pallets/click</code>.<br/>
            <strong>Validation:</strong> Reference implementation patches, behavioral feature tests, regression suites, deliberate code mutation testing, and Harbor 0.25.x NOP/Oracle runs.<br/>
            <strong>Outcome:</strong> Repeatable, inspectable, and objectively verified AI coding benchmark packages.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    base_sha = ra.get("git_verification", {}).get("head_sha", gt.get("base_commit", "Pending"))
    tasks_gen = gt.get("generated_task_count", 0)
    tasks_val = qr.get("valid_tasks", 0)
    mut_score = mr.get("overall_mutation_score_pct", None)
    nop_rewards = br.get("summary", {}).get("nop_rewards", {})
    ora_rewards = br.get("summary", {}).get("oracle_rewards", {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Repository", TARGET_REPO_NAME, f"SHA: {base_sha[:10]}...")
    with c2:
        metric_card("Tasks Generated", f"{tasks_gen} / 5", "Distinct feature tasks")
    with c3:
        metric_card(
            "Tasks Validated",
            f"{tasks_val} / {tasks_gen or 5}",
            f"Mutation: {mut_score}%" if mut_score is not None else "Run Quality Auditor",
        )
    with c4:
        nop_ok = sum(1 for v in nop_rewards.values() if v == 0.0)
        ora_ok = sum(1 for v in ora_rewards.values() if v == 1.0)
        metric_card(
            "Harbor NOP / Oracle",
            f"{nop_ok} NOP / {ora_ok} Oracle",
            br.get("execution_backend", "Not executed yet"),
        )

    st.subheader("Pipeline Status")
    pipeline_rows = [
        {
            "Stage": "Module A: Repository Analyzer",
            "Status": "Complete" if ra else "Pending",
            "Artifact": "output/repository_analysis.json",
            "Detail": f"{ra.get('source_analysis', {}).get('source_module_count', 0)} modules, {ra.get('test_analysis', {}).get('total_test_functions', 0)} tests"
            if ra
            else "Not run",
        },
        {
            "Stage": "Modules B-E: 5-Task Factory + Patches + Tests",
            "Status": "Complete" if tasks_gen == 5 else "Pending",
            "Artifact": "output/generated_tasks.json",
            "Detail": f"{tasks_gen} tasks generated, {len(gt.get('rejected_candidates', []))} existing candidate rejected"
            if gt
            else "Not run",
        },
        {
            "Stage": "Module F: Quality & Mutation Auditor",
            "Status": "Complete" if qr else "Pending",
            "Artifact": "output/quality_report.json",
            "Detail": f"{tasks_val}/{qr.get('total_tasks', 0)} valid, {mr.get('total_killed', 0)}/{mr.get('total_mutants', 0)} mutants killed"
            if qr
            else "Not run",
        },
        {
            "Stage": "Module G: Harbor 0.25.x Evaluation",
            "Status": "Complete" if br else "Pending",
            "Artifact": "output/benchmark_results.json",
            "Detail": f"NOP 0.0: {nop_ok}/{len(nop_rewards)}, Oracle 1.0: {ora_ok}/{len(ora_rewards)}"
            if br
            else "Not run",
        },
        {
            "Stage": "Module H: Final Verification Report",
            "Status": "Complete" if FINAL_REPORT_PATH.exists() else "Pending",
            "Artifact": "output/FINAL_VERIFICATION_REPORT.md",
            "Detail": "Ready for export" if FINAL_REPORT_PATH.exists() else "Not generated",
        },
    ]
    st.dataframe(pd.DataFrame(pipeline_rows), width="stretch", hide_index=True)

    st.subheader("Recent Execution Activity")
    activity = []
    if ra:
        activity.append(f"Analyzed `{TARGET_REPO_NAME}` at `{base_sha}` in {ra.get('analysis_duration_sec')}s.")
    if gt:
        activity.append(
            f"Generated {tasks_gen} Harbor packages in {gt.get('generation_duration_sec')}s "
            f"(LLM mode: `{gt.get('llm_provider')}`)."
        )
    if qr:
        activity.append(
            f"Audited {qr.get('total_tasks')} tasks in {qr.get('duration_sec')}s; "
            f"overall mutation score {mut_score}%."
        )
    if br:
        activity.append(
            f"Executed Harbor `{br.get('environment_check', {}).get('harbor_version', '')}` "
            f"via `{br.get('execution_backend')}` in {br.get('summary', {}).get('total_duration_sec')}s."
        )
    if not activity:
        st.info("No pipeline runs recorded yet. Use the sidebar pages or CLI scripts to execute the pipeline.")
    else:
        for line in activity:
            st.markdown(f"- {line}")


# ==============================================================================
# PAGE 2: Repository Analysis
# ==============================================================================
elif page == "2. Repository Analysis":
    st.title("Repository Analysis")
    st.markdown(
        '<div class="ff-subtitle">Automated Git, AST source, test suite, and capability-gap inspection of pallets/click</div>',
        unsafe_allow_html=True,
    )

    if st.button("Run Repository Analyzer", type="primary"):
        with st.spinner("Inspecting pallets/click source AST, tests, and Git history..."):
            ra = RepositoryAnalyzer(TARGET_REPO_DIR).run(save=True)
        st.success("Repository analysis completed and saved to output/repository_analysis.json.")
        st.rerun()

    if not ra:
        st.warning("Run the Repository Analyzer above to inspect pallets/click.")
    else:
        gv = ra["git_verification"]
        sa = ra["source_analysis"]
        ta = ra["test_analysis"]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("Base Commit", gv["head_sha"][:12], "40-char SHA verified")
        with col2:
            metric_card("Working Tree", "Clean" if gv["is_clean_working_tree"] else "Dirty", gv["branch"])
        with col3:
            metric_card("Source Modules", str(sa["source_module_count"]), f"{sa['total_source_lines']} lines")
        with col4:
            metric_card("Test Functions", str(ta["total_test_functions"]), f"Across {ta['test_file_count']} files")

        st.markdown(f"**Full 40-char Base SHA:** `{gv['head_sha']}`  \n**Latest Commit:** {gv['commit_subject']} ({gv['commit_date']})")

        left, right = st.columns(2)
        with left:
            st.subheader("Source Modules Analyzed")
            mod_rows = [
                {
                    "Module": m["relative_path"],
                    "Lines": m["line_count"],
                    "Classes": len(m["classes"]),
                    "Functions": len(m["functions"]),
                }
                for m in sa["modules"]
            ]
            st.dataframe(pd.DataFrame(mod_rows), width="stretch", hide_index=True)

        with right:
            st.subheader("Existing Test Suite Breakdown")
            test_rows = [
                {
                    "Test File": tf["relative_path"],
                    "Test Functions": tf["test_count"],
                }
                for tf in ta["test_files"]
            ]
            st.dataframe(pd.DataFrame(test_rows), width="stretch", hide_index=True)

        st.subheader("Capability Scan (Novel vs Already Existing)")
        scan = ra.get("capability_scan", {})
        c_nov, c_rej = st.columns(2)
        with c_nov:
            st.markdown("**Identified Novel Opportunities**")
            for item in scan.get("novel_feature_opportunities", []):
                st.markdown(f"- {status_badge('NOVEL', 'pass')} **{item['title']}**", unsafe_allow_html=True)
        with c_rej:
            st.markdown("**Rejected (Already Exists in Base Commit)**")
            for item in scan.get("existing_capabilities_rejected", []):
                ev = "; ".join(item.get("evidence", [])[:2])
                st.markdown(
                    f"- {status_badge('EXISTS', 'fail')} **{item['title']}** — `{ev}`",
                    unsafe_allow_html=True,
                )


# ==============================================================================
# PAGE 3: Task Factory
# ==============================================================================
elif page == "3. Task Factory":
    st.title("Task Factory")
    st.markdown(
        '<div class="ff-subtitle">Generate and inspect five distinct Harbor 0.25.x feature-development task packages</div>',
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        use_llm = st.checkbox("Use LLM spec enrichment (if API key available)", value=False)
    with col_btn2:
        if st.button("Generate 5 Feature Tasks", type="primary"):
            with st.spinner("Running Feature Generator, Novelty Auditor, Oracle Patch Generator & Test Generator..."):
                gt = TaskGenerator(use_llm_enrichment=use_llm).run(save=True)
            st.success(f"Generated {gt['generated_task_count']} validated task packages under tasks/.")
            st.rerun()

    if not gt:
        st.warning("No generated tasks found yet. Click 'Generate 5 Feature Tasks' above.")
    else:
        st.caption(
            f"Provider: `{gt.get('llm_provider')}` ({gt.get('llm_model')}) — "
            f"Candidates evaluated: {gt.get('total_candidates_evaluated')}, "
            f"Rejected: {len(gt.get('rejected_candidates', []))}, "
            f"Approved: {gt.get('generated_task_count')}"
        )

        if gt.get("rejected_candidates"):
            with st.expander("View Novelty Auditor Rejections (Demonstrating Real Non-LLM Filtering)", expanded=False):
                for rej in gt["rejected_candidates"]:
                    st.markdown(
                        f"{status_badge('REJECTED', 'fail')} **{rej['task_id']} — {rej['feature_title']}**",
                        unsafe_allow_html=True,
                    )
                    for reason in rej.get("rejection_reasons", []):
                        st.markdown(f"  - {reason}")

        audit_by_id = {a["task_id"]: a for a in gt.get("novelty_audit_records", [])}

        for t_entry in gt["tasks"]:
            tid = t_entry["task_id"]
            prop = t_entry["proposal"]
            audit = audit_by_id.get(tid, {})
            nov_status = audit.get("status", "APPROVED")

            st.markdown(
                f"""
                <div class="ff-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="font-size:1.05rem;">{tid}: {t_entry['feature_title']}</strong>
                        <span>{status_badge(t_entry['subsystem'], 'orange')} {status_badge(nov_status, 'pass')}</span>
                    </div>
                    <p style="color:#666666;margin-top:0.45rem;margin-bottom:0.4rem;">{prop['problem_description']}</p>
                    <div style="font-size:0.85rem;color:#444444;">
                        <strong>Modified files:</strong> <code>{', '.join(t_entry['modified_files'])}</code> &nbsp;|&nbsp;
                        <strong>Feature tests:</strong> <code>{t_entry['fail_to_pass_count']}</code> &nbsp;|&nbsp;
                        <strong>Regression targets:</strong> <code>{', '.join(t_entry['pass_to_pass_targets'])}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander(f"Inspect {tid} Package & Acceptance Criteria"):
                st.markdown("**Acceptance Criteria**")
                for ac in prop["acceptance_criteria"]:
                    st.markdown(f"- {ac}")

                task_dir = Path(t_entry["task_dir"])
                file_choice = st.selectbox(
                    "Select package file to view",
                    [
                        "instruction.md",
                        "task.toml",
                        "environment/Dockerfile",
                        "solution/feature.patch",
                        "solution/solve.sh",
                        f"tests/{t_entry['feature_test_file']}",
                        "tests/fail_to_pass.json",
                        "tests/pass_to_pass.json",
                        "tests/test.sh",
                    ],
                    key=f"inspect_{tid}",
                )
                fpath = task_dir / file_choice
                if fpath.exists():
                    lang = (
                        "toml"
                        if file_choice.endswith(".toml")
                        else "diff"
                        if file_choice.endswith(".patch")
                        else "python"
                        if file_choice.endswith(".py")
                        else "json"
                        if file_choice.endswith(".json")
                        else "bash"
                        if file_choice.endswith(".sh")
                        else "dockerfile"
                        if file_choice.endswith("Dockerfile")
                        else "markdown"
                    )
                    st.code(fpath.read_text(encoding="utf-8"), language=lang)


# ==============================================================================
# PAGE 4: Quality Auditor
# ==============================================================================
elif page == "4. Quality Auditor":
    st.title("Quality & Mutation Auditor")
    st.markdown(
        '<div class="ff-subtitle">Six-dimension verification: requirement consistency, feature coverage, regression safety, code mutation testing, isolation, and determinism</div>',
        unsafe_allow_html=True,
    )

    if st.button("Run Quality & Mutation Audit", type="primary"):
        with st.spinner("Running pytest across base/patched worktrees and executing deliberate mutants..."):
            qa_res = QualityAuditor().run_all(save=True)
        st.success(
            f"Quality audit finished: {qa_res['valid_tasks']}/{qa_res['total_tasks']} valid tasks, "
            f"mutation score {qa_res['overall_mutation_score_pct']}%."
        )
        st.rerun()

    if not qr:
        st.warning("No quality report found yet. Click 'Run Quality & Mutation Audit' above.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Valid Tasks", f"{qr['valid_tasks']} / {qr['total_tasks']}")
        with c2:
            metric_card(
                "Mutation Score",
                f"{mr.get('overall_mutation_score_pct', 0)}%",
                f"{mr.get('total_killed', 0)}/{mr.get('total_mutants', 0)} killed",
            )
        with c3:
            metric_card("Mutants Survived", str(mr.get("total_survived", 0)))
        with c4:
            metric_card("Audit Duration", f"{qr.get('duration_sec', 0)}s")

        matrix_rows = []
        for t in qr["tasks"]:
            ch = t["checks"]
            matrix_rows.append(
                {
                    "Task": t["task_id"],
                    "Overall": "PASS" if t["overall_passed"] else "FAIL",
                    "1. Req-Test Consistency": "PASS" if ch["1_requirement_test_consistency"]["passed"] else "FAIL",
                    "2. Feature Coverage": "PASS" if ch["2_feature_coverage"]["passed"] else "FAIL",
                    "3. Regression Safety": "PASS" if ch["3_regression_safety"]["passed"] else "FAIL",
                    "4. Mutation Testing": f"{ch['4_mutation_testing']['killed']}/{ch['4_mutation_testing']['total_mutants']} ({ch['4_mutation_testing']['mutation_score_pct']}%)",
                    "5. Test Isolation": "PASS" if ch["5_test_isolation"]["passed"] else "FAIL",
                    "6. Determinism": "PASS" if ch["6_deterministic_execution"]["passed"] else "FAIL",
                }
            )
        st.subheader("Quality Verification Matrix")
        st.dataframe(pd.DataFrame(matrix_rows), width="stretch", hide_index=True)

        if mr:
            st.subheader("Mutation Detection Rate (%) by Task")
            chart_df = pd.DataFrame(
                [
                    {
                        "Task": mtask["task_id"],
                        "Mutation Score (%)": mtask.get("mutation_score_pct", 0.0),
                    }
                    for mtask in mr.get("tasks", [])
                ]
            ).set_index("Task")
            st.bar_chart(chart_df, color="#F97316", height=220)

            st.subheader("Deliberate Code Mutation Testing Results")
            mut_rows = []
            for mtask in mr.get("tasks", []):
                for m in mtask.get("mutants", []):
                    mut_rows.append(
                        {
                            "Task": mtask["task_id"],
                            "Mutant ID": m["id"],
                            "File": m["file"],
                            "Mutation": m["description"],
                            "Outcome": m["status"],
                            "Time (s)": m.get("duration_sec", 0),
                        }
                    )
            st.dataframe(pd.DataFrame(mut_rows), width="stretch", hide_index=True)


# ==============================================================================
# PAGE 5: Harbor Benchmark
# ==============================================================================
elif page == "5. Harbor Benchmark":
    st.title("Harbor 0.25.x Benchmark Execution")
    st.markdown(
        '<div class="ff-subtitle">Execute genuine Harbor CLI NOP (expected 0.0) and Oracle (expected 1.0) trials across all five tasks</div>',
        unsafe_allow_html=True,
    )

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Run NOP Baseline", type="secondary", width="stretch"):
            with st.spinner("Running Harbor 0.25.0 NOP trials across 5 tasks..."):
                HarborRunner().run_all(agents=("nop",), save=True)
            st.rerun()
    with b2:
        if st.button("Run Oracle Reference", type="secondary", width="stretch"):
            with st.spinner("Running Harbor 0.25.0 Oracle trials across 5 tasks..."):
                HarborRunner().run_all(agents=("oracle",), save=True)
            st.rerun()
    with b3:
        if st.button("Run Full NOP + Oracle Benchmark", type="primary", width="stretch"):
            with st.spinner("Running full Harbor 0.25.0 NOP + Oracle suite across 5 tasks..."):
                HarborRunner().run_all(agents=("nop", "oracle"), save=True)
            st.rerun()

    if not br:
        st.warning("No Harbor benchmark results recorded yet. Click one of the run buttons above.")
    else:
        env_chk = br.get("environment_check", {})
        st.markdown(
            f"**Harbor Version:** `{env_chk.get('harbor_version')}` &nbsp;|&nbsp; "
            f"**Backend:** `{br.get('execution_backend')}` &nbsp;|&nbsp; "
            f"**Docker Available:** `{env_chk.get('docker_available')}`"
        )
        if not env_chk.get("docker_available"):
            probe = br.get("docker_default_probe") or {}
            st.warning(
                f"Docker validation is INCOMPLETE: Docker runtime is unavailable on this host (`{env_chk.get('docker_status')}`, "
                f"default `harbor run` exited `{probe.get('returncode')}`). The table below shows Harbor 0.25.0 CLI trials "
                f"executed via `--env {env_chk.get('local_worktree_env')}` (local isolated worktrees, NOT Docker validation)."
            )

        rows = []
        for tid, entry in br.get("tasks", {}).items():
            nop = entry.get("nop", {})
            ora = entry.get("oracle", {})
            rows.append(
                {
                    "Task": tid,
                    "Dry-Run": "PASS" if entry.get("dry_run_passed") else "FAIL",
                    "NOP Reward": nop.get("reward", "N/A"),
                    "NOP Duration (s)": nop.get("duration_sec", "N/A"),
                    "Oracle Reward": ora.get("reward", "N/A"),
                    "Oracle Duration (s)": ora.get("duration_sec", "N/A"),
                }
            )
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        reward_chart_df = pd.DataFrame(
            [
                {
                    "Task": tid,
                    "NOP Reward": entry.get("nop", {}).get("reward", 0.0) or 0.0,
                    "Oracle Reward": entry.get("oracle", {}).get("reward", 0.0) or 0.0,
                }
                for tid, entry in br.get("tasks", {}).items()
            ]
        ).set_index("Task")
        if not reward_chart_df.empty:
            st.subheader("NOP vs Oracle Rewards by Task (LocalWorktreeEnvironment)")
            st.bar_chart(reward_chart_df, color=["#666666", "#F97316"], height=220)

        st.subheader("Trial Logs & Verifier Output")
        task_sel = st.selectbox("Inspect task logs", list(br.get("tasks", {}).keys()))
        if task_sel:
            t_data = br["tasks"][task_sel]
            tab_nop, tab_ora = st.tabs(["NOP Execution Log", "Oracle Execution Log"])
            with tab_nop:
                nop = t_data.get("nop", {})
                if nop:
                    st.code(nop.get("command", ""), language="bash")
                    st.text(nop.get("test_stdout_tail") or nop.get("harbor_stdout_tail", ""))
                else:
                    st.info("NOP not executed in this run.")
            with tab_ora:
                ora = t_data.get("oracle", {})
                if ora:
                    st.code(ora.get("command", ""), language="bash")
                    st.text(ora.get("test_stdout_tail") or ora.get("harbor_stdout_tail", ""))
                else:
                    st.info("Oracle not executed in this run.")


# ==============================================================================
# PAGE 6: Final Reports
# ==============================================================================
elif page == "6. Final Reports":
    st.title("Final Verification Reports")
    st.markdown(
        '<div class="ff-subtitle">Inspect and export real benchmark, quality, and Harbor verification reports</div>',
        unsafe_allow_html=True,
    )

    if st.button("Regenerate Final Verification Report", type="primary"):
        generate_final_report(save=True)
        st.success("Saved output/FINAL_VERIFICATION_REPORT.md")
        st.rerun()

    report_md = (
        FINAL_REPORT_PATH.read_text(encoding="utf-8")
        if FINAL_REPORT_PATH.exists()
        else generate_final_report(save=False)
    )

    dl1, dl2, dl3, dl4 = st.columns(4)
    with dl1:
        st.download_button(
            "Download Markdown Report",
            data=report_md,
            file_name="FINAL_VERIFICATION_REPORT.md",
            mime="text/markdown",
            width="stretch",
        )
    with dl2:
        st.download_button(
            "Download generated_tasks.json",
            data=json.dumps(gt, indent=2),
            file_name="generated_tasks.json",
            mime="application/json",
            width="stretch",
        )
    with dl3:
        st.download_button(
            "Download quality_report.json",
            data=json.dumps(qr, indent=2),
            file_name="quality_report.json",
            mime="application/json",
            width="stretch",
        )
    with dl4:
        st.download_button(
            "Download benchmark_results.json",
            data=json.dumps(br, indent=2),
            file_name="benchmark_results.json",
            mime="application/json",
            width="stretch",
        )

    st.markdown("---")
    st.markdown(report_md)
