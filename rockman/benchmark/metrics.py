"""Metrics calculation for Rockman benchmark"""

import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from rockman.benchmark.schema import Problem, RockmanScore, ExecutionResult
from rockman.benchmark.evaluator import EvaluationResult


def estimate_pass_at_k(n: int, c: int, k: int) -> float:
    """
    Calculate Pass@k metric.
    n: total samples generated
    c: number of correct samples
    k: the k in Pass@k
    """
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def calculate_pass_at_k_per_problem(
    results_by_problem: Dict[str, List[EvaluationResult]], 
    k: int = 1
) -> Dict[str, float]:
    """
    Calculate Pass@k for each problem from multiple samples.
    results_by_problem: {task_id: [EvaluationResult, ...]} - multiple samples per problem
    """
    pass_at_k = {}
    for task_id, results in results_by_problem.items():
        n = len(results)
        c = sum(1 for r in results if r.passed)
        pass_at_k[task_id] = estimate_pass_at_k(n, c, k)
    return pass_at_k


def calculate_pass_at_k_from_results(results: List[EvaluationResult], k: int = 1) -> float:
    """Calculate Pass@k assuming 1 sample per problem (for backward compat)."""
    n = len(results)
    c = sum(1 for r in results if r.passed)
    return estimate_pass_at_k(n, c, k)


def aggregate_scores(
    results_by_problem: Dict[str, List[EvaluationResult]], 
    problems: List[Problem],
    k: int = 1
) -> RockmanScore:
    """
    Aggregate evaluation results into a RockmanScore using Pass@k.
    results_by_problem: {task_id: [EvaluationResult, ...]} - multiple samples per problem
    """
    problem_map = {p.task_id: p for p in problems}

    total_problems = len(results_by_problem)
    if total_problems == 0:
        return RockmanScore(overall=0.0, total_tasks=0, passed_tasks=0)

    # Calculate Pass@k per problem
    pass_at_k_per_problem = {}
    for task_id, results in results_by_problem.items():
        n = len(results)
        c = sum(1 for r in results if r.passed)
        pass_at_k_per_problem[task_id] = estimate_pass_at_k(n, c, k)

    # Overall score = mean Pass@k across problems
    overall = sum(pass_at_k_per_problem.values()) / total_problems * 100

    # Aggregate by dimensions
    by_difficulty: Dict[int, List[float]] = defaultdict(list)
    by_category: Dict[str, List[float]] = defaultdict(list)
    by_subcategory: Dict[str, List[float]] = defaultdict(list)
    by_task_type: Dict[str, List[float]] = defaultdict(list)
    by_language: Dict[str, List[float]] = defaultdict(list)

    efficiency_scores = []
    robustness_scores = []

    for task_id, pass_at_k in pass_at_k_per_problem.items():
        problem = problem_map.get(task_id)
        if not problem:
            continue

        by_difficulty[problem.difficulty].append(pass_at_k)
        by_category[problem.category].append(pass_at_k)
        by_subcategory[problem.subcategory].append(pass_at_k)
        by_task_type[problem.task_type].append(pass_at_k)
        by_language[problem.language].append(pass_at_k)

        if "efficiency" in problem.tags or "complexity" in problem.tags:
            efficiency_scores.append(pass_at_k)
        if "edge-case" in problem.tags or "robustness" in problem.tags:
            robustness_scores.append(pass_at_k)

    def avg(lst: List[float]) -> float:
        return sum(lst) / len(lst) * 100 if lst else 0.0

    return RockmanScore(
        overall=overall,
        by_difficulty={d: avg(v) for d, v in by_difficulty.items()},
        by_category={c: avg(v) for c, v in by_category.items()},
        by_subcategory={s: avg(v) for s, v in by_subcategory.items()},
        by_task_type={t: avg(v) for t, v in by_task_type.items()},
        by_language={l: avg(v) for l, v in by_language.items()},
        efficiency_score=avg(efficiency_scores),
        robustness_score=avg(robustness_scores),
        total_tasks=total_problems,
        passed_tasks=int(sum(1 for v in pass_at_k_per_problem.values() if v == 1.0)),
    )


def aggregate_scores_legacy(results: List[EvaluationResult], problems: List[Problem]) -> RockmanScore:
    """Legacy aggregate_scores for backward compatibility (1 sample per problem)."""
    # Convert to new format
    results_by_problem = {}
    for r in results:
        task_id = r.problem.task_id
        if task_id not in results_by_problem:
            results_by_problem[task_id] = []
        results_by_problem[task_id].append(r)
    return aggregate_scores(results_by_problem, problems)


def format_leaderboard_row(model_name: str, model_version: str, score: RockmanScore,
                           temperature: float = 0.2, max_tokens: int = 4096,
                           attempts: int = 1, hardware: str = "unknown", date: str = "") -> str:
    """Format a leaderboard table row."""
    cats = score.by_category
    return (
        f"| {model_name:<15} | {model_version:<10} | {temperature:<5} | {max_tokens:<6} | "
        f"{attempts:<8} | {hardware:<10} | {date:<10} | {score.overall:.1f}% | "
        f"{cats.get('Dynamic Programming', 0):.0f}% | {cats.get('Graphs', 0):.0f}% | "
        f"{cats.get('Debugging', 0):.0f}% | "
        f"{sum(v for k, v in score.by_difficulty.items() if k >= 4) / max(1, sum(1 for k in score.by_difficulty if k >= 4)):.1f}% |"
    )


def print_leaderboard_header():
    print("| Model           | Version    | Temp | Tokens | Attempts | Hardware   | Date       | Overall | DP  | Graphs | Debug | Adv |")
    print("|-----------------|------------|------|--------|----------|------------|------------|---------|-----|--------|-------|-----|")


def calculate_confidence_interval(passed: int, total: int, confidence: float = 0.95) -> tuple:
    """Calculate Wilson score interval for binomial proportion."""
    if total == 0:
        return (0.0, 0.0)

    z = 1.96 if confidence == 0.95 else 2.576
    p = passed / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return (max(0, centre - half) * 100, min(1, centre + half) * 100)


def statistical_significance(score1: RockmanScore, score2: RockmanScore) -> Dict[str, Any]:
    """Compare two scores for statistical significance (two-proportion z-test)."""
    try:
        from scipy import stats
    except ImportError:
        # Fallback without scipy
        return {"significant": False, "p_value": 1.0, "note": "scipy not installed"}

    n1, c1 = score1.total_tasks, score1.passed_tasks
    n2, c2 = score2.total_tasks, score2.passed_tasks

    if n1 == 0 or n2 == 0:
        return {"significant": False, "p_value": 1.0}

    p1, p2 = c1 / n1, c2 / n2
    p_pool = (c1 + c2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    z = (p1 - p2) / se if se > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    return {
        "significant": p_value < 0.05,
        "p_value": p_value,
        "z_score": z,
        "diff": (p1 - p2) * 100,
    }


def compare_scores_by_category(
    score1: RockmanScore, 
    score2: RockmanScore, 
    categories: List[str] = None
) -> Dict[str, Dict[str, Any]]:
    """Compare two scores category by category."""
    if categories is None:
        categories = set(score1.by_category.keys()) | set(score2.by_category.keys())

    results = {}
    for cat in categories:
        if cat in score1.by_category and cat in score2.by_category:
            # We don't have n per category, so we can't do proper significance test
            # Return the difference
            results[cat] = {
                "score1": score1.by_category[cat],
                "score2": score2.by_category[cat],
                "diff": score1.by_category[cat] - score2.by_category[cat],
            }
    return results


@dataclass
class BenchmarkReport:
    """Full benchmark report with all metrics."""
    benchmark_version: str
    model_name: str
    model_version: str
    temperature: float
    max_tokens: int
    num_attempts: int
    hardware: str
    date: str
    score: RockmanScore
    per_problem: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    confidence_interval: tuple = (0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "num_attempts": self.num_attempts,
            "hardware": self.hardware,
            "date": self.date,
            "score": self.score.to_dict(),
            "per_problem": self.per_problem,
            "confidence_interval": self.confidence_interval,
        }

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"Rockman Benchmark Report")
        print(f"{'='*60}")
        print(f"Benchmark: {self.benchmark_version}")
        print(f"Model: {self.model_name} ({self.model_version})")
        print(f"Settings: temp={self.temperature}, tokens={self.max_tokens}, attempts={self.num_attempts}")
        print(f"Hardware: {self.hardware}")
        print(f"Date: {self.date}")
        print(f"{'='*60}")
        print(self.score.format_leaderboard())
        print(f"\n95% CI: [{self.confidence_interval[0]:.1f}%, {self.confidence_interval[1]:.1f}%]")