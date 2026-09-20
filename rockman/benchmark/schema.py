"""Core data schemas for Rockman Benchmark v0.2+"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json
from datetime import datetime


class TaskType(str, Enum):
    GENERATION = "generation"
    DEBUGGING = "debugging"
    COMPLETION = "completion"
    REFACTORING = "refactoring"
    OPTIMIZATION = "optimization"
    API_IMPLEMENTATION = "api_implementation"
    PARSING = "parsing"
    FILE_IO = "file_io"
    STATEFUL = "stateful"
    MULTI_STEP = "multi_step"


class Language(str, Enum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"


class SourceType(str, Enum):
    ORIGINAL = "original"
    ADAPTED = "adapted"
    GENERATED = "generated"
    CONTRIBUTED = "contributed"


class DifficultyLevel(int, Enum):
    INTRODUCTORY = 1
    EASY = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    HARD = 5
    EXPERT = 6
    RESEARCH = 7


@dataclass
class TestCase:
    input_data: str
    expected_output: str
    description: str = ""
    is_hidden: bool = False
    timeout_override: Optional[float] = None
    memory_override: Optional[int] = None


@dataclass
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    error_type: Optional[str] = None
    error_message: str = ""
    passed_tests: int = 0
    total_tests: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_time_ms": self.execution_time_ms,
            "memory_used_mb": self.memory_used_mb,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "passed_tests": self.passed_tests,
            "total_tests": self.total_tests,
        }


@dataclass
class Problem:
    task_id: str
    category: str
    subcategory: str
    difficulty: int
    prompt: str
    public_test: str
    hidden_test_encrypted: str = ""
    hidden_test_nonce: str = ""
    hidden_test_tag: str = ""
    time_limit: float = 2.0
    memory_limit: int = 256
    language: str = "python"
    tags: List[str] = field(default_factory=list)
    source_type: str = "original"
    expected_complexity: str = ""
    deterministic: bool = True
    task_type: str = "generation"
    version: str = "v0.2"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Contamination tracking metadata
    creation_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    publication_date: Optional[str] = None
    source_url: Optional[str] = None
    source_license: Optional[str] = None
    derived_from: List[str] = field(default_factory=list)  # Original problem IDs if adapted
    generation_method: Optional[str] = None  # "synthetic", "human", "llm", "template"
    generator_version: Optional[str] = None
    content_hash: str = ""  # SHA256 of prompt+tests for integrity
    canary: str = ""  # Unique canary string for contamination detection

    def __post_init__(self):
        from datetime import datetime
        if isinstance(self.difficulty, DifficultyLevel):
            self.difficulty = self.difficulty.value
        if isinstance(self.task_type, TaskType):
            self.task_type = self.task_type.value
        if isinstance(self.language, Language):
            self.language = self.language.value
        if isinstance(self.source_type, SourceType):
            self.source_type = self.source_type.value
        
        # Auto-generate content hash if not present
        if not self.content_hash:
            self.content_hash = self._compute_content_hash()
        
        # Auto-generate canary if not present
        if not self.canary:
            self.canary = self._generate_canary()
    
    def _compute_content_hash(self) -> str:
        import hashlib
        content = f"{self.prompt}:{self.public_test}:{self.hidden_test_encrypted}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _generate_canary(self) -> str:
        import hashlib
        # Canary includes creation date for temporal uniqueness
        seed = f"{self.task_id}:{self.content_hash}:{self.creation_date}"
        return "ROCKMAN_CANARY_" + hashlib.sha256(seed.encode()).hexdigest()[:16]
    
    def verify_integrity(self) -> bool:
        """Verify content hasn't been modified."""
        return self.content_hash == self._compute_content_hash()
    
    def check_contamination(self, text: str) -> bool:
        """Check if text contains this problem's canary."""
        return self.canary in text

    def to_dict(self, include_hidden: bool = False) -> Dict[str, Any]:
        d = {
            "task_id": self.task_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "difficulty": self.difficulty,
            "prompt": self.prompt,
            "public_test": self.public_test,
            "time_limit": self.time_limit,
            "memory_limit": self.memory_limit,
            "language": self.language,
            "tags": self.tags,
            "source_type": self.source_type,
            "expected_complexity": self.expected_complexity,
            "deterministic": self.deterministic,
            "task_type": self.task_type,
            "version": self.version,
            "metadata": self.metadata,
            # Contamination tracking
            "creation_date": self.creation_date,
            "publication_date": self.publication_date,
            "source_url": self.source_url,
            "source_license": self.source_license,
            "derived_from": self.derived_from,
            "generation_method": self.generation_method,
            "generator_version": self.generator_version,
            "content_hash": self.content_hash,
            "canary": self.canary,
        }
        if include_hidden:
            d.update({
                "hidden_test_encrypted": self.hidden_test_encrypted,
                "hidden_test_nonce": self.hidden_test_nonce,
                "hidden_test_tag": self.hidden_test_tag,
            })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Problem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_jsonl(self, include_hidden: bool = False) -> str:
        return json.dumps(self.to_dict(include_hidden), ensure_ascii=False)


@dataclass
class RockmanScore:
    overall: float
    by_difficulty: Dict[int, float] = field(default_factory=dict)
    by_category: Dict[str, float] = field(default_factory=dict)
    by_subcategory: Dict[str, float] = field(default_factory=dict)
    by_task_type: Dict[str, float] = field(default_factory=dict)
    by_language: Dict[str, float] = field(default_factory=dict)
    efficiency_score: float = 0.0
    robustness_score: float = 0.0
    total_tasks: int = 0
    passed_tasks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "by_difficulty": self.by_difficulty,
            "by_category": self.by_category,
            "by_subcategory": self.by_subcategory,
            "by_task_type": self.by_task_type,
            "by_language": self.by_language,
            "efficiency_score": self.efficiency_score,
            "robustness_score": self.robustness_score,
            "total_tasks": self.total_tasks,
            "passed_tasks": self.passed_tasks,
        }

    def format_leaderboard(self) -> str:
        lines = [
            "Rockman Score",
            "─────────────",
            f"Overall:        {self.overall:.1f}%",
            f"Tasks Passed:   {self.passed_tasks}/{self.total_tasks}",
            "",
            "By Difficulty:",
        ]
        for d in sorted(self.by_difficulty.keys()):
            lines.append(f"  Level {d}:       {self.by_difficulty[d]:.1f}%")
        lines.append("")
        lines.append("By Category:")
        for cat in sorted(self.by_category.keys()):
            lines.append(f"  {cat:<25} {self.by_category[cat]:.1f}%")
        lines.append("")
        lines.append("By Task Type:")
        for tt in sorted(self.by_task_type.keys()):
            lines.append(f"  {tt:<20} {self.by_task_type[tt]:.1f}%")
        if self.by_language:
            lines.append("")
            lines.append("By Language:")
            for lang in sorted(self.by_language.keys()):
                lines.append(f"  {lang:<15} {self.by_language[lang]:.1f}%")
        lines.append("")
        lines.append(f"Efficiency:     {self.efficiency_score:.1f}%")
        lines.append(f"Robustness:     {self.robustness_score:.1f}%")
        return "\n".join(lines)


@dataclass
class ModelEvaluation:
    model_name: str
    model_version: str
    benchmark_version: str
    temperature: float
    max_tokens: int
    num_attempts: int
    hardware: str
    date: str
    score: RockmanScore
    raw_results: Dict[str, List[ExecutionResult]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "benchmark_version": self.benchmark_version,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "num_attempts": self.num_attempts,
            "hardware": self.hardware,
            "date": self.date,
            "score": self.score.to_dict(),
        }