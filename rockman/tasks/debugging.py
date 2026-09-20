"""Debugging task utilities - bug injection, prompt templates"""

import ast
import random
from typing import List, Dict, Any, Optional, Tuple
from rockman.benchmark.schema import Problem, TaskType


BUG_PATTERNS = {
    "off-by-one": {
        "description": "Off-by-one error in loop bounds or array indexing",
        "inject": lambda code: inject_off_by_one(code),
        "tags": ["off-by-one", "logic-bug", "indexing"],
    },
    "edge-case": {
        "description": "Missing edge case handling (empty, single element, null)",
        "inject": lambda code: inject_edge_case_bug(code),
        "tags": ["edge-case", "empty-input", "boundary"],
    },
    "type-error": {
        "description": "Type confusion or missing type checks",
        "inject": lambda code: inject_type_error(code),
        "tags": ["type-error", "type-confusion"],
    },
    "state-mutation": {
        "description": "Incorrect state mutation or shared mutable state",
        "inject": lambda code: inject_state_mutation(code),
        "tags": ["state-mutation", "side-effect"],
    },
    "infinite-loop": {
        "description": "Loop termination condition never met",
        "inject": lambda code: inject_infinite_loop(code),
        "tags": ["infinite-loop", "termination"],
    },
    "complexity-bug": {
        "description": "Algorithmically correct but wrong complexity class",
        "inject": lambda code: inject_complexity_bug(code),
        "tags": ["complexity-bug", "performance"],
    },
    "recursion-bug": {
        "description": "Missing base case or incorrect recursive call",
        "inject": lambda code: inject_recursion_bug(code),
        "tags": ["recursion-bug", "stack-overflow"],
    },
    "logic-bug": {
        "description": "General logic error in algorithm",
        "inject": lambda code: inject_logic_bug(code),
        "tags": ["logic-bug", "algorithm"],
    },
}


def inject_off_by_one(code: str) -> str:
    """Inject off-by-one error."""
    lines = code.split("\n")
    for i, line in enumerate(lines):
        if "range(len(" in line and ")" in line:
            lines[i] = line.replace("range(len(", "range(len(").replace("))", "))")
            if "range(len(" in lines[i] and "- 1" not in lines[i]:
                lines[i] = lines[i].replace("range(len(", "range(len(")
        if "for i in range(" in line and "len(" in line:
            if "- 1" not in line:
                lines[i] = line.replace("range(", "range(").replace("len(", "len(")
    return "\n".join(lines)


def inject_edge_case_bug(code: str) -> str:
    """Remove edge case handling."""
    lines = code.split("\n")
    new_lines = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        stripped = line.strip()
        if stripped.startswith("if not ") or stripped.startswith("if len(") == 0:
            skip_next = True
            continue
        if "empty" in stripped.lower() or "null" in stripped.lower() or "none" in stripped.lower():
            if "return" in line or "raise" in line:
                skip_next = True
                continue
        new_lines.append(line)
    return "\n".join(new_lines)


def inject_type_error(code: str) -> str:
    """Inject type-related bug."""
    return code.replace("isinstance(", "# isinstance(").replace("type(", "# type(")


def inject_state_mutation(code: str) -> str:
    """Inject state mutation bug."""
    return code.replace("self.", "self._").replace("this.", "this._")


def inject_infinite_loop(code: str) -> str:
    """Inject infinite loop bug."""
    lines = code.split("\n")
    for i, line in enumerate(lines):
        if "while " in line and "True" in line:
            lines[i] = line.replace("while True:", "while True:  # BUG: missing break")
    return "\n".join(lines)


def inject_complexity_bug(code: str) -> str:
    """Replace efficient algorithm with inefficient one."""
    if "bisect" in code or "heapq" in code:
        return code.replace("bisect_left", "# bisect_left").replace("heappush", "# heappush")
    return code


def inject_recursion_bug(code: str) -> str:
    """Inject recursion bug."""
    lines = code.split("\n")
    for i, line in enumerate(lines):
        if "def " in line and "(" in line and "):" in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith("if ") and "return" in next_line:
                    lines[i + 1] = "    # BUG: base case removed"
    return "\n".join(lines)


def inject_logic_bug(code: str) -> str:
    """Inject general logic bug."""
    return code.replace(">=", ">").replace("<=", "<").replace("==", "!=").replace("!=", "==")


def create_buggy_version(correct_code: str, bug_type: str) -> Tuple[str, str]:
    """Create a buggy version of correct code."""
    if bug_type not in BUG_PATTERNS:
        bug_type = random.choice(list(BUG_PATTERNS.keys()))

    pattern = BUG_PATTERNS[bug_type]
    buggy_code = pattern["inject"](correct_code)

    # Ensure the bug was actually injected
    if buggy_code == correct_code:
        buggy_code = inject_logic_bug(correct_code)

    return buggy_code, bug_type


def generate_debugging_prompt(problem: Problem, buggy_code: str, bug_type: str) -> str:
    """Generate prompt for debugging task."""
    bug_info = BUG_PATTERNS.get(bug_type, {})
    return f"""# Debugging Challenge: {bug_info.get('description', 'Fix the bug')}

The following code has a bug. Identify and fix it.

## Buggy Code:
```python
{buggy_code}
```

## Problem:
{problem.prompt}

## Tests (your fix must pass these):
{problem.public_test}

## Instructions:
1. Analyze the buggy code to identify the issue
2. Provide the corrected implementation
3. Return ONLY the fixed function/class code
"""


def create_debugging_problem(
    base_problem: Problem,
    correct_solution: str,
    bug_type: str = None
) -> Problem:
    """Create a debugging task from a base problem and solution."""
    if bug_type is None:
        bug_type = random.choice(list(BUG_PATTERNS.keys()))

    buggy_code, actual_bug_type = create_buggy_version(correct_solution, bug_type)

    debug_problem = Problem(
        task_id=f"{base_problem.task_id}_debug_{actual_bug_type}",
        category="Debugging",
        subcategory=actual_bug_type.replace("-", " ").title(),
        difficulty=base_problem.difficulty,
        prompt=generate_debugging_prompt(base_problem, buggy_code, actual_bug_type),
        public_test=base_problem.public_test,
        hidden_test_encrypted=base_problem.hidden_test_encrypted,
        hidden_test_nonce=base_problem.hidden_test_nonce,
        hidden_test_tag=base_problem.hidden_test_tag,
        time_limit=base_problem.time_limit,
        memory_limit=base_problem.memory_limit,
        language=base_problem.language,
        tags=base_problem.tags + ["debugging", actual_bug_type] + BUG_PATTERNS[actual_bug_type]["tags"],
        source_type=base_problem.source_type,
        expected_complexity=base_problem.expected_complexity,
        deterministic=base_problem.deterministic,
        task_type=TaskType.DEBUGGING.value,
        version=base_problem.version,
        metadata={
            **base_problem.metadata,
            "base_task_id": base_problem.task_id,
            "bug_type": actual_bug_type,
            "buggy_code": buggy_code,
            "correct_solution": correct_solution,
        }
    )
    return debug_problem


DEBUGGING_PROMPT_TEMPLATE = """# Debugging Task: {bug_description}

The following implementation contains a bug. Your task is to identify and fix it.

## Buggy Implementation:
```{language}
{buggy_code}
```

## Problem Specification:
{prompt}

## Test Cases (your fix must pass all):
{public_test}

## Requirements:
- Fix ONLY the bug - do not change the algorithm or approach unnecessarily
- Maintain the same function signature
- Return the complete corrected implementation
- Do not include explanations, only code
"""