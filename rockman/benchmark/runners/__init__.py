"""Runner registry and factory"""

from typing import Dict, Type
from rockman.benchmark.runners.base import BaseRunner
from rockman.benchmark.runners.python_runner import PythonRunner
from rockman.benchmark.runners.cpp_runner import CPPRunner
from rockman.benchmark.runners.java_runner import JavaRunner
from rockman.benchmark.runners.js_runner import JavaScriptRunner
from rockman.benchmark.runners.ts_runner import TypeScriptRunner
from rockman.benchmark.runners.rust_runner import RustRunner
from rockman.benchmark.runners.go_runner import GoRunner


RUNNER_REGISTRY: Dict[str, Type[BaseRunner]] = {
    "python": PythonRunner,
    "py": PythonRunner,
    "cpp": CPPRunner,
    "c++": CPPRunner,
    "cc": CPPRunner,
    "java": JavaRunner,
    "javascript": JavaScriptRunner,
    "js": JavaScriptRunner,
    "typescript": TypeScriptRunner,
    "ts": TypeScriptRunner,
    "rust": RustRunner,
    "rs": RustRunner,
    "go": GoRunner,
    "golang": GoRunner,
}


def get_runner(language: str, time_limit: float = 2.0, memory_limit_mb: int = 256) -> BaseRunner:
    """Get runner instance for a language."""
    lang = language.lower().strip()
    if lang not in RUNNER_REGISTRY:
        raise ValueError(f"Unsupported language: {language}. Supported: {list(RUNNER_REGISTRY.keys())}")
    return RUNNER_REGISTRY[lang](time_limit=time_limit, memory_limit_mb=memory_limit_mb)


def list_supported_languages() -> list[str]:
    """List all supported languages."""
    return sorted(set(RUNNER_REGISTRY.keys()))