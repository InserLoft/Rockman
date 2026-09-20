"""Determinism tracking and reproducibility utilities"""

import os
import sys
import platform
import subprocess
import json
import hashlib
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager


@dataclass
class ExecutionEnvironment:
    """Complete execution environment snapshot for reproducibility."""
    # System info
    os: str
    os_version: str
    architecture: str
    hostname: str
    python_version: str
    python_implementation: str
    
    # Compiler/interpreter versions
    gcc_version: Optional[str] = None
    clang_version: Optional[str] = None
    javac_version: Optional[str] = None
    java_version: Optional[str] = None
    node_version: Optional[str] = None
    npm_version: Optional[str] = None
    rustc_version: Optional[str] = None
    cargo_version: Optional[str] = None
    go_version: Optional[str] = None
    
    # Hardware
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    total_memory_gb: Optional[float] = None
    
    # Environment
    environment_variables: Dict[str, str] = field(default_factory=dict)
    working_directory: str = ""
    
    # Timestamps
    captured_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    # Random seeds
    python_seed: Optional[int] = None
    numpy_seed: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def capture(cls) -> "ExecutionEnvironment":
        """Capture current execution environment."""
        env = cls(
            os=platform.system(),
            os_version=platform.version(),
            architecture=platform.machine(),
            hostname=platform.node(),
            python_version=platform.python_version(),
            python_implementation=platform.python_implementation(),
            working_directory=os.getcwd(),
        )
        
        # Capture compiler versions
        env.gcc_version = cls._run_version(["gcc", "--version"])
        env.clang_version = cls._run_version(["clang", "--version"])
        env.javac_version = cls._run_version(["javac", "-version"])
        env.java_version = cls._run_version(["java", "-version"])
        env.node_version = cls._run_version(["node", "--version"])
        env.npm_version = cls._run_version(["npm", "--version"])
        env.rustc_version = cls._run_version(["rustc", "--version"])
        env.cargo_version = cls._run_version(["cargo", "--version"])
        env.go_version = cls._run_version(["go", "version"])
        
        # Capture hardware info
        env.cpu_model = cls._get_cpu_model()
        env.cpu_cores = os.cpu_count()
        env.total_memory_gb = cls._get_total_memory_gb()
        
        # Capture relevant environment variables
        relevant_vars = [
            "PATH", "PYTHONPATH", "JAVA_HOME", "GOROOT", "RUSTUP_HOME",
            "CARGO_HOME", "NODE_PATH", "PYTHONHASHSEED",
            "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        ]
        for var in relevant_vars:
            if var in os.environ:
                env.environment_variables[var] = os.environ[var]
        
        return env
    
    @staticmethod
    def _run_version(cmd: List[str]) -> Optional[str]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Return first line only
                return result.stdout.strip().split('\n')[0]
            if result.stderr:
                return result.stderr.strip().split('\n')[0]
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_cpu_model() -> Optional[str]:
        try:
            if platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if line.startswith("model name"):
                            return line.split(":")[1].strip()
            elif platform.system() == "Darwin":
                result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_total_memory_gb() -> Optional[float]:
        try:
            if platform.system() == "Linux":
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            return kb / (1024 * 1024)
            elif platform.system() == "Darwin":
                result = subprocess.run(["sysctl", "-n", "hw.memsize"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return int(result.stdout.strip()) / (1024 ** 3)
        except Exception:
            pass
        return None


@dataclass
class DeterministicExecution:
    """Record of a deterministic execution."""
    task_id: str
    language: str
    source_hash: str  # Hash of source code
    environment: ExecutionEnvironment
    
    # Seeds
    seeds: Dict[str, int] = field(default_factory=dict)
    
    # Execution results (multiple runs)
    runs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Determinism verification
    is_deterministic: bool = True
    nondeterminism_reasons: List[str] = field(default_factory=list)
    
    def add_run(self, result: Dict[str, Any]):
        """Add a run result and check determinism."""
        self.runs.append(result)
        if len(self.runs) >= 2:
            self._verify_determinism()
    
    def _verify_determinism(self):
        """Check if all runs produced identical results."""
        if len(self.runs) < 2:
            return
        
        first = self.runs[0]
        for i, run in enumerate(self.runs[1:], 2):
            # Compare key fields
            for key in ["success", "stdout", "stderr", "exit_code"]:
                if run.get(key) != first.get(key):
                    self.is_deterministic = False
                    self.nondeterminism_reasons.append(
                        f"Run {i}: {key} differs (run1={first.get(key)}, run{i}={run.get(key)})"
                    )
            
            # Allow small timing differences
            time_diff = abs(run.get("execution_time_ms", 0) - first.get("execution_time_ms", 0))
            if time_diff > 100:  # >100ms difference
                self.nondeterminism_reasons.append(
                    f"Run {i}: execution time differs by {time_diff:.1f}ms"
                )


class DeterminismTracker:
    """Tracks and enforces deterministic execution."""
    
    def __init__(self):
        self.executions: Dict[str, DeterministicExecution] = {}
        self.global_seeds: Dict[str, int] = {}
    
    def set_global_seeds(self, seed: int = 42):
        """Set all random seeds for reproducibility."""
        self.global_seeds = {
            "python": seed,
            "numpy": seed,
            "random": seed,
        }
        random.seed(seed)
        os.environ["PYTHONHASHSEED"] = str(seed)
        
        try:
            import numpy as np
            np.random.seed(seed)
            self.global_seeds["numpy"] = seed
        except ImportError:
            pass
    
    def get_seeds(self) -> Dict[str, int]:
        """Get current seed values."""
        seeds = {"python": random.getstate()[1][0] if hasattr(random, 'getstate') else 0}
        seeds.update(self.global_seeds)
        try:
            import numpy as np
            seeds["numpy"] = int(np.random.get_state()[1][0])
        except:
            pass
        return seeds
    
    @contextmanager
    def deterministic_context(self, seed: int = 42):
        """Context manager for deterministic execution."""
        # Save state
        py_state = random.getstate()
        old_hashseed = os.environ.get("PYTHONHASHSEED")
        
        # Set seeds
        self.set_global_seeds(seed)
        
        try:
            yield
        finally:
            # Restore state
            random.setstate(py_state)
            if old_hashseed is not None:
                os.environ["PYTHONHASHSEED"] = old_hashseed
            else:
                os.environ.pop("PYTHONHASHSEED", None)
    
    def record_execution(
        self, 
        task_id: str, 
        language: str, 
        source_code: str,
        environment: ExecutionEnvironment = None,
        num_runs: int = 3
    ) -> DeterministicExecution:
        """Record a deterministic execution with multiple runs."""
        from rockman.benchmark.runners import get_runner
        
        source_hash = hashlib.sha256(source_code.encode()).hexdigest()[:16]
        exec_key = f"{task_id}:{language}:{source_hash}"
        
        if environment is None:
            environment = ExecutionEnvironment.capture()
        
        execution = DeterministicExecution(
            task_id=task_id,
            language=language,
            source_hash=source_hash,
            environment=environment,
            seeds=self.get_seeds(),
        )
        
        runner = get_runner(language, time_limit=5.0, memory_limit_mb=256)
        
        for run_idx in range(num_runs):
            with self.deterministic_context(self.global_seeds.get("python", 42) + run_idx):
                result = runner.execute(source_code)
                execution.add_run({
                    "run_index": run_idx,
                    "success": result.success,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.return_code,
                    "execution_time_ms": result.execution_time_ms,
                    "memory_used_mb": result.memory_used_mb,
                })
        
        self.executions[exec_key] = execution
        return execution
    
    def get_determinism_report(self) -> Dict[str, Any]:
        """Generate determinism report for all tracked executions."""
        total = len(self.executions)
        deterministic = sum(1 for e in self.executions.values() if e.is_deterministic)
        
        report = {
            "total_executions": total,
            "deterministic": deterministic,
            "non_deterministic": total - deterministic,
            "determinism_rate": deterministic / total if total > 0 else 1.0,
            "details": {},
        }
        
        for key, exec in self.executions.items():
            report["details"][key] = {
                "is_deterministic": exec.is_deterministic,
                "num_runs": len(exec.runs),
                "reasons": exec.nondeterminism_reasons,
                "seeds": exec.seeds,
            }
        
        return report
    
    def save_report(self, filepath: str):
        """Save determinism report to JSON."""
        report = self.get_determinism_report()
        # Convert ExecutionEnvironment to dict
        for key, detail in report["details"].items():
            if "environment" in detail:
                detail["environment"] = detail["environment"].to_dict() if hasattr(detail["environment"], "to_dict") else detail["environment"]
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)


def capture_environment() -> Dict[str, Any]:
    """Convenience function to capture full environment."""
    env = ExecutionEnvironment.capture()
    return env.to_dict()


def verify_deterministic(
    source_code: str,
    language: str,
    num_runs: int = 5,
    seed: int = 42
) -> Dict[str, Any]:
    """Verify if code execution is deterministic."""
    tracker = DeterminismTracker()
    env = ExecutionEnvironment.capture()
    execution = tracker.record_execution(
        task_id="verify",
        language=language,
        source_code=source_code,
        environment=env,
        num_runs=num_runs
    )
    return {
        "is_deterministic": execution.is_deterministic,
        "num_runs": num_runs,
        "reasons": execution.nondeterminism_reasons,
        "sample_outputs": [r.get("stdout", "")[:100] for r in execution.runs[:3]],
    }


def create_reproducibility_manifest(
    problems: List["Problem"],
    model_name: str,
    model_version: str,
    output_path: str
) -> Dict[str, Any]:
    """Create a reproducibility manifest for a benchmark run."""
    from rockman.benchmark.schema import Problem
    
    env = ExecutionEnvironment.capture()
    
    manifest = {
        "benchmark_version": problems[0].version if problems else "unknown",
        "model_name": model_name,
        "model_version": model_version,
        "execution_environment": env.to_dict(),
        "problems": [
            {
                "task_id": p.task_id,
                "content_hash": p.content_hash,
                "canary": p.canary,
                "creation_date": p.creation_date,
                "source_type": p.source_type,
            }
            for p in problems
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    return manifest