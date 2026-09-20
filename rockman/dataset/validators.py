"""Quality validators for Rockman benchmark tasks"""

import re
import time
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from rockman.benchmark.schema import Problem, TaskType, Language
from rockman.benchmark.runners import get_runner
from rockman.benchmark.evaluator import get_handler


@dataclass
class ValidationResult:
    passed: bool
    checks: Dict[str, bool]
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]


class TaskValidator:
    """Validates a benchmark task meets quality standards."""

    def __init__(self, reference_solution: str = "", buggy_solutions: List[str] = None):
        self.reference_solution = reference_solution
        self.buggy_solutions = buggy_solutions or []
        self.checks = {}

    def validate(self, problem: Problem) -> ValidationResult:
        """Run all validation checks."""
        self.checks = {}
        errors = []
        warnings = []
        metrics = {}

        checks = [
            ("prompt_valid", self._check_prompt_valid, problem),
            ("has_signature", self._check_has_signature, problem),
            ("has_docstring", self._check_has_docstring, problem),
            ("tests_parsable", self._check_tests_parsable, problem),
            ("reference_passes", self._check_reference_passes, problem),
            ("tests_detect_bugs", self._check_tests_detect_bugs, problem),
            ("no_ambiguity", self._check_no_ambiguity, problem),
            ("difficulty_consistent", self._check_difficulty_consistent, problem),
            ("runtime_within_limits", self._check_runtime_limits, problem),
            ("memory_within_limits", self._check_memory_limits, problem),
            ("deterministic", self._check_deterministic, problem),
            ("tags_appropriate", self._check_tags_appropriate, problem),
            ("hidden_tests_exist", self._check_hidden_tests, problem),
        ]

        for name, check_func, *args in checks:
            try:
                result = check_func(*args)
                self.checks[name] = result
                if not result:
                    errors.append(f"Check failed: {name}")
            except Exception as e:
                self.checks[name] = False
                errors.append(f"Check error {name}: {e}")

        # Warnings for non-critical issues
        if problem.expected_complexity and "O(" not in problem.expected_complexity:
            warnings.append("expected_complexity should use Big-O notation (e.g., O(n log n))")
        if not problem.tags:
            warnings.append("No tags specified; consider adding relevant tags")
        if problem.difficulty > 5 and problem.task_type == TaskType.GENERATION.value:
            warnings.append("High difficulty for generation task; consider debugging/optimization type")

        metrics = {
            "prompt_length": len(problem.prompt),
            "test_length": len(problem.public_test),
            "num_tags": len(problem.tags),
            "estimated_difficulty": problem.difficulty,
        }

        passed = all(self.checks.values()) if self.checks else False
        return ValidationResult(
            passed=passed,
            checks=self.checks,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
        )

    def _check_prompt_valid(self, problem: Problem) -> bool:
        return len(problem.prompt.strip()) > 50 and "def " in problem.prompt

    def _check_has_signature(self, problem: Problem) -> bool:
        # Check for function signature pattern: def name(...):
        # Handles both `def foo():` and `def foo(...) -> int:` formats
        import re
        return bool(re.search(r'def\s+\w+\s*\([^)]*\)\s*(->\s*\w+\s*)?:', problem.prompt))

    def _check_has_docstring(self, problem: Problem) -> bool:
        return '"""' in problem.prompt or "'''" in problem.prompt

    def _check_tests_parsable(self, problem: Problem) -> bool:
        try:
            handler = get_handler(problem.task_type)
            tests = handler.extract_test_cases(problem)
            return len(tests) > 0
        except:
            return False

    def _check_reference_passes(self, problem: Problem) -> bool:
        if not self.reference_solution:
            return True  # Skip if no reference provided
        handler = get_handler(problem.task_type)
        result = handler.evaluate(problem, self.reference_solution, include_hidden=False)
        return result.passed

    def _check_tests_detect_bugs(self, problem: Problem) -> bool:
        if not self.buggy_solutions:
            return True  # Skip if no buggy solutions provided
        handler = get_handler(problem.task_type)
        for buggy in self.buggy_solutions:
            result = handler.evaluate(problem, buggy, include_hidden=False)
            if result.passed:
                return False  # Buggy solution passed - tests don't detect bug
        return True

    def _check_no_ambiguity(self, problem: Problem) -> bool:
        ambiguous_phrases = [
            "implement a function that does something",
            "write code to solve this",
            "figure out the answer",
            "as appropriate",
            "handle all cases",
        ]
        prompt_lower = problem.prompt.lower()
        return not any(phrase in prompt_lower for phrase in ambiguous_phrases)

    def _check_difficulty_consistent(self, problem: Problem) -> bool:
        from rockman.dataset.categories import get_difficulty_range, validate_category
        if not validate_category(problem.category, problem.subcategory):
            return False
        low, high = get_difficulty_range(problem.category)
        return low <= problem.difficulty <= high

    def _check_runtime_limits(self, problem: Problem) -> bool:
        if not self.reference_solution:
            return True
        handler = get_handler(problem.task_type)
        result = handler.evaluate(problem, self.reference_solution, include_hidden=False)
        if not result.results:
            return True
        max_time = max(r.execution_time_ms for r in result.results)
        return max_time < problem.time_limit * 1000 * 0.5  # 50% of limit

    def _check_memory_limits(self, problem: Problem) -> bool:
        if not self.reference_solution:
            return True
        handler = get_handler(problem.task_type)
        result = handler.evaluate(problem, self.reference_solution, include_hidden=False)
        if not result.results:
            return True
        max_mem = max(r.memory_used_mb for r in result.results)
        return max_mem < problem.memory_limit * 0.5  # 50% of limit

    def _check_deterministic(self, problem: Problem) -> bool:
        if not problem.deterministic:
            return True
        if not self.reference_solution:
            return True
        handler = get_handler(problem.task_type)
        results = []
        for _ in range(3):
            result = handler.evaluate(problem, self.reference_solution, include_hidden=False)
            results.append(result.passed)
        return all(results) or not any(results)  # All same outcome

    def _check_tags_appropriate(self, problem: Problem) -> bool:
        if not problem.tags:
            return True
        relevant_tags = set(problem.tags)
        category_tags = set()
        from rockman.dataset.categories import get_category_tags, get_edge_case_tags
        category_tags.update(get_category_tags(problem.category))
        category_tags.update(get_edge_case_tags())
        # At least one tag should be relevant
        return len(relevant_tags & category_tags) > 0 or len(problem.tags) <= 3

    def _check_hidden_tests(self, problem: Problem) -> bool:
        return bool(problem.hidden_test_encrypted) or problem.task_type in [
            TaskType.DEBUGGING.value,
            TaskType.COMPLETION.value,
        ]


def validate_task(problem: Problem, reference_solution: str = "",
                  buggy_solutions: List[str] = None) -> ValidationResult:
    """Convenience function to validate a single task."""
    validator = TaskValidator(reference_solution, buggy_solutions)
    return validator.validate(problem)


def validate_dataset(problems: List[Problem], solutions: Dict[str, str] = None,
                     buggy_solutions: Dict[str, List[str]] = None) -> Dict[str, ValidationResult]:
    """Validate entire dataset."""
    results = {}
    for problem in problems:
        ref = solutions.get(problem.task_id, "") if solutions else ""
        buggy = buggy_solutions.get(problem.task_id, []) if buggy_solutions else []
        results[problem.task_id] = validate_task(problem, ref, buggy)
    return results


def generate_validation_report(results: Dict[str, ValidationResult]) -> str:
    """Generate human-readable validation report."""
    total = len(results)
    passed = sum(1 for r in results.values() if r.passed)
    failed = total - passed

    lines = [
        f"Validation Report: {passed}/{total} passed",
        "=" * 50,
    ]

    for task_id, result in results.items():
        status = "✓" if result.passed else "✗"
        lines.append(f"{status} {task_id}")
        if not result.passed:
            for error in result.errors:
                lines.append(f"    ERROR: {error}")
        for warning in result.warnings:
            lines.append(f"    WARN: {warning}")

    lines.append("")
    lines.append("Check Summary:")
    if results:
        all_checks = set()
        for r in results.values():
            all_checks.update(r.checks.keys())
        for check in sorted(all_checks):
            check_passed = sum(1 for r in results.values() if r.checks.get(check, False))
            lines.append(f"  {check}: {check_passed}/{total}")

    return "\n".join(lines)