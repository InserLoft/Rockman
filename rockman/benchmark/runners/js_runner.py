"""JavaScript/Node.js code runner"""

from pathlib import Path
from typing import List
from rockman.benchmark.runners.base import BaseRunner


class JavaScriptRunner(BaseRunner):
    """Runner for JavaScript code (Node.js)."""

    @property
    def language_name(self) -> str:
        return "javascript"

    @property
    def file_extension(self) -> str:
        return ".js"

    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        return ["node", "--check", str(source_path)]

    def get_run_command(self, executable_path: Path) -> List[str]:
        return ["node", "--max-old-space-size={}".format(self.memory_limit_mb), str(executable_path)]