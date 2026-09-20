"""Rockman Task Types - Specialized task implementations"""

from rockman.tasks.debugging import (
    BUG_PATTERNS,
    inject_off_by_one,
    inject_edge_case_bug,
    inject_type_error,
    inject_state_mutation,
    inject_infinite_loop,
    inject_complexity_bug,
    inject_recursion_bug,
    inject_logic_bug,
    create_buggy_version,
    generate_debugging_prompt,
    create_debugging_problem,
    DEBUGGING_PROMPT_TEMPLATE,
)

from rockman.tasks.complexity import (
    COMPLEXITY_CLASSES,
    generate_performance_test,
    generate_input_for_problem,
    create_complexity_challenge,
    verify_complexity,
    estimate_complexity_class,
    COMPLEXITY_PROMPT_TEMPLATE,
)

from rockman.tasks.stateful import (
    StatefulOperation,
    StatefulScenario,
    STATEFUL_TEMPLATES,
    generate_stateful_test_code,
    create_stateful_problem,
    create_all_stateful_problems,
)

from rockman.tasks.multi_step import (
    Step,
    MULTI_STEP_TEMPLATES,
    create_multi_step_problem,
    generate_multi_step_chain,
    verify_step_outputs,
    MULTI_STEP_PROMPT_TEMPLATE,
)

__all__ = [
    "BUG_PATTERNS",
    "inject_off_by_one",
    "inject_edge_case_bug",
    "inject_type_error",
    "inject_state_mutation",
    "inject_infinite_loop",
    "inject_complexity_bug",
    "inject_recursion_bug",
    "inject_logic_bug",
    "create_buggy_version",
    "generate_debugging_prompt",
    "create_debugging_problem",
    "DEBUGGING_PROMPT_TEMPLATE",
    "COMPLEXITY_CLASSES",
    "generate_performance_test",
    "generate_input_for_problem",
    "create_complexity_challenge",
    "verify_complexity",
    "estimate_complexity_class",
    "COMPLEXITY_PROMPT_TEMPLATE",
    "StatefulOperation",
    "StatefulScenario",
    "STATEFUL_TEMPLATES",
    "generate_stateful_test_code",
    "create_stateful_problem",
    "create_all_stateful_problems",
    "Step",
    "MULTI_STEP_TEMPLATES",
    "create_multi_step_problem",
    "generate_multi_step_chain",
    "verify_step_outputs",
    "MULTI_STEP_PROMPT_TEMPLATE",
]