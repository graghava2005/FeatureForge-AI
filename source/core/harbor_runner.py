"""Module G: Harbor 0.25.x Evaluation Engine."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import (
    BENCHMARK_RESULTS_PATH,
    HARBOR_EXE_DEFAULT,
    HARBOR_JOBS_DIR,
    HARBOR_VERSION_PREFIX,
    PROJECT_ROOT,
    TASKS_DIR,
    ensure_directories,
)


def _find_harbor_exe() -> str:
    if HARBOR_EXE_DEFAULT.exists():
        return str(HARBOR_EXE_DEFAULT)
    found = shutil.which("harbor")
    if found:
        return found
    raise FileNotFoundError("Harbor CLI executable not found.")


class HarborRunner:
    """Runs Harbor 0.25.x NOP and Oracle validations across generated tasks."""

    def __init__(
        self,
        tasks_dir: Path = TASKS_DIR,
        jobs_dir: Path = HARBOR_JOBS_DIR,
    ) -> None:
        self.tasks_dir = Path(tasks_dir)
        self.jobs_dir = Path(jobs_dir)

    def check_environment(self) -> dict[str, Any]:
        harbor_exe = _find_harbor_exe()
        ver_proc = subprocess.run(
            [harbor_exe, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        harbor_version = (ver_proc.stdout or ver_proc.stderr).strip()

        docker_available = False
        docker_status = "docker CLI not found in PATH"
        docker_exe = shutil.which("docker")
        if docker_exe:
            d_proc = subprocess.run(
                [docker_exe, "info"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            docker_available = d_proc.returncode == 0
            docker_status = (
                "Docker daemon running"
                if docker_available
                else (d_proc.stderr or d_proc.stdout or "Docker daemon unreachable").strip()
            )

        return {
            "harbor_exe": harbor_exe,
            "harbor_version": harbor_version,
            "harbor_0_25_ok": harbor_version.startswith(HARBOR_VERSION_PREFIX),
            "docker_available": docker_available,
            "docker_status": docker_status,
            "local_worktree_env": "core.harbor_local_env:LocalWorktreeEnvironment",
        }

    def run_dry_run_preflight(
        self,
        task_dir: Path,
        env_spec: str | None = "core.harbor_local_env:LocalWorktreeEnvironment",
    ) -> dict[str, Any]:
        harbor_exe = _find_harbor_exe()
        env = dict(os.environ)
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        cmd = [
            harbor_exe,
            "run",
            "-p",
            str(task_dir),
            "-a",
            "nop",
            "-k",
            "1",
            "--dry-run",
            "-y",
        ]
        if env_spec:
            cmd.extend(["--env", env_spec])
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        return {
            "returncode": proc.returncode,
            "passed": proc.returncode == 0,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:],
        }

    def _probe_default_docker_run(self, task_dir: Path, out_dir: Path) -> dict[str, Any]:
        """Run exact default `harbor run` (Docker) once to capture genuine host result."""
        harbor_exe = _find_harbor_exe()
        cmd = [
            harbor_exe,
            "run",
            "-p",
            str(task_dir),
            "-a",
            "nop",
            "-k",
            "1",
            "-o",
            str(out_dir),
            "--no-delete",
            "-y",
        ]
        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        return {
            "command": " ".join(cmd),
            "returncode": proc.returncode,
            "duration_sec": round(time.perf_counter() - t0, 2),
            "stdout_tail": proc.stdout[-1500:],
            "stderr_tail": proc.stderr[-1500:],
        }

    def run_single_trial(
        self,
        task_dir: Path,
        agent: str,
        out_dir: Path,
        env_spec: str | None = "core.harbor_local_env:LocalWorktreeEnvironment",
    ) -> dict[str, Any]:
        harbor_exe = _find_harbor_exe()
        out_dir.mkdir(parents=True, exist_ok=True)
        run_tag = f"{task_dir.name}_{agent}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

        cmd = [
            harbor_exe,
            "run",
            "-p",
            str(task_dir),
            "-a",
            agent,
            "-k",
            "1",
            "-o",
            str(out_dir),
            "--job-name",
            run_tag,
            "--no-delete",
            "-y",
        ]
        if env_spec:
            cmd.extend(["--env", env_spec])

        env = dict(os.environ)
        env["PYTHONPATH"] = str(PROJECT_ROOT)

        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        duration = round(time.perf_counter() - t0, 2)

        job_dir = out_dir / run_tag
        reward = None
        verifier_details: dict[str, Any] = {}
        test_stdout = ""
        trial_result: dict[str, Any] = {}

        # Locate trial artifacts generated by Harbor
        if job_dir.exists():
            job_result_path = job_dir / "result.json"
            if job_result_path.exists():
                try:
                    trial_result = json.loads(job_result_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            for reward_json in job_dir.rglob("verifier/reward.json"):
                try:
                    rdata = json.loads(reward_json.read_text(encoding="utf-8"))
                    if "reward" in rdata:
                        reward = float(rdata["reward"])
                except Exception:
                    pass
                details_path = reward_json.parent / "verifier_details.json"
                if details_path.exists():
                    try:
                        verifier_details = json.loads(details_path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                stdout_path = reward_json.parent / "test-stdout.txt"
                if stdout_path.exists():
                    test_stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
                break

            if reward is None:
                for reward_txt in job_dir.rglob("verifier/reward.txt"):
                    try:
                        reward = float(reward_txt.read_text(encoding="utf-8").strip())
                    except Exception:
                        pass
                    break

        return {
            "task_id": task_dir.name,
            "agent": agent,
            "environment": env_spec or "docker",
            "command": " ".join(cmd),
            "job_dir": str(job_dir),
            "returncode": proc.returncode,
            "duration_sec": duration,
            "reward": reward,
            "verifier_details": verifier_details,
            "test_stdout_tail": test_stdout[-3000:],
            "harbor_stdout_tail": proc.stdout[-2000:],
            "harbor_stderr_tail": proc.stderr[-2000:],
            "trial_summary": trial_result.get("stats", {}),
        }

    def run_all(
        self,
        agents: tuple[str, ...] = ("nop", "oracle"),
        task_ids: list[str] | None = None,
        save: bool = True,
    ) -> dict[str, Any]:
        ensure_directories()
        t0 = time.perf_counter()
        env_info = self.check_environment()
        use_env = None if env_info["docker_available"] else env_info["local_worktree_env"]

        task_dirs = sorted(
            p for p in self.tasks_dir.iterdir()
            if p.is_dir() and (task_ids is None or p.name in task_ids)
        )

        docker_probe = None
        if not env_info["docker_available"] and task_dirs:
            docker_probe = self._probe_default_docker_run(
                task_dirs[0], self.jobs_dir / "docker_probe"
            )

        dry_runs: dict[str, Any] = {}
        results_by_task: dict[str, dict[str, Any]] = {}

        for task_dir in task_dirs:
            tid = task_dir.name
            dry_runs[tid] = self.run_dry_run_preflight(task_dir, env_spec=use_env)
            task_entry: dict[str, Any] = {
                "task_id": tid,
                "dry_run_passed": dry_runs[tid]["passed"],
            }
            for agent in agents:
                trial = self.run_single_trial(
                    task_dir=task_dir,
                    agent=agent,
                    out_dir=self.jobs_dir / agent,
                    env_spec=use_env,
                )
                task_entry[agent] = trial
            results_by_task[tid] = task_entry

        nop_rewards = {
            tid: entry["nop"]["reward"]
            for tid, entry in results_by_task.items()
            if "nop" in entry
        }
        oracle_rewards = {
            tid: entry["oracle"]["reward"]
            for tid, entry in results_by_task.items()
            if "oracle" in entry
        }

        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "environment_check": env_info,
            "execution_backend": "docker" if env_info["docker_available"] else "harbor-cli-local-worktree",
            "docker_default_probe": docker_probe,
            "dry_run_preflights": dry_runs,
            "tasks": results_by_task,
            "summary": {
                "tasks_evaluated": len(results_by_task),
                "nop_rewards": nop_rewards,
                "oracle_rewards": oracle_rewards,
                "nop_all_zero": all(r == 0.0 for r in nop_rewards.values()) if nop_rewards else False,
                "oracle_all_one": all(r == 1.0 for r in oracle_rewards.values()) if oracle_rewards else False,
                "total_duration_sec": round(time.perf_counter() - t0, 2),
            },
        }

        if save:
            BENCHMARK_RESULTS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
