"""TypeScript code runner"""

from pathlib import Path
from typing import List
from rockman.benchmark.runners.base import BaseRunner


class TypeScriptRunner(BaseRunner):
    """Runner for TypeScript code (via ts-node or compiled)."""

    @property
    def language_name(self) -> str:
        return "typescript"

    @property
    def file_extension(self) -> str:
        return ".ts"

    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        return ["tsc", "--noEmit", str(source_path)]

    def get_run_command(self, executable_path: Path) -> List[str]:
        return ["ts-node", "--transpile-only", str(executable_path)]