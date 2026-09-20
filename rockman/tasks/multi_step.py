"""Multi-step reasoning task utilities"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rockman.benchmark.schema import Problem, TaskType


@dataclass
class Step:
    """A single step in a multi-step problem."""
    number: int
    description: str
    input_from_previous: Optional[str] = None
    output_to_next: Optional[str] = None
    verification_code: str = ""


MULTI_STEP_TEMPLATES = {
    "parse_build_solve": {
        "name": "Parse → Build → Solve",
        "steps": [
            Step(1, "Parse the input string into structured data", output_to_next="parsed_data"),
            Step(2, "Build the appropriate data structure from parsed data", input_from_previous="parsed_data", output_to_next="data_structure"),
            Step(3, "Apply the algorithm to solve the problem", input_from_previous="data_structure", output_to_next="result"),
            Step(4, "Format and return the result", input_from_previous="result"),
        ],
        "example_problem": "Given a string representation of a graph, parse it, build adjacency list, find shortest path, return path length.",
    },
    "multi_phase_algorithm": {
        "name": "Multi-phase Algorithm",
        "steps": [
            Step(1, "Preprocess input (sort, filter, transform)", output_to_next="preprocessed"),
            Step(2, "Phase 1: Build auxiliary structure", input_from_previous="preprocessed", output_to_next="aux_structure"),
            Step(3, "Phase 2: Main computation using auxiliary structure", input_from_previous="aux_structure", output_to_next="intermediate"),
            Step(4, "Phase 3: Post-process and extract answer", input_from_previous="intermediate"),
        ],
        "example_problem": "Process a stream of operations: build segment tree, handle queries, output results.",
    },
    "pipeline_processing": {
        "name": "Pipeline Processing",
        "steps": [
            Step(1, "Stage 1: Input validation and normalization", output_to_next="validated"),
            Step(2, "Stage 2: Feature extraction", input_from_previous="validated", output_to_next="features"),
            Step(3, "Stage 3: Model inference / core algorithm", input_from_previous="features", output_to_next="predictions"),
            Step(4, "Stage 4: Result aggregation and formatting", input_from_previous="predictions"),
        ],
        "example_problem": "Process log files: parse, extract metrics, detect anomalies, generate report.",
    },
}


def create_multi_step_problem(
    template_key: str,
    problem_statement: str,
    function_signature: str,
    test_cases: List[Dict[str, Any]],
    task_id: str = None,
    difficulty: int = 5,
) -> Problem:
    """Create a multi-step reasoning problem."""
    if template_key not in MULTI_STEP_TEMPLATES:
        raise ValueError(f"Unknown template: {template_key}")

    template = MULTI_STEP_TEMPLATES[template_key]

    # Build prompt with step-by-step instructions
    prompt_lines = [
        function_signature,
        '    """',
        problem_statement,
        "",
        "## Required Steps:",
    ]

    for step in template["steps"]:
        prompt_lines.append(f"    {step.number}. {step.description}")
        if step.input_from_previous:
            prompt_lines.append(f"       (uses output from step {step.number - 1}: {step.input_from_previous})")
        if step.output_to_next:
            prompt_lines.append(f"       (produces: {step.output_to_next} for next step)")
    prompt_lines.append('    """')

    prompt = "\n".join(prompt_lines)

    # Build test code
    test_lines = []
    for i, tc in enumerate(test_cases):
        test_lines.append(f"# Test case {i+1}")
        for key, value in tc.items():
            if key != "expected":
                test_lines.append(f"{key} = {repr(value)}")
        test_lines.append(f"assert solve({', '.join(k for k in tc if k != 'expected')}) == {repr(tc['expected'])}")

    public_test = "\n".join(test_lines)

    problem = Problem(
        task_id=task_id or f"Rockman/MultiStep_{template_key}",
        category="Multi-step",
        subcategory=template["name"],
        difficulty=difficulty,
        prompt=prompt,
        public_test=public_test,
        hidden_test_encrypted="",
        hidden_test_nonce="",
        hidden_test_tag="",
        time_limit=5.0,
        memory_limit=512,
        language="python",
        tags=["multi-step", "reasoning", template_key],
        source_type="generated",
        expected_complexity="Varies by step",
        deterministic=True,
        task_type=TaskType.MULTI_STEP.value,
        version="v0.2",
        metadata={
            "template": template_key,
            "steps": [{"number": s.number, "description": s.description} for s in template["steps"]],
        }
    )
    return problem


def generate_multi_step_chain(
    steps: List[Dict[str, Any]],
    function_signature: str,
) -> str:
    """Generate a multi-step function skeleton."""
    lines = [
        function_signature,
        '    """',
        "Multi-step problem:",
    ]
    for i, step in enumerate(steps, 1):
        lines.append(f"    Step {i}: {step['description']}")
    lines.append('    """')

    for i, step in enumerate(steps, 1):
        lines.append(f"    # Step {i}: {step['description']}")
        if "code" in step:
            for line in step["code"].split("\n"):
                lines.append(f"    {line}")
        else:
            lines.append(f"    step_{i}_result = ...  # TODO")

    lines.append("    return final_result")
    return "\n".join(lines)


def verify_step_outputs(
    solution: str,
    test_input: Any,
    expected_intermediates: Dict[str, Any],
) -> Dict[str, bool]:
    """Verify each step produces expected intermediate output."""
    # This would require instrumenting the solution to capture intermediate values
    # For now, return placeholder
    return {k: True for k in expected_intermediates}


MULTI_STEP_PROMPT_TEMPLATE = """# Multi-Step Reasoning Challenge

{problem_statement}

## Function Signature:
{function_signature}

## Required Steps:
{steps}

## Test Cases:
{test_cases}

## Instructions:
1. Implement ALL steps in order
2. Each step's output feeds into the next step
3. Return the final result
4. Do not skip or reorder steps
5. Return only the complete implementation
"""