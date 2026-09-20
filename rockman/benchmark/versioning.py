"""Version management for Rockman benchmark"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
import json
import hashlib


@dataclass
class BenchmarkVersion:
    version: str
    created_at: str
    task_count: int
    task_ids: List[str]
    description: str = ""
    parent_version: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "task_count": self.task_count,
            "task_ids": self.task_ids,
            "description": self.description,
            "parent_version": self.parent_version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BenchmarkVersion":
        return cls(**data)


class VersionRegistry:
    """Manages benchmark versions and ensures immutability."""

    def __init__(self, registry_path: str = "rockman_versions.json"):
        self.registry_path = registry_path
        self.versions: Dict[str, BenchmarkVersion] = {}
        self._load()

    def _load(self):
        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)
                for v in data.get("versions", []):
                    version = BenchmarkVersion.from_dict(v)
                    self.versions[version.version] = version
        except FileNotFoundError:
            pass

    def _save(self):
        data = {"versions": [v.to_dict() for v in self.versions.values()]}
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def register(self, version: str, task_ids: List[str], description: str = "",
                 parent_version: Optional[str] = None, metadata: Optional[Dict] = None) -> BenchmarkVersion:
        if version in self.versions:
            raise ValueError(f"Version {version} already exists. Use a new version number.")

        if parent_version and parent_version not in self.versions:
            raise ValueError(f"Parent version {parent_version} not found.")

        bv = BenchmarkVersion(
            version=version,
            created_at=datetime.utcnow().isoformat() + "Z",
            task_count=len(task_ids),
            task_ids=sorted(task_ids),
            description=description,
            parent_version=parent_version,
            metadata=metadata or {},
        )
        self.versions[version] = bv
        self._save()
        return bv

    def get(self, version: str) -> Optional[BenchmarkVersion]:
        return self.versions.get(version)

    def list_versions(self) -> List[BenchmarkVersion]:
        return sorted(self.versions.values(), key=lambda v: v.created_at)

    def verify_integrity(self, version: str, current_task_ids: Set[str]) -> bool:
        """Verify that published tasks haven't been modified."""
        bv = self.get(version)
        if not bv:
            return False
        return set(bv.task_ids) == current_task_ids

    def get_task_history(self, task_id: str) -> List[str]:
        """Get all versions containing a task."""
        return [v.version for v in self.versions.values() if task_id in v.task_ids]


def compute_dataset_hash(task_ids: List[str], problem_loader) -> str:
    """Compute hash of dataset for integrity verification."""
    hasher = hashlib.sha256()
    for task_id in sorted(task_ids):
        problem = problem_loader(task_id)
        if problem:
            content = f"{task_id}:{problem.prompt}:{problem.public_test}"
            hasher.update(content.encode())
    return hasher.hexdigest()[:16]


CURRENT_VERSION = "v0.2"
VERSION_HISTORY = {
    "v0.1": {
        "task_count": 200,
        "description": "Initial release with 200 algorithmic challenges",
        "date": "2024-01-15",
    },
    "v0.2": {
        "task_count": 500,
        "description": "Extended with debugging, complexity, stateful, multi-step tasks; multi-language support",
        "date": "2024-09-19",
    },
}


def get_version_info(version: str) -> Dict:
    return VERSION_HISTORY.get(version, {})