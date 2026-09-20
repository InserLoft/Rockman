"""Rust code runner"""

from pathlib import Path
from typing import List
from rockman.benchmark.runners.base import BaseRunner
import subprocess


class RustRunner(BaseRunner):
    """Runner for Rust code."""

    @property
    def language_name(self) -> str:
        return "rust"

    @property
    def file_extension(self) -> str:
        return ".rs"

    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        return ["rustc", "-C", "opt-level=3", str(source_path), "-o", str(output_path)]

    def get_run_command(self, executable_path: Path) -> List[str]:
        return [str(executable_path)]

    def compile(self, source_code: str, work_dir: Path):
        """Rust needs a proper main function and sometimes Cargo.toml for dependencies."""
        source_path = work_dir / "main.rs"
        source_path.write_text(source_code, encoding="utf-8")

        output_path = work_dir / "main"
        compile_cmd = self.get_compile_command(source_path, output_path)
        try:
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=work_dir,
            )
            if result.returncode != 0:
                return False, result.stderr, None
            return True, "", output_path
        except subprocess.TimeoutExpired:
            return False, "Compilation timeout", None
        except Exception as e:
            return False, str(e), None