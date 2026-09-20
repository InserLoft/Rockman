"""Container-based sandbox for secure code execution"""

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

import tempfile
import os
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

from rockman.benchmark.runners.base import BaseRunner, RunResult


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    image: str = "rockman-sandbox:latest"
    cpu_limit: float = 1.0  # CPU cores
    memory_limit_mb: int = 256
    timeout_seconds: float = 30.0
    network_disabled: bool = True
    read_only_rootfs: bool = True
    tmpfs_size_mb: int = 64
    pids_limit: int = 64
    user: str = "nobody"
    working_dir: str = "/workspace"


@dataclass
class ContainerResult:
    """Result from container execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    memory_used_mb: float
    oom_killed: bool = False
    timeout: bool = False


class ContainerSandbox:
    """Docker-based sandbox for secure code execution."""

    def __init__(self, config: SandboxConfig = None):
        if not DOCKER_AVAILABLE:
            raise RuntimeError("Docker SDK not available. Install with: pip install docker")
        self.config = config or SandboxConfig()
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Docker daemon: {e}")

    def _ensure_image(self):
        """Ensure the sandbox image exists, build if necessary."""
        try:
            self.client.images.get(self.config.image)
        except docker.errors.ImageNotFound:
            self._build_image()

    def _build_image(self):
        """Build the sandbox Docker image with all language runtimes."""
        dockerfile = f"""
FROM ubuntu:22.04

# Install language runtimes
RUN apt-get update && apt-get install -y --no-install-recommends \\
    python3 python3-pip \\
    openjdk-17-jdk-headless \\
    nodejs npm \\
    golang-go \\
    rustc cargo \\
    g++ make \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash nobody

WORKDIR /workspace
USER nobody
"""
        print(f"Building sandbox image: {self.config.image}...")
        try:
            self.client.images.build(
                fileobj=tempfile.BytesIO(dockerfile.encode()),
                tag=self.config.image,
                rm=True,
            )
            print("Sandbox image built successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to build sandbox image: {e}")

    def execute(
        self,
        source_code: str,
        language: str,
        input_data: str = "",
        config: SandboxConfig = None
    ) -> ContainerResult:
        """Execute code in container."""
        cfg = config or self.config
        self._ensure_image()

        # Create temp directory with source code
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Write source file
            ext = self._get_extension(language)
            source_file = workspace / f"main{ext}"
            source_file.write_text(source_code, encoding="utf-8")

            # Write input file if provided
            input_file = None
            if input_data:
                input_file = workspace / "input.txt"
                input_file.write_text(input_data, encoding="utf-8")

            # Prepare volume mount
            volumes = {
                str(workspace): {"bind": "/workspace", "mode": "rw"}
            }

            # Build command
            cmd = self._get_run_command(language, source_file.name)

            # Container configuration
            container_config = {
                "image": cfg.image,
                "command": cmd,
                "volumes": volumes,
                "working_dir": cfg.working_dir,
                "user": cfg.user,
                "mem_limit": f"{cfg.memory_limit_mb}m",
                "memswap_limit": f"{cfg.memory_limit_mb}m",
                "cpu_quota": int(cfg.cpu_limit * 100000),
                "cpu_period": 100000,
                "network_disabled": cfg.network_disabled,
                "read_only": cfg.read_only_rootfs,
                "tmpfs": {"/tmp": f"size={cfg.tmpfs_size_mb}m"},
                "pids_limit": cfg.pids_limit,
                "detach": True,
                "stdout": True,
                "stderr": True,
            }

            # Run container
            start_time = time.perf_counter()
            container = None
            try:
                container = self.client.containers.run(**container_config)
                
                # Wait with timeout
                try:
                    exit_code = container.wait(timeout=cfg.timeout_seconds)["StatusCode"]
                    timeout = False
                except Exception:
                    container.kill()
                    timeout = True
                    exit_code = -1

                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

                # Get stats
                stats = container.stats(stream=False)
                memory_mb = self._parse_memory_stats(stats)

                execution_time_ms = (time.perf_counter() - start_time) * 1000

                return ContainerResult(
                    success=exit_code == 0 and not timeout,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time_ms=execution_time_ms,
                    memory_used_mb=memory_mb,
                    oom_killed="OOMKilled" in str(container.attrs.get("State", {})),
                    timeout=timeout,
                )

            except Exception as e:
                return ContainerResult(
                    success=False,
                    stdout="",
                    stderr=str(e),
                    exit_code=-1,
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    memory_used_mb=0,
                )
            finally:
                if container:
                    try:
                        container.remove(force=True)
                    except:
                        pass

    def _get_extension(self, language: str) -> str:
        extensions = {
            "python": ".py",
            "py": ".py",
            "cpp": ".cpp",
            "c++": ".cpp",
            "cc": ".cc",
            "java": ".java",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "rust": ".rs",
            "go": ".go",
        }
        return extensions.get(language.lower(), ".txt")

    def _get_run_command(self, language: str, filename: str) -> List[str]:
        lang = language.lower()
        
        if lang in ("python", "py"):
            return ["python3", filename]
        elif lang in ("cpp", "c++", "cc"):
            return ["sh", "-c", f"g++ -std=c++17 -O2 -pipe -static -s {filename} -o main && ./main"]
        elif lang == "java":
            return ["sh", "-c", f"javac {filename} && java -Xmx{self.config.memory_limit_mb}m -cp . Main"]
        elif lang in ("javascript", "js"):
            return ["node", f"--max-old-space-size={self.config.memory_limit_mb}", filename]
        elif lang in ("typescript", "ts"):
            return ["sh", "-c", f"tsc {filename} && node --max-old-space-size={self.config.memory_limit_mb} {filename.replace('.ts', '.js')}"]
        elif lang == "rust":
            return ["sh", "-c", f"rustc -C opt-level=3 {filename} -o main && ./main"]
        elif lang == "go":
            return ["sh", "-c", f"go build -ldflags='-s -w' -o main {filename} && ./main"]
        else:
            return ["cat", filename]

    def _parse_memory_stats(self, stats: Dict) -> float:
        """Parse memory usage from Docker stats."""
        try:
            mem_usage = stats["memory_stats"].get("usage", 0)
            return mem_usage / (1024 * 1024)
        except:
            return 0.0

    def close(self):
        """Close Docker client."""
        if self.client:
            self.client.close()


class HybridRunner(BaseRunner):
    """Runner that uses container sandbox when available, falls back to local."""

    def __init__(
        self, 
        language: str, 
        time_limit: float = 2.0, 
        memory_limit_mb: int = 256,
        use_container: bool = True
    ):
        super().__init__(time_limit, memory_limit_mb)
        self.language = language
        self.use_container = use_container
        self.sandbox = None
        if use_container:
            try:
                self.sandbox = ContainerSandbox(SandboxConfig(
                    cpu_limit=1.0,
                    memory_limit_mb=memory_limit_mb,
                    timeout_seconds=time_limit + 5,
                ))
            except Exception as e:
                print(f"Container sandbox unavailable, falling back to local: {e}")
                self.use_container = False

    @property
    def language_name(self) -> str:
        return self.language

    @property
    def file_extension(self) -> str:
        # Delegate to appropriate runner
        from rockman.benchmark.runners import get_runner
        fallback = get_runner(self.language, self.time_limit, self.memory_limit_mb)
        return fallback.file_extension

    def get_compile_command(self, source_path: Path, output_path: Path) -> List[str]:
        from rockman.benchmark.runners import get_runner
        fallback = get_runner(self.language, self.time_limit, self.memory_limit_mb)
        return fallback.get_compile_command(source_path, output_path)

    def get_run_command(self, executable_path: Path) -> List[str]:
        from rockman.benchmark.runners import get_runner
        fallback = get_runner(self.language, self.time_limit, self.memory_limit_mb)
        return fallback.get_run_command(executable_path)

    def execute(self, source_code: str, input_data: str = "") -> RunResult:
        if self.use_container and self.sandbox:
            try:
                result = self.sandbox.execute(
                    source_code, 
                    self.language, 
                    input_data,
                    SandboxConfig(
                        memory_limit_mb=self.memory_limit_mb,
                        timeout_seconds=self.time_limit + 5,
                    )
                )
                return RunResult(
                    success=result.success,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    execution_time_ms=result.execution_time_ms,
                    memory_used_mb=result.memory_used_mb,
                    error_type=self._classify_container_error(result),
                    return_code=result.exit_code,
                )
            except Exception as e:
                print(f"Container execution failed, falling back: {e}")
                self.use_container = False

        # Fallback to local execution
        from rockman.benchmark.runners import get_runner
        fallback = get_runner(self.language, self.time_limit, self.memory_limit_mb)
        return fallback.execute(source_code, input_data)

    def _classify_container_error(self, result: ContainerResult) -> Optional[str]:
        if result.success:
            return None
        if result.timeout:
            return "TimeoutError"
        if result.oom_killed:
            return "MemoryLimitExceeded"
        if result.exit_code == -1:
            return "ExecutionError"
        if "assert" in result.stderr.lower() and "assertionerror" in result.stderr.lower():
            return "AssertionError"
        return "RuntimeError"


def get_hybrid_runner(language: str, time_limit: float = 2.0, memory_limit_mb: int = 256, use_container: bool = True) -> HybridRunner:
    """Get a hybrid runner that uses container sandbox when available."""
    return HybridRunner(language, time_limit, memory_limit_mb, use_container)