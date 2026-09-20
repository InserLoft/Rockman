"""Unified evaluator for all task types"""

import re
import math
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from rockman.benchmark.schema import Problem, ExecutionResult, TaskType, Language
from rockman.benchmark.runners import get_runner
from rockman.benchmark.encryption import HiddenTestEncryption


@dataclass
class EvaluationResult:
    problem: Problem
    completion: str
    results: List[ExecutionResult]
    passed: bool
    pass_at_k: float
    score_details: Dict[str, Any]


class TaskTypeHandler:
    """Base handler for different task types."""

    def prepare_code(self, problem: Problem, completion: str) -> str:
        """Prepare full code for execution. Override in subclasses."""
        return completion

    def extract_test_cases(self, problem: Problem, include_hidden: bool = False) -> List[Tuple[str, str]]:
        """Extract (input, expected_output) pairs from test code."""
        test_code = problem.public_test
        if include_hidden and problem.hidden_test_encrypted:
            try:
                encryption = HiddenTestEncryption(benchmark_version=problem.version)
                hidden = encryption.decrypt_problem_hidden_tests(problem)
                test_code += "\n" + hidden
            except Exception:
                pass
        return self._parse_tests(test_code)

    def _parse_tests(self, test_code: str) -> List[Tuple[str, str]]:
        """Parse test code into input/expected pairs. Override for specific formats."""
        return []

    def evaluate(self, problem: Problem, completion: str, include_hidden: bool = False) -> EvaluationResult:
        """Run evaluation for this task type."""
        raise NotImplementedError


class GenerationHandler(TaskTypeHandler):
    """Handler for code generation tasks."""

    def prepare_code(self, problem: Problem, completion: str) -> str:
        return completion

    def _parse_tests(self, test_code: str) -> List[Tuple[str, str]]:
        tests = []
        for line in test_code.strip().split("\n"):
            line = line.strip()
            if line.startswith("assert "):
                try:
                    expr = line[7:]
                    if "==" in expr:
                        left, right = expr.split("==", 1)
                        tests.append((left.strip(), right.strip()))
                except:
                    pass
        return tests

    def evaluate(self, problem: Problem, completion: str, include_hidden: bool = False) -> EvaluationResult:
        runner = get_runner(problem.language, problem.time_limit, problem.memory_limit)
        full_code = self.prepare_code(problem, completion)

        test_cases = self.extract_test_cases(problem, include_hidden)
        if not test_cases:
            full_code += "\n" + problem.public_test
            if include_hidden and problem.hidden_test_encrypted:
                try:
                    encryption = HiddenTestEncryption(benchmark_version=problem.version)
                    hidden = encryption.decrypt_problem_hidden_tests(problem)
                    full_code += "\n" + hidden
                except:
                    pass
            result = runner.execute(full_code)
            passed = result.success
            results = [result]
            pass_at_k = 1.0 if passed else 0.0
        else:
            results = []
            passed_count = 0
            for input_data, expected in test_cases:
                test_code = f"{full_code}\n# Test\nresult = {input_data}\nexpected = {expected}\nassert result == expected, f'Expected {{expected}}, got {{result}}'"
                result = runner.execute(test_code)
                results.append(result)
                if result.success:
                    passed_count += 1
            passed = passed_count == len(test_cases)
            pass_at_k = passed_count / len(test_cases) if test_cases else 0.0

        return EvaluationResult(
            problem=problem,
            completion=completion,
            results=results,
            passed=passed,
            pass_at_k=pass_at_k,
            score_details={
                "total_tests": len(results),
                "passed_tests": sum(1 for r in results if r.success),
            },
        )


class DebuggingHandler(TaskTypeHandler):
    """Handler for debugging/bug-fixing tasks."""

    def prepare_code(self, problem: Problem, completion: str) -> str:
        return completion

    def _parse_tests(self, test_code: str) -> List[Tuple[str, str]]:
        return GenerationHandler()._parse_tests(test_code)

    def evaluate(self, problem: Problem, completion: str, include_hidden: bool = False) -> EvaluationResult:
        base_handler = GenerationHandler()
        return base_handler.evaluate(problem, completion, include_hidden)


class CompletionHandler(TaskTypeHandler):
    """Handler for code completion tasks."""

    def prepare_code(self, problem: Problem, completion: str) -> str:
        prompt = problem.prompt
        if "..." in prompt:
            return prompt.replace("...", completion)
        return prompt + "\n" + completion

    def _parse_tests(self, test_code: str) -> List[Tuple[str, str]]:
        return GenerationHandler()._parse_tests(test_code)

    def evaluate(self, problem: Problem, completion: str, include_hidden: bool = False) -> EvaluationResult:
        base_handler = GenerationHandler()
        return base_handler.evaluate(problem, completion, include_hidden)


class OptimizationHandler(TaskTypeHandler):
    """Handler for optimization tasks with complexity constraints."""

    def __init__(self):
        self.complexity_tests = []

    def prepare_code(self, problem: Problem, completion: str) -> str:
        return completion

    def _parse_tests(self, test_code: str) -> List[Tuple[str, str]]:
        return GenerationHandler()._parse_tests(test_code)

    def evaluate(self, problem: Problem, completion: str, include_hidden: bool = False) -> EvaluationResult:
        base_handler = GenerationHandler()
        result = base_handler.evaluate(problem, completion, include_hidden)

        if result.passed and problem.expected_complexity:
            complexity_passed = self._check_complexity(problem, completion, result.results)
            result.passed = result.passed and complexity_passed
            result.score_details["complexity_check"] = complexity_passed
            result.score_details["expected_complexity"] = problem.expected_complexity

        return result

    def _check_complexity(self, problem: Problem, completion: str, results: List[ExecutionResult]) -> bool:
        if not results:
            return True
        max_time = max(r.execution_time_ms for r in results)
        expected = problem.expected_complexity.lower()

        if "o(1)" in expected or "o(log n)" in expected:
            return max_time < 100
        elif "o(n)" in expected and "log" not in expected:
            return max_time < 500
        elif "o(n log n)" in expected:
            return max_time < 1000
        elif "o(n^2)" in expected or "o(n²)" in expected:
            return max_time < 5000
        return True


class StatefulHandler(TaskTypeHandler):
    """Handler for stateful tasks (classes with state)."""

    def prepare_code(self, problem: Problem, completion: str) -> str:
        return completion

    def evaluate(self, problem: Problem, completion: str, include_hidden: bool = False) -> EvaluationResult:
        runner = get_runner(problem.language, problem.time_limit, problem.memory_limit)

        test_code = problem.public_test
        if include_hidden and problem.hidden_test_encrypted:
            try:
                encryption = HiddenTestEncryption(benchmark_version=problem.version)
                hidden = encryption.decrypt_problem_hidden_tests(problem)
                test_code += "\n" + hidden
            except:
                pass

        full_code = f"{completion}\n{test_code}"
        result = runner.execute(full_code)

        return EvaluationResult(
            problem=problem,
            completion=completion,
            results=[result],
            passed=result.success,
            pass_at_k=1.0 if result.success else 0.0,
            score_details={"total_tests": 1, "passed_tests": 1 if result.success else 0},
        )


class MultiStepHandler(TaskTypeHandler):
    """Handler for multi-step reasoning tasks."""

    def prepare_code(self, problem: Problem, completion: str) -> str:
        return completion

    def evaluate(self, problem: Problem, completion: str, include_hidden: bool = False) -> EvaluationResult:
        return StatefulHandler().evaluate(problem, completion, include_hidden)


HANDLER_REGISTRY: Dict[str, TaskTypeHandler] = {
    TaskType.GENERATION.value: GenerationHandler(),
    TaskType.DEBUGGING.value: DebuggingHandler(),
    TaskType.COMPLETION.value: CompletionHandler(),
    TaskType.REFACTORING.value: GenerationHandler(),
    TaskType.OPTIMIZATION.value: OptimizationHandler(),
    TaskType.API_IMPLEMENTATION.value: GenerationHandler(),
    TaskType.PARSING.value: GenerationHandler(),
    TaskType.FILE_IO.value: GenerationHandler(),
    TaskType.STATEFUL.value: StatefulHandler(),
    TaskType.MULTI_STEP.value: MultiStepHandler(),
}


def get_handler(task_type: str) -> TaskTypeHandler:
    return HANDLER_REGISTRY.get(task_type, GenerationHandler())


class Evaluator:
    """Main evaluator for Rockman benchmark."""

    def __init__(self, benchmark_version: str = "v0.2", master_secret: Optional[str] = None):
        self.benchmark_version = benchmark_version
        self.encryption = HiddenTestEncryption(master_secret, benchmark_version) if master_secret else None

    def evaluate_single(self, problem: Problem, completion: str, include_hidden: bool = False,
                        k: int = 1) -> EvaluationResult:
        """Evaluate a single completion against a problem."""
        handler = get_handler(problem.task_type)
        return handler.evaluate(problem, completion, include_hidden)

    def evaluate_multiple(self, problem: Problem, completions: List[str],
                          include_hidden: bool = False, k: int = 1) -> Tuple[float, List[EvaluationResult]]:
        """Evaluate multiple completions (for Pass@k)."""
        results = []
        for completion in completions:
            result = self.evaluate_single(problem, completion, include_hidden, k)
            results.append(result)

        passed_count = sum(1 for r in results if r.passed)
        n = len(completions)
        c = passed_count

        if n - c < k:
            pass_at_k = 1.0
        else:
            pass_at_k = 1.0 - math.comb(n - c, k) / math.comb(n, k)

        return pass_at_k, results

    def evaluate_dataset(self, problems: List[Problem], completions: Dict[str, List[str]],
                         include_hidden: bool = False, k: int = 1) -> Dict[str, Any]:
        """Evaluate a full dataset."""
        total_pass_at_k = 0.0
        evaluated = 0
        all_results = {}

        for problem in problems:
            task_id = problem.task_id
            if task_id not in completions:
                continue

            task_completions = completions[task_id]
            pass_at_k, results = self.evaluate_multiple(problem, task_completions, include_hidden, k)
            total_pass_at_k += pass_at_k
            evaluated += 1
            all_results[task_id] = results

        mean_pass_at_k = total_pass_at_k / evaluated if evaluated > 0 else 0.0
        return {
            "mean_pass_at_k": mean_pass_at_k,
            "evaluated_count": evaluated,
            "results": all_results,
        }