"""C++ code runner"""

from pathlib import Path
from typing import List
from rockman.benchmark.runners.base import BaseRunner


class CPPRunner(BaseRunner):
    """Runner for C++ code."""

    @property
    def language_name(self) -> str:
        return "cpp"

    @property
    def file_extension(self) -> str:
        return ".cpp"

    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        return [
            "g++",
            "-std=c++17",
            "-O2",
            "-pipe",
            "-static",
            "-s",
            str(source_path),
            "-o",
            str(output_path),
        ]

    def get_run_command(self, executable_path: Path) -> List[str]:
        return [str(executable_path)]