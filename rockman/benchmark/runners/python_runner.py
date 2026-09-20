"""Python code runner"""

import subprocess
import sys
from pathlib import Path
from typing import List
from rockman.benchmark.runners.base import BaseRunner, RunResult


class PythonRunner(BaseRunner):
    """Runner for Python code."""

    @property
    def language_name(self) -> str:
        return "python"

    @property
    def file_extension(self) -> str:
        return ".py"

    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        return [sys.executable, "-m", "py_compile", str(source_path)]

    def get_run_command(self, executable_path: Path) -> List[str]:
        return [sys.executable, str(executable_path)]

    def execute(self, source_code: str, input_data: str = "") -> RunResult:
        """Execute Python code directly without temp file for speed."""
        import tempfile
        import time
        import resource
        import signal

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_path = Path(f.name)

        try:
            start_time = time.perf_counter()
            proc = subprocess.Popen(
                [sys.executable, str(temp_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
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
        finally:
            temp_path.unlink(missing_ok=True)