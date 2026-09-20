"""Dataset split management for Rockman benchmark"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from rockman.benchmark.schema import Problem


@dataclass
class DatasetSplit:
    name: str
    task_ids: List[str]
    description: str
    is_public: bool = False
    version: str = "v0.2"


class SplitManager:
    """Manages public/private/hidden dataset splits."""

    def __init__(self, base_path: str = "rockman_splits"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.splits: Dict[str, DatasetSplit] = {}
        self._load_splits()

    def _load_splits(self):
        for split_file in self.base_path.glob("split_*.json"):
            with open(split_file) as f:
                data = json.load(f)
                split = DatasetSplit(**data)
                self.splits[split.name] = split

    def create_split(self, name: str, task_ids: List[str], description: str,
                     is_public: bool = False, version: str = "v0.2") -> DatasetSplit:
        split = DatasetSplit(name, task_ids, description, is_public, version)
        self.splits[name] = split
        self._save_split(split)
        return split

    def _save_split(self, split: DatasetSplit):
        split_file = self.base_path / f"split_{split.name}.json"
        with open(split_file, "w") as f:
            json.dump({
                "name": split.name,
                "task_ids": split.task_ids,
                "description": split.description,
                "is_public": split.is_public,
                "version": split.version,
            }, f, indent=2)

    def get_split(self, name: str) -> Optional[DatasetSplit]:
        return self.splits.get(name)

    def list_splits(self) -> List[DatasetSplit]:
        return list(self.splits.values())

    def filter_problems(self, problems: List[Problem], split_name: str) -> List[Problem]:
        split = self.get_split(split_name)
        if not split:
            return problems
        task_id_set = set(split.task_ids)
        return [p for p in problems if p.task_id in task_id_set]

    def export_public_dataset(self, problems: List[Problem], output_path: str,
                              split_name: str = "public", include_hidden: bool = False):
        """Export dataset for public release (no hidden tests)."""
        split = self.get_split(split_name)
        if not split:
            raise ValueError(f"Split {split_name} not found")

        filtered = self.filter_problems(problems, split_name)
        with open(output_path, "w", encoding="utf-8") as f:
            for problem in filtered:
                f.write(problem.to_jsonl(include_hidden=include_hidden) + "\n")

    def export_private_dataset(self, problems: List[Problem], output_path: str,
                               split_name: str = "private", master_secret: str = None):
        """Export dataset with encrypted hidden tests for evaluation server."""
        from rockman.benchmark.encryption import HiddenTestEncryption
        encryption = HiddenTestEncryption(master_secret) if master_secret else None

        split = self.get_split(split_name)
        if not split:
            raise ValueError(f"Split {split_name} not found")

        filtered = self.filter_problems(problems, split_name)
        with open(output_path, "w", encoding="utf-8") as f:
            for problem in filtered:
                if encryption and problem.metadata.get("_hidden_test_raw"):
                    problem = encryption.encrypt_problem_hidden_tests(problem)
                f.write(problem.to_jsonl(include_hidden=True) + "\n")

    def export_hidden_dataset(self, problems: List[Problem], output_path: str,
                              split_name: str = "hidden"):
        """Export held-out evaluation set (never published)."""
        split = self.get_split(split_name)
        if not split:
            raise ValueError(f"Split {split_name} not found")

        filtered = self.filter_problems(problems, split_name)
        with open(output_path, "w", encoding="utf-8") as f:
            for problem in filtered:
                f.write(problem.to_jsonl(include_hidden=True) + "\n")

    def create_standard_splits(self, problems: List[Problem], version: str = "v0.2",
                               public_ratio: float = 0.7, private_ratio: float = 0.2,
                               hidden_ratio: float = 0.1) -> Dict[str, DatasetSplit]:
        """Create standard public/private/hidden splits."""
        task_ids = [p.task_id for p in problems]
        random.shuffle(task_ids)

        n = len(task_ids)
        n_public = int(n * public_ratio)
        n_private = int(n * private_ratio)

        splits = {}
        splits["public"] = self.create_split(
            "public", task_ids[:n_public],
            "Public benchmark tasks with visible tests only",
            is_public=True, version=version
        )
        splits["private"] = self.create_split(
            "private", task_ids[n_public:n_public + n_private],
            "Private evaluation tasks with hidden tests (encrypted)",
            is_public=False, version=version
        )
        splits["hidden"] = self.create_split(
            "hidden", task_ids[n_public + n_private:],
            "Held-out test set for final evaluation (never published)",
            is_public=False, version=version
        )
        return splits

    def verify_no_overlap(self) -> List[str]:
        """Check for task ID overlap between splits."""
        overlaps = []
        split_names = list(self.splits.keys())
        for i, name1 in enumerate(split_names):
            for name2 in split_names[i+1:]:
                set1 = set(self.splits[name1].task_ids)
                set2 = set(self.splits[name2].task_ids)
                overlap = set1 & set2
                if overlap:
                    overlaps.append(f"{name1} ∩ {name2}: {overlap}")
        return overlaps

    def compute_split_hashes(self, problems: List[Problem]) -> Dict[str, str]:
        """Compute hash for each split for integrity verification."""
        problem_map = {p.task_id: p for p in problems}
        hashes = {}
        for split in self.splits.values():
            hasher = hashlib.sha256()
            for task_id in sorted(split.task_ids):
                if task_id in problem_map:
                    p = problem_map[task_id]
                    content = f"{task_id}:{p.prompt}:{p.public_test}"
                    hasher.update(content.encode())
            hashes[split.name] = hasher.hexdigest()[:16]
        return hashes


def create_canary_strings(problems: List[Problem]) -> Dict[str, str]:
    """Generate unique canary strings for each problem to detect contamination."""
    canaries = {}
    for problem in problems:
        content = f"{problem.task_id}:{problem.prompt}:{problem.public_test}"
        canary = "ROCKMAN_CANARY_" + hashlib.sha256(content.encode()).hexdigest()[:16]
        canaries[problem.task_id] = canary
    return canaries


def check_contamination(model_output: str, canaries: Dict[str, str]) -> List[str]:
    """Check if model output contains any canary strings (indicating contamination)."""
    found = []
    for task_id, canary in canaries.items():
        if canary in model_output:
            found.append(task_id)
    return found


import random