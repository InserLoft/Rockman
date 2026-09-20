"""Reference model implementations for baselines"""

import random
import subprocess
import tempfile
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from rockman.benchmark.schema import Problem, TaskType
from rockman.benchmark.runners import get_runner


class BaselineModel(ABC):
    """Abstract baseline model."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    def solve(self, problem: Problem) -> List[str]:
        """Generate completions for a problem. Returns list of samples."""
        pass


class RandomBaseline(BaselineModel):
    """Random code generation baseline."""

    @property
    def name(self) -> str:
        return "random"

    @property
    def version(self) -> str:
        return "1.0"

    def solve(self, problem: Problem) -> List[str]:
        """Generate random syntactically valid but semantically random code."""
        # Extract function signature from prompt
        import re
        sig_match = re.search(r'(def\s+\w+\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:)', problem.prompt)
        if not sig_match:
            return ["pass"]

        signature = sig_match.group(1)
        return_type = "int"
        if "->" in signature:
            return_type = signature.split("->")[1].split(":")[0].strip()

        # Generate random implementations
        templates = {
            "int": [
                "return 0",
                "return 42",
                "return -1",
                "return len([])",
                "return sum([])",
            ],
            "bool": [
                "return True",
                "return False",
                "return True if False else False",
            ],
            "str": [
                'return ""',
                'return "hello"',
                'return str(0)',
            ],
            "list": [
                "return []",
                "return [1, 2, 3]",
                "return list(range(10))",
            ],
            "dict": [
                "return {}",
                "return {'a': 1}",
            ],
        }

        implementations = templates.get(return_type, ["pass"])
        return [f"{signature}\n    {impl}" for impl in implementations[:5]]


class HeuristicBaseline(BaselineModel):
    """Simple heuristic-based baseline (e.g., return first input, max, min, etc.)."""

    @property
    def name(self) -> str:
        return "heuristic"

    @property
    def version(self) -> str:
        return "1.0"

    def solve(self, problem: Problem) -> List[str]:
        import re
        sig_match = re.search(r'(def\s+\w+\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:)', problem.prompt)
        if not sig_match:
            return ["pass"]

        signature = sig_match.group(1)
        params = re.search(r'\(([^)]*)\)', signature)
        param_names = [p.split(":")[0].strip() for p in params.group(1).split(",")] if params else []

        # Heuristics based on problem category/tags
        category = problem.category.lower()
        tags = [t.lower() for t in problem.tags]

        if "sort" in category or "sort" in tags:
            impl = "return sorted(args[0]) if args else []"
        elif "max" in category or "maximum" in category:
            impl = "return max(args[0]) if args and args[0] else 0"
        elif "min" in category or "minimum" in category:
            impl = "return min(args[0]) if args and args[0] else 0"
        elif "sum" in category or "add" in category:
            impl = "return sum(args) if args else 0"
        elif "search" in category or "find" in category:
            impl = "return args[0].index(args[1]) if len(args) > 1 and args[1] in args[0] else -1"
        elif len(param_names) >= 2:
            impl = f"return {param_names[0]}"
        elif len(param_names) == 1:
            impl = f"return {param_names[0]}"
        else:
            impl = "return 0"

        return [f"{signature}\n    {impl}"]


class TemplateBaseline(BaselineModel):
    """Template-based baseline for common patterns."""

    @property
    def name(self) -> str:
        return "template"

    @property
    def version(self) -> str:
        return "1.0"

    TEMPLATES = {
        ("binary search", "search"): """
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
""",
        ("two pointers", "two-pointer"): """
    left, right = 0, len(arr) - 1
    while left < right:
        current = arr[left] + arr[right]
        if current == target:
            return [left, right]
        elif current < target:
            left += 1
        else:
            right -= 1
    return []
""",
        ("sliding window", "sliding-window"): """
    max_sum = float('-inf')
    current_sum = 0
    for i, val in enumerate(arr):
        current_sum += val
        if i >= k:
            current_sum -= arr[i - k]
        if i >= k - 1:
            max_sum = max(max_sum, current_sum)
    return max_sum
""",
        ("dp", "dynamic-programming"): """
    n = len(arr)
    dp = [0] * (n + 1)
    for i in range(n):
        dp[i + 1] = max(dp[i], dp[i] + arr[i])  # Placeholder
    return dp[n]
""",
        ("bfs", "graph"): """
    from collections import deque
    visited = set([start])
    queue = deque([(start, 0)])
    while queue:
        node, dist = queue.popleft()
        if node == target:
            return dist
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return -1
""",
    }

    def solve(self, problem: Problem) -> List[str]:
        import re
        sig_match = re.search(r'(def\s+\w+\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:)', problem.prompt)
        if not sig_match:
            return ["pass"]

        signature = sig_match.group(1)
        prompt_lower = problem.prompt.lower()
        category = problem.category.lower()
        tags = [t.lower() for t in problem.tags]

        # Match template
        for keywords, template in self.TEMPLATES.items():
            if any(kw in prompt_lower or kw in category or kw in tags for kw in keywords):
                return [f"{signature}\n{template}"]

        # Default based on category
        defaults = {
            "graph": "return []",
            "tree": "return None",
            "dynamic programming": "return 0",
            "greedy": "return 0",
            "math": "return 0",
        }
        impl = defaults.get(category, "pass")
        return [f"{signature}\n    {impl}"]


class LLMBaseline(BaselineModel):
    """Baseline using an LLM API (placeholder for actual integration)."""

    def __init__(self, model_name: str, api_key: str = None, temperature: float = 0.2):
        self._model_name = model_name
        self.api_key = api_key
        self.temperature = temperature

    @property
    def name(self) -> str:
        return f"llm-{self._model_name}"

    @property
    def version(self) -> str:
        return "1.0"

    def solve(self, problem: Problem) -> List[str]:
        # Placeholder - would integrate with actual LLM API
        # For now, return heuristic baseline
        heuristic = HeuristicBaseline()
        return heuristic.solve(problem)


def run_baseline_suite(
    problems: List[Problem],
    baselines: List[BaselineModel] = None,
    samples_per_problem: int = 5
) -> Dict[str, Dict[str, List[str]]]:
    """Run multiple baselines on a problem set."""
    if baselines is None:
        baselines = [RandomBaseline(), HeuristicBaseline(), TemplateBaseline()]

    all_completions = {}
    for baseline in baselines:
        print(f"Running baseline: {baseline.name} v{baseline.version}")
        completions = {}
        for problem in problems:
            try:
                samples = baseline.solve(problem)
                # Pad or truncate to samples_per_problem
                while len(samples) < samples_per_problem:
                    samples.append(samples[0] if samples else "pass")
                completions[problem.task_id] = samples[:samples_per_problem]
            except Exception as e:
                print(f"  Error on {problem.task_id}: {e}")
                completions[problem.task_id] = ["pass"] * samples_per_problem
        all_completions[baseline.name] = completions

    return all_completions


def evaluate_baselines(
    problems: List[Problem],
    baseline_completions: Dict[str, Dict[str, List[str]]],
    k: int = 1,
    include_hidden: bool = False
) -> Dict[str, Any]:
    """Evaluate all baseline completions."""
    from rockman.benchmark.evaluator import Evaluator
    from rockman.benchmark.metrics import aggregate_scores

    evaluator = Evaluator()
    results = {}

    for baseline_name, completions in baseline_completions.items():
        print(f"\nEvaluating {baseline_name}...")
        eval_result = evaluator.evaluate_dataset(problems, completions, include_hidden, k)
        results[baseline_name] = eval_result

    return results


def print_baseline_comparison(results: Dict[str, Any], problems: List[Problem]):
    """Print comparison of baseline results."""
    from rockman.benchmark.metrics import aggregate_scores

    print(f"\n{'='*80}")
    print("Baseline Comparison")
    print(f"{'='*80}")
    print(f"{'Baseline':<20} {'Pass@1':<10} {'Evaluated':<12}")
    print("-" * 50)

    for baseline_name, result in results.items():
        pass_at_k = result.get("mean_pass_at_k", 0)
        evaluated = result.get("evaluated_count", 0)
        print(f"{baseline_name:<20} {pass_at_k:.4f}    {evaluated:<12}")

    print(f"{'='*80}")