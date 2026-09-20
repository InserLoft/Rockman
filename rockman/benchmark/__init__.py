"""Rockman Benchmark - Core Evaluation Engine"""

from rockman.benchmark.schema import (
    Problem,
    TestCase,
    ExecutionResult,
    RockmanScore,
    ModelEvaluation,
    TaskType,
    Language,
    SourceType,
    DifficultyLevel,
)

from rockman.benchmark.encryption import HiddenTestEncryption, create_encryption_from_env
from rockman.benchmark.runners import get_runner, list_supported_languages
from rockman.benchmark.evaluator import Evaluator, get_handler, EvaluationResult
from rockman.benchmark.metrics import (
    estimate_pass_at_k,
    aggregate_scores,
    calculate_pass_at_k_per_problem,
    BenchmarkReport,
    format_leaderboard_row,
    print_leaderboard_header,
)
from rockman.benchmark.versioning import VersionRegistry, BenchmarkVersion, CURRENT_VERSION
from rockman.benchmark.sandbox import (
    SandboxConfig,
    ContainerResult,
    HybridRunner,
    get_hybrid_runner,
)
try:
    from rockman.benchmark.sandbox import ContainerSandbox
except ImportError:
    ContainerSandbox = None
    pass
from rockman.benchmark.determinism import (
    ExecutionEnvironment,
    DeterministicExecution,
    DeterminismTracker,
    capture_environment,
    verify_deterministic,
    create_reproducibility_manifest,
)

__all__ = [
    "Problem",
    "TestCase",
    "ExecutionResult",
    "RockmanScore",
    "ModelEvaluation",
    "TaskType",
    "Language",
    "SourceType",
    "DifficultyLevel",
    "HiddenTestEncryption",
    "create_encryption_from_env",
    "get_runner",
    "list_supported_languages",
    "Evaluator",
    "get_handler",
    "EvaluationResult",
    "estimate_pass_at_k",
    "aggregate_scores",
    "calculate_pass_at_k_per_problem",
    "BenchmarkReport",
    "format_leaderboard_row",
    "print_leaderboard_header",
    "VersionRegistry",
    "BenchmarkVersion",
    "CURRENT_VERSION",
    "SandboxConfig",
    "ContainerResult",
    "HybridRunner",
    "get_hybrid_runner",
    "ExecutionEnvironment",
    "DeterministicExecution",
    "DeterminismTracker",
    "capture_environment",
    "verify_deterministic",
    "create_reproducibility_manifest",
]

# Conditionally add ContainerSandbox if docker is available
try:
    from rockman.benchmark.sandbox import ContainerSandbox
    __all__.append("ContainerSandbox")
except ImportError:
    pass

__version__ = "0.2.0"