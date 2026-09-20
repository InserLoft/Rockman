"""Java code runner"""

from pathlib import Path
from typing import List
from rockman.benchmark.runners.base import BaseRunner


class JavaRunner(BaseRunner):
    """Runner for Java code."""

    @property
    def language_name(self) -> str:
        return "java"

    @property
    def file_extension(self) -> str:
        return ".java"

    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        return ["javac", str(source_path)]

    def get_run_command(self, executable_path: Path) -> List[str]:
        return ["java", "-Xmx{}m".format(self.memory_limit_mb), "-cp", str(executable_path.parent), "Main"]

    def compile(self, source_code: str, work_dir: Path):
        """Java requires class name to match filename."""
        source_path = work_dir / "Main.java"
        source_path.write_text(source_code, encoding="utf-8")

        compile_cmd = self.get_compile_command(source_path, work_dir / "Main")
        import subprocess
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
            return True, "", work_dir / "Main.class"
        except subprocess.TimeoutExpired:
            return False, "Compilation timeout", None
        except Exception as e:
            return False, str(e), None