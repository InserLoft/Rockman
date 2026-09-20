"""Base runner interface for code execution"""

import subprocess
import tempfile
import os
import time
import resource
import signal
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Tuple
from pathlib import Path


@dataclass
class RunResult:
    success: bool
    stdout: str
    stderr: str
    execution_time_ms: float
    memory_used_mb: float
    error_type: Optional[str] = None
    return_code: int = 0


class BaseRunner(ABC):
    """Abstract base class for language runners."""

    def __init__(self, time_limit: float = 2.0, memory_limit_mb: int = 256):
        self.time_limit = time_limit
        self.memory_limit_mb = memory_limit_mb
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024

    @property
    @abstractmethod
    def language_name(self) -> str:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass

    @abstractmethod
    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        pass

    @abstractmethod
    def get_run_command(self, executable_path: Path) -> List[str]:
        pass

    def compile(self, source_code: str, work_dir: Path) -> Tuple[bool, str, Optional[Path]]:
        """Compile source code. Returns (success, error_message, executable_path)."""
        source_path = work_dir / f"main{self.file_extension}"
        source_path.write_text(source_code, encoding="utf-8")

        output_path = work_dir / "main"
        if self.language_name == "java":
            output_path = work_dir / "Main"
        elif self.language_name in ("python", "javascript", "typescript"):
            return True, "", source_path

        compile_cmd = self.get_compile_command(source_path, output_path)
        try:
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=work_dir,
            )
            if result.returncode != 0:
                return False, result.stderr, None
            return True, "", output_path
        except subprocess.TimeoutExpired:
            return False, "Compilation timeout", None
        except Exception as e:
            return False, str(e), None

    def run(self, executable_path: Path, input_data: str = "") -> RunResult:
        """Run compiled executable with input."""
        run_cmd = self.get_run_command(executable_path)
        start_time = time.perf_counter()

        try:
            if self.language_name == "python":
                proc = subprocess.Popen(
                    run_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=executable_path.parent,
                    preexec_fn=self._set_limits,
                )
            else:
                proc = subprocess.Popen(
                    run_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=executable_path.parent,
                    preexec_fn=self._set_limits,
                )

            try:
                stdout, stderr = proc.communicate(input=input_data, timeout=self.time_limit)
                return_code = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                return RunResult(
                    success=False,
                    stdout=stdout or "",
                    stderr=stderr or "Execution timeout",
                    execution_time_ms=self.time_limit * 1000,
                    memory_used_mb=0,
                    error_type="TimeoutError",
                    return_code=-1,
                )

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            try:
                usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                memory_mb = usage.ru_maxrss / 1024
            except:
                memory_mb = 0

            success = return_code == 0
            error_type = None if success else self._classify_error(return_code, stderr)

            return RunResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                execution_time_ms=execution_time_ms,
                memory_used_mb=memory_mb,
                error_type=error_type,
                return_code=return_code,
            )

        except Exception as e:
            return RunResult(
                success=False,
                stdout="",
                stderr=str(e),
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                memory_used_mb=0,
                error_type=type(e).__name__,
                return_code=-1,
            )

    def _set_limits(self):
        """Set resource limits for child process."""
        try:
            resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit_bytes, self.memory_limit_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (int(self.time_limit) + 1, int(self.time_limit) + 1))
        except:
            pass

    def _classify_error(self, return_code: int, stderr: str) -> str:
        if return_code == -signal.SIGSEGV or "segfault" in stderr.lower():
            return "SegmentationFault"
        if return_code == -signal.SIGKILL or "killed" in stderr.lower():
            return "MemoryLimitExceeded"
        if return_code == -signal.SIGXCPU:
            return "TimeLimitExceeded"
        if "assert" in stderr.lower() and "assertionerror" in stderr.lower():
            return "AssertionError"
        if "error" in stderr.lower() or "exception" in stderr.lower():
            return "RuntimeError"
        return "ExecutionError"

    def execute(self, source_code: str, input_data: str = "") -> RunResult:
        """Full compile + run cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            success, error, executable = self.compile(source_code, work_dir)
            if not success:
                return RunResult(
                    success=False,
                    stdout="",
                    stderr=error,
                    execution_time_ms=0,
                    memory_used_mb=0,
                    error_type="CompilationError",
                    return_code=-1,
                )
            return self.run(executable, input_data)