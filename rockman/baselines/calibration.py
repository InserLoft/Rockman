"""Difficulty calibration and reference model evaluation"""

import json
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime

from rockman.benchmark.schema import Problem, RockmanScore
from rockman.benchmark.metrics import aggregate_scores
from rockman.benchmark.evaluator import Evaluator


@dataclass
class ReferenceModel:
    """A reference model for calibration."""
    name: str
    version: str
    description: str = ""
    # Results: {task_id: {passed: bool, samples: int, correct: int}}
    results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    evaluated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationResult:
    """Results of difficulty calibration."""
    model_name: str
    model_version: str
    benchmark_version: str
    date: str
    difficulty_scores: Dict[int, float]  # difficulty -> pass rate
    category_scores: Dict[str, float]
    task_type_scores: Dict[str, float]
    overall_pass_rate: float
    total_problems: int
    total_samples: int
    # Statistical validation
    difficulty_separation: Dict[str, float]  # e.g., "1_vs_2": 0.3 (difference in pass rates)
    confidence_intervals: Dict[str, tuple] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


class DifficultyCalibrator:
    """Calibrates problem difficulty using reference models."""

    def __init__(self, evaluator: Evaluator = None):
        self.evaluator = evaluator or Evaluator()
        self.reference_models: Dict[str, ReferenceModel] = {}

    def add_reference_model(self, model: ReferenceModel):
        """Add a reference model for calibration."""
        key = f"{model.name}-{model.version}"
        self.reference_models[key] = model

    def evaluate_reference_model(
        self, 
        model_name: str, 
        model_version: str, 
        problems: List[Problem],
        completions: Dict[str, List[str]],
        description: str = "",
        metadata: Dict = None,
        include_hidden: bool = False
    ) -> ReferenceModel:
        """Evaluate a reference model and store results."""
        results = self.evaluator.evaluate_dataset(problems, completions, include_hidden)

        model = ReferenceModel(
            name=model_name,
            version=model_version,
            description=description,
            results=results.get("results", {}),
            metadata=metadata or {},
        )
        self.add_reference_model(model)
        return model

    def calibrate_difficulty(
        self, 
        problems: List[Problem], 
        model_key: str = None,
        min_samples_per_difficulty: int = 10
    ) -> CalibrationResult:
        """Calibrate difficulty levels using reference model results."""
        if model_key:
            if model_key not in self.reference_models:
                raise ValueError(f"Reference model {model_key} not found")
            model = self.reference_models[model_key]
        else:
            # Use the most recent model
            if not self.reference_models:
                raise ValueError("No reference models available")
            model = max(self.reference_models.values(), key=lambda m: m.evaluated_at)

        # Group problems by difficulty
        problems_by_difficulty = defaultdict(list)
        for p in problems:
            problems_by_difficulty[p.difficulty].append(p)

        difficulty_scores = {}
        difficulty_sample_counts = {}

        for difficulty in sorted(problems_by_difficulty.keys()):
            probs = problems_by_difficulty[difficulty]
            task_ids = [p.task_id for p in probs]

            total_samples = 0
            total_correct = 0
            evaluated = 0

            for task_id in task_ids:
                if task_id in model.results:
                    for result in model.results[task_id]:
                        total_samples += 1
                        if result.get("passed", False):
                            total_correct += 1
                    evaluated += 1

            if evaluated >= min_samples_per_difficulty:
                pass_rate = total_correct / total_samples if total_samples > 0 else 0
                difficulty_scores[difficulty] = pass_rate
                difficulty_sample_counts[difficulty] = total_samples

        # Calculate category scores
        category_scores = {}
        categories = set(p.category for p in problems)
        for cat in categories:
            cat_probs = [p for p in problems if p.category == cat]
            cat_task_ids = [p.task_id for p in cat_probs]
            total_s = 0
            correct_s = 0
            for tid in cat_task_ids:
                if tid in model.results:
                    for result in model.results[tid]:
                        total_s += 1
                        if result.get("passed", False):
                            correct_s += 1
            category_scores[cat] = correct_s / total_s if total_s > 0 else 0

        # Calculate task type scores
        task_type_scores = {}
        task_types = set(p.task_type for p in problems)
        for tt in task_types:
            tt_probs = [p for p in problems if p.task_type == tt]
            tt_task_ids = [p.task_id for p in tt_probs]
            total_s = 0
            correct_s = 0
            for tid in tt_task_ids:
                if tid in model.results:
                    for result in model.results[tid]:
                        total_s += 1
                        if result.get("passed", False):
                            correct_s += 1
            task_type_scores[tt] = correct_s / total_s if total_s > 0 else 0

        # Overall
        all_task_ids = [p.task_id for p in problems]
        total_all = 0
        correct_all = 0
        for tid in all_task_ids:
            if tid in model.results:
                for result in model.results[tid]:
                    total_all += 1
                    if result.get("passed", False):
                        correct_all += 1

        overall_pass_rate = correct_all / total_all if total_all > 0 else 0

        # Calculate difficulty separation (should be monotonic decreasing)
        difficulty_separation = {}
        sorted_diffs = sorted(difficulty_scores.keys())
        for i in range(len(sorted_diffs) - 1):
            d1, d2 = sorted_diffs[i], sorted_diffs[i + 1]
            diff = difficulty_scores[d1] - difficulty_scores[d2]
            difficulty_separation[f"{d1}_vs_{d2}"] = diff

        # Confidence intervals using Wilson score
        from rockman.benchmark.metrics import calculate_confidence_interval
        confidence_intervals = {}
        for d, rate in difficulty_scores.items():
            n = difficulty_sample_counts.get(d, 0)
            if n > 0:
                c = int(rate * n)
                ci = calculate_confidence_interval(c, n)
                confidence_intervals[f"difficulty_{d}"] = ci

        # Validation notes
        notes = []
        # Check monotonicity
        if difficulty_scores:
            values = [difficulty_scores[d] for d in sorted_diffs]
            if not all(values[i] >= values[i+1] for i in range(len(values)-1)):
                notes.append("WARNING: Difficulty scores not monotonic - calibration may be unreliable")
            if values[0] - values[-1] < 0.3:
                notes.append("WARNING: Low dynamic range between easiest and hardest difficulty")

        return CalibrationResult(
            model_name=model.name,
            model_version=model.version,
            benchmark_version="v0.2",  # Would come from problems
            date=datetime.utcnow().isoformat() + "Z",
            difficulty_scores=difficulty_scores,
            category_scores=category_scores,
            task_type_scores=task_type_scores,
            overall_pass_rate=overall_pass_rate,
            total_problems=len(problems),
            total_samples=total_all,
            difficulty_separation=difficulty_separation,
            confidence_intervals=confidence_intervals,
            notes=notes,
        )

    def save_calibration(self, result: CalibrationResult, filepath: str):
        """Save calibration result to JSON."""
        data = {
            "model_name": result.model_name,
            "model_version": result.model_version,
            "benchmark_version": result.benchmark_version,
            "date": result.date,
            "difficulty_scores": result.difficulty_scores,
            "category_scores": result.category_scores,
            "task_type_scores": result.task_type_scores,
            "overall_pass_rate": result.overall_pass_rate,
            "total_problems": result.total_problems,
            "total_samples": result.total_samples,
            "difficulty_separation": result.difficulty_separation,
            "confidence_intervals": result.confidence_intervals,
            "notes": result.notes,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_calibration(self, filepath: str) -> CalibrationResult:
        """Load calibration result from JSON."""
        with open(filepath) as f:
            data = json.load(f)
        return CalibrationResult(**data)

    def print_calibration_report(self, result: CalibrationResult):
        """Print human-readable calibration report."""
        print(f"\n{'='*70}")
        print(f"Difficulty Calibration Report")
        print(f"{'='*70}")
        print(f"Model: {result.model_name} {result.model_version}")
        print(f"Benchmark: {result.benchmark_version}")
        print(f"Date: {result.date}")
        print(f"Problems: {result.total_problems}, Samples: {result.total_samples}")
        print(f"Overall Pass Rate: {result.overall_pass_rate:.1%}")
        print(f"\nDifficulty Scores (Pass Rate):")
        for d in sorted(result.difficulty_scores.keys()):
            rate = result.difficulty_scores[d]
            ci = result.confidence_intervals.get(f"difficulty_{d}", (0, 0))
            print(f"  Level {d}: {rate:.1%} (n={result.difficulty_scores[d]*100:.0f}%, CI: [{ci[0]:.1f}%, {ci[1]:.1f}%])")
        print(f"\nDifficulty Separation (should be positive):")
        for k, v in result.difficulty_separation.items():
            status = "✓" if v > 0 else "✗"
            print(f"  {k}: {v:.3f} {status}")
        print(f"\nCategory Scores:")
        for cat, rate in sorted(result.category_scores.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {rate:.1%}")
        print(f"\nTask Type Scores:")
        for tt, rate in sorted(result.task_type_scores.items(), key=lambda x: -x[1]):
            print(f"  {tt}: {rate:.1%}")
        if result.notes:
            print(f"\nNotes:")
            for note in result.notes:
                print(f"  - {note}")
        print(f"{'='*70}")


def run_calibration_suite(
    problems: List[Problem],
    reference_models: List[Dict[str, Any]],
    output_dir: str = "calibration_results"
) -> List[CalibrationResult]:
    """Run full calibration suite with multiple reference models."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    calibrator = DifficultyCalibrator()
    results = []

    for model_info in reference_models:
        print(f"\nEvaluating reference model: {model_info['name']} v{model_info['version']}")
        # This would be called with actual model completions
        # model = calibrator.evaluate_reference_model(...)
        # result = calibrator.calibrate_difficulty(problems, f"{model_info['name']}-{model_info['version']}")
        # calibrator.save_calibration(result, f"{output_dir}/{model_info['name']}_{model_info['version']}.json")
        # results.append(result)
        pass

    return results