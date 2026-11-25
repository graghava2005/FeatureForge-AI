"""Custom Harbor 0.25.x BaseEnvironment using an isolated local git checkout."""

from __future__ import annotations

import asyncio
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.capabilities import EnvironmentCapabilities

from config.settings import BASE_COMMIT_SHA, TARGET_REPO_DIR


class LocalWorktreeEnvironment(BaseEnvironment):
    """Isolated local sandbox executing Harbor tasks against a clean git checkout."""

    def __init__(self, *args, **kwargs) -> None:
        self._root: Path | None = None
        self._app_dir: Path | None = None
        super().__init__(*args, **kwargs)

    @staticmethod
    def type() -> str:
        return "local-worktree"

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(mounted=False)

    def _validate_definition(self) -> None:
        if not self.environment_dir.exists():
            raise FileNotFoundError(f"Environment directory missing: {self.environment_dir}")
        dockerfile = self.environment_dir / "Dockerfile"
        compose = self.environment_dir / "docker-compose.yaml"
        if not dockerfile.exists() and not compose.exists():
            raise FileNotFoundError(
                f"Expected Dockerfile or docker-compose.yaml in {self.environment_dir}"
            )

    def _map_container_path(self, container_path: str) -> Path:
        assert self._root is not None
        norm = container_path.replace("\\", "/")
        mappings = [
            ("/app", self._root / "app"),
            ("/solution", self._root / "solution"),
            ("/tests", self._root / "tests"),
            ("/logs/agent", self._root / "logs" / "agent"),
            ("/logs/verifier", self._root / "logs" / "verifier"),
            ("/logs", self._root / "logs"),
            ("/tmp", self._root / "tmp"),
        ]
        for prefix, host_base in mappings:
            if norm == prefix:
                return host_base
            if norm.startswith(prefix + "/"):
                rel = norm[len(prefix) + 1 :]
                return host_base / rel
        rel = norm.lstrip("/")
        return self._root / rel

    async def start(self, force_build: bool) -> None:
        safe_session = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.session_id)
        self._root = Path(tempfile.mkdtemp(prefix=f"harbor_local_{safe_session}_"))
        self._app_dir = self._root / "app"
        for sub in ("solution", "tests", "logs/agent", "logs/verifier", "tmp"):
            (self._root / sub).mkdir(parents=True, exist_ok=True)

        def _setup_repo() -> None:
            shutil.copytree(
                TARGET_REPO_DIR,
                self._app_dir,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
            )

        await asyncio.to_thread(_setup_repo)

    async def stop(self, delete: bool) -> None:
        if delete and self._root is not None and self._root.exists():
            await asyncio.to_thread(shutil.rmtree, self._root, ignore_errors=True)

    async def upload_file(self, source_path: Path | str, target_path: str) -> None:
        dst = self._map_container_path(target_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, Path(source_path), dst)

    async def upload_dir(self, source_dir: Path | str, target_dir: str) -> None:
        src = Path(source_dir)
        dst = self._map_container_path(target_dir)
        dst.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copytree, src, dst, dirs_exist_ok=True)

    async def download_file(self, source_path: str, target_path: Path | str) -> None:
        src = self._map_container_path(source_path)
        dst = Path(target_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not src.exists():
            raise FileNotFoundError(f"Sandbox file not found: {src}")
        await asyncio.to_thread(shutil.copy2, src, dst)

    async def download_dir(self, source_dir: str, target_dir: Path | str) -> None:
        src = self._map_container_path(source_dir)
        dst = Path(target_dir)
        dst.mkdir(parents=True, exist_ok=True)
        if src.exists():
            await asyncio.to_thread(shutil.copytree, src, dst, dirs_exist_ok=True)

    def _run_shell_script_in_python(
        self, script_path: Path, stdout_path: Path | None, merged_env: dict[str, str]
    ) -> ExecResult:
        assert self._root is not None and self._app_dir is not None
        script_text = script_path.read_text(encoding="utf-8", errors="replace")

        if script_path.name == "solve.sh":
            patch_path = self._root / "solution" / "feature.patch"
            check_proc = subprocess.run(
                [
                    "git",
                    "-c",
                    "safe.directory=*",
                    "-C",
                    str(self._app_dir),
                    "apply",
                    "--check",
                    str(patch_path),
                ],
                env=merged_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if check_proc.returncode != 0:
                combined = (check_proc.stdout or "") + (check_proc.stderr or "")
                if stdout_path:
                    stdout_path.parent.mkdir(parents=True, exist_ok=True)
                    stdout_path.write_text(combined, encoding="utf-8")
                return ExecResult(
                    stdout=check_proc.stdout,
                    stderr=check_proc.stderr,
                    return_code=check_proc.returncode,
                )
            apply_proc = subprocess.run(
                [
                    "git",
                    "-c",
                    "safe.directory=*",
                    "-C",
                    str(self._app_dir),
                    "apply",
                    str(patch_path),
                ],
                env=merged_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            combined = (
                (apply_proc.stdout or "")
                + (apply_proc.stderr or "")
                + ("Applied reference feature patch cleanly.\n" if apply_proc.returncode == 0 else "")
            )
            if stdout_path:
                stdout_path.parent.mkdir(parents=True, exist_ok=True)
                stdout_path.write_text(combined, encoding="utf-8")
            return ExecResult(
                stdout=combined,
                stderr=apply_proc.stderr,
                return_code=apply_proc.returncode,
            )

        if script_path.name == "test.sh":
            # Extract the embedded Python runner block and feature test filename from test.sh
            m_py = re.search(r"<<'PY'\s*\n(.*?)\nPY", script_text, flags=re.DOTALL)
            m_file = re.search(r'"(test_feature_[^"]+\.py)"\s*<<\'PY\'', script_text)
            if not m_py or not m_file:
                raise RuntimeError(f"Could not parse Python test runner block in {script_path}")

            py_code = m_py.group(1)
            feature_test_filename = m_file.group(1)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    py_code,
                    str(self._app_dir),
                    str(self._root / "tests"),
                    str(self._root / "logs" / "verifier"),
                    feature_test_filename,
                ],
                cwd=str(self._app_dir),
                env=merged_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            combined = (proc.stdout or "") + (proc.stderr or "")
            if stdout_path:
                stdout_path.parent.mkdir(parents=True, exist_ok=True)
                stdout_path.write_text(combined, encoding="utf-8")
            return ExecResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
            )

        raise RuntimeError(f"Unsupported shell script in LocalWorktreeEnvironment: {script_path}")

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        assert self._root is not None and self._app_dir is not None
        merged_env = dict(os.environ)
        extra = self._merge_env(env)
        if extra:
            merged_env.update(extra)
        merged_env["PYTHONPATH"] = str((self._app_dir / "src").resolve())
        merged_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

        cmd = command.strip()

        if cmd == "pwd":
            return ExecResult(stdout="/app\n", stderr="", return_code=0)

        if cmd.startswith("chmod "):
            return ExecResult(stdout="", stderr="", return_code=0)

        if cmd.startswith("rm -f"):
            tokens = shlex.split(cmd)
            for tok in tokens[2:]:
                if tok == "--":
                    continue
                target = self._map_container_path(tok)
                if target.is_file() or target.is_symlink():
                    target.unlink(missing_ok=True)
            return ExecResult(stdout="", stderr="", return_code=0)

        if cmd.startswith("test -d ") or cmd.startswith("test -f "):
            tokens = shlex.split(cmd)
            target = self._map_container_path(tokens[2])
            ok = target.is_dir() if tokens[1] == "-d" else target.is_file()
            return ExecResult(stdout="", stderr="", return_code=0 if ok else 1)

        # Match Harbor's build_execution_command: `(script) > stdout 2>&1`
        m_exec = re.match(r"^\((.+)\)\s*>\s*(.+?)\s+2>&1$", cmd)
        if m_exec:
            inner = m_exec.group(1).strip()
            stdout_raw = shlex.split(m_exec.group(2).strip())[0]
            script_raw = shlex.split(inner)[0]
            script_path = self._map_container_path(script_raw)
            stdout_path = self._map_container_path(stdout_raw)
            res = await asyncio.to_thread(
                self._run_shell_script_in_python, script_path, stdout_path, merged_env
            )
        else:
            tokens = shlex.split(cmd)
            if tokens and tokens[0].endswith(".sh"):
                script_path = self._map_container_path(tokens[0])
                res = await asyncio.to_thread(
                    self._run_shell_script_in_python, script_path, None, merged_env
                )
            else:
                work_dir = self._map_container_path(cwd) if cwd else self._app_dir
                proc = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    cwd=str(work_dir),
                    env=merged_env,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout_sec or 300,
                )
                res = ExecResult(
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    return_code=proc.returncode,
                )

        callback = self._output_callback()
        if callback is not None:
            if res.stdout:
                await callback(res.stdout, "stdout")
            if res.stderr:
                await callback(res.stderr, "stderr")
        return res
