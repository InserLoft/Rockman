"""Complexity challenge utilities - performance test generation"""

import time
import random
from typing import List, Dict, Any, Callable, Optional
from rockman.benchmark.schema import Problem, TaskType, ExecutionResult
from rockman.benchmark.runners import get_runner


COMPLEXITY_CLASSES = {
    "O(1)": {"max_n": 1000000, "time_factor": 0.001},
    "O(log n)": {"max_n": 1000000, "time_factor": 0.01},
    "O(n)": {"max_n": 100000, "time_factor": 0.1},
    "O(n log n)": {"max_n": 50000, "time_factor": 1.0},
    "O(n^2)": {"max_n": 2000, "time_factor": 10.0},
    "O(n^3)": {"max_n": 200, "time_factor": 100.0},
    "O(2^n)": {"max_n": 20, "time_factor": 1000.0},
}


def generate_performance_test(
    problem: Problem,
    reference_solution: str,
    complexity_class: str,
    num_tests: int = 3
) -> List[Dict[str, Any]]:
    """Generate performance test cases that verify complexity."""
    if complexity_class not in COMPLEXITY_CLASSES:
        complexity_class = "O(n log n)"

    config = COMPLEXITY_CLASSES[complexity_class]
    max_n = config["max_n"]

    tests = []
    runner = get_runner(problem.language, problem.time_limit, problem.memory_limit)

    for i in range(num_tests):
        # Generate input size that should complete within time limit for correct complexity
        n = min(max_n, random.randint(max_n // 10, max_n))

        input_data = generate_input_for_problem(problem, n)
        if not input_data:
            continue

        # Run reference solution to get expected output and baseline time
        test_code = f"{reference_solution}\nresult = solve({input_data})\nprint(result)"
        result = runner.execute(test_code)

        if result.success:
            tests.append({
                "input": input_data,
                "expected_output": result.stdout.strip(),
                "max_time_ms": result.execution_time_ms * 5,  # 5x reference time
                "input_size": n,
                "description": f"Performance test n={n} for {complexity_class}",
            })

    return tests


def generate_input_for_problem(problem: Problem, n: int) -> Optional[str]:
    """Generate input data of size n for a problem."""
    # This is problem-specific - would need customization per problem
    # Return a generic template
    category = problem.category.lower()

    if "array" in problem.prompt.lower() or "list" in problem.prompt.lower():
        arr = [random.randint(-1000, 1000) for _ in range(n)]
        return f"[{', '.join(map(str, arr))}]"
    elif "graph" in problem.prompt.lower() or "edge" in problem.prompt.lower():
        edges = []
        for _ in range(min(n, n * 2)):
            u = random.randint(0, n - 1)
            v = random.randint(0, n - 1)
            w = random.randint(1, 100)
            edges.append(f"({u}, {v}, {w})")
        return f"{n}, [{', '.join(edges)}]"
    elif "string" in problem.prompt.lower():
        return f"'{''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=n))}'"
    elif "tree" in problem.prompt.lower():
        return f"generate_tree({n})"

    return None


def create_complexity_challenge(
    base_problem: Problem,
    reference_solution: str,
    target_complexity: str,
    naive_solution: str = None
) -> Problem:
    """Create an optimization/complexity challenge from a base problem."""
    perf_tests = generate_performance_test(base_problem, reference_solution, target_complexity)

    # Build test code with performance assertions
    test_lines = [base_problem.public_test]
    for pt in perf_tests:
        test_lines.append(f"""
# Performance test: {pt['description']}
import time
start = time.time()
result = solve({pt['input']})
elapsed = (time.time() - start) * 1000
assert elapsed < {pt['max_time_ms']}, f"Too slow: {{elapsed}}ms > {{pt['max_time_ms']}}ms for n={pt['input_size']}"
assert result == {pt['expected_output']}
""")

    enhanced_test = "\n".join(test_lines)

    challenge = Problem(
        task_id=f"{base_problem.task_id}_complexity_{target_complexity.replace('(', '').replace(')', '').replace('^', '')}",
        category="Complexity",
        subcategory=target_complexity,
        difficulty=max(base_problem.difficulty, 3),
        prompt=f"""# Optimization Challenge: {target_complexity}

{base_problem.prompt}

## Additional Requirement:
Your solution MUST run in {target_complexity} time complexity.
Solutions with worse complexity will fail the hidden performance tests.
""",
        public_test=enhanced_test,
        hidden_test_encrypted="",
        hidden_test_nonce="",
        hidden_test_tag="",
        time_limit=base_problem.time_limit * 2,
        memory_limit=base_problem.memory_limit,
        language=base_problem.language,
        tags=base_problem.tags + ["complexity", "optimization", target_complexity.replace("(", "").replace(")", "").replace("^", "")],
        source_type=base_problem.source_type,
        expected_complexity=target_complexity,
        deterministic=base_problem.deterministic,
        task_type=TaskType.OPTIMIZATION.value,
        version=base_problem.version,
        metadata={
            **base_problem.metadata,
            "base_task_id": base_problem.task_id,
            "target_complexity": target_complexity,
            "reference_solution": reference_solution,
            "naive_solution": naive_solution,
            "performance_tests": perf_tests,
        }
    )
    return challenge


def verify_complexity(
    solution: str,
    problem: Problem,
    test_inputs: List[str],
    max_times: List[float],
    language: str = "python"
) -> Dict[str, Any]:
    """Verify solution meets complexity requirements."""
    runner = get_runner(language, problem.time_limit, problem.memory_limit)
    results = []

    for input_data, max_time in zip(test_inputs, max_times):
        test_code = f"{solution}\nimport time\nstart = time.time()\nresult = solve({input_data})\nelapsed = (time.time() - start) * 1000\nprint(f'TIME:{{elapsed}}')\nprint(result)"
        result = runner.execute(test_code)

        passed = result.success and result.execution_time_ms <= max_time
        results.append({
            "input_size": len(input_data),
            "time_ms": result.execution_time_ms,
            "max_time_ms": max_time,
            "passed": passed,
            "output": result.stdout,
        })

    all_passed = all(r["passed"] for r in results)
    return {
        "passed": all_passed,
        "details": results,
        "summary": f"{sum(1 for r in results if r['passed'])}/{len(results)} performance tests passed",
    }


def estimate_complexity_class(times: List[float], sizes: List[int]) -> str:
    """Estimate complexity class from timing data."""
    if len(times) < 3:
        return "Unknown"

    # Fit to common complexity classes
    import math

    ratios = []
    for i in range(1, len(times)):
        if times[i-1] > 0:
            size_ratio = sizes[i] / sizes[i-1]
            time_ratio = times[i] / times[i-1]
            ratios.append((size_ratio, time_ratio))

    if not ratios:
        return "Unknown"

    # Check which complexity fits best
    avg_ratio = sum(t/s for s, t in ratios) / len(ratios)

    if avg_ratio < 1.5:
        return "O(1) or O(log n)"
    elif avg_ratio < 2.5:
        return "O(n)"
    elif avg_ratio < 4:
        return "O(n log n)"
    elif avg_ratio < 8:
        return "O(n^2)"
    else:
        return "O(n^3) or worse"


COMPLEXITY_PROMPT_TEMPLATE = """# Optimization Challenge: {complexity_class}

{base_prompt}

## Critical Requirement:
Your solution MUST achieve **{complexity_class}** time complexity.
Implementations with worse asymptotic complexity will fail hidden performance tests.

## Performance Constraints:
- Time limit: {time_limit}s
- Memory limit: {memory_limit}MB
- Test inputs up to size N where naive O(N^2) would timeout

## Example:
{example}

## Your Task:
Implement the function with optimal complexity. Return only the implementation.
"""