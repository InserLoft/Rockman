"""Stateful task utilities - classes with persistent state"""

from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from rockman.benchmark.schema import Problem, TaskType


@dataclass
class StatefulOperation:
    """Represents a single operation in a stateful task."""
    method: str
    args: List[Any]
    expected_return: Any
    description: str = ""


@dataclass
class StatefulScenario:
    """A complete scenario for a stateful task."""
    name: str
    initial_state: Dict[str, Any]
    operations: List[StatefulOperation]
    final_state_check: Optional[Callable] = None


STATEFUL_TEMPLATES = {
    "lru_cache": {
        "class_name": "LRUCache",
        "methods": ["__init__", "get", "put"],
        "init_args": ["capacity"],
        "scenarios": [
            StatefulScenario(
                name="basic_lru",
                initial_state={"capacity": 2},
                operations=[
                    StatefulOperation("put", [1, 1], None, "Insert key 1"),
                    StatefulOperation("put", [2, 2], None, "Insert key 2"),
                    StatefulOperation("get", [1], 1, "Get key 1"),
                    StatefulOperation("put", [3, 3], None, "Insert key 3 (evicts 2)"),
                    StatefulOperation("get", [2], -1, "Key 2 should be evicted"),
                    StatefulOperation("get", [3], 3, "Key 3 should exist"),
                    StatefulOperation("put", [4, 4], None, "Insert key 4 (evicts 1)"),
                    StatefulOperation("get", [1], -1, "Key 1 should be evicted"),
                    StatefulOperation("get", [3], 3, "Key 3 should exist"),
                    StatefulOperation("get", [4], 4, "Key 4 should exist"),
                ],
            ),
            StatefulScenario(
                name="update_existing",
                initial_state={"capacity": 2},
                operations=[
                    StatefulOperation("put", [1, 1], None, "Insert key 1"),
                    StatefulOperation("put", [1, 10], None, "Update key 1"),
                    StatefulOperation("get", [1], 10, "Should return updated value"),
                ],
            ),
        ],
    },
    "banking_ledger": {
        "class_name": "BankingLedger",
        "methods": ["__init__", "deposit", "withdraw", "transfer", "get_balance", "get_history"],
        "init_args": [],
        "scenarios": [
            StatefulScenario(
                name="basic_banking",
                initial_state={},
                operations=[
                    StatefulOperation("deposit", ["acc1", 100], True, "Deposit 100 to acc1"),
                    StatefulOperation("deposit", ["acc2", 50], True, "Deposit 50 to acc2"),
                    StatefulOperation("withdraw", ["acc1", 30], True, "Withdraw 30 from acc1"),
                    StatefulOperation("get_balance", ["acc1"], 70, "Balance should be 70"),
                    StatefulOperation("get_balance", ["acc2"], 50, "Balance should be 50"),
                    StatefulOperation("transfer", ["acc1", "acc2", 20], True, "Transfer 20 from acc1 to acc2"),
                    StatefulOperation("get_balance", ["acc1"], 50, "Balance should be 50"),
                    StatefulOperation("get_balance", ["acc2"], 70, "Balance should be 70"),
                    StatefulOperation("withdraw", ["acc1", 100], False, "Insufficient funds"),
                    StatefulOperation("get_history", ["acc1"], None, "Check transaction history"),
                ],
            ),
        ],
    },
    "event_processor": {
        "class_name": "EventProcessor",
        "methods": ["__init__", "subscribe", "unsubscribe", "emit", "get_event_count"],
        "init_args": [],
        "scenarios": [
            StatefulScenario(
                name="pub_sub",
                initial_state={},
                operations=[
                    StatefulOperation("subscribe", ["event1", "handler1"], None, "Subscribe handler1 to event1"),
                    StatefulOperation("subscribe", ["event1", "handler2"], None, "Subscribe handler2 to event1"),
                    StatefulOperation("emit", ["event1", {"data": "test"}], 2, "Emit event1, should call 2 handlers"),
                    StatefulOperation("unsubscribe", ["event1", "handler1"], None, "Unsubscribe handler1"),
                    StatefulOperation("emit", ["event1", {"data": "test2"}], 1, "Emit event1, should call 1 handler"),
                    StatefulOperation("get_event_count", ["event1"], 2, "Total events emitted"),
                ],
            ),
        ],
    },
    "task_scheduler": {
        "class_name": "TaskScheduler",
        "methods": ["__init__", "add_task", "remove_task", "run_next", "get_pending"],
        "init_args": [],
        "scenarios": [
            StatefulScenario(
                name="priority_scheduling",
                initial_state={},
                operations=[
                    StatefulOperation("add_task", ["task1", 1, "low"], None, "Add low priority task"),
                    StatefulOperation("add_task", ["task2", 10, "high"], None, "Add high priority task"),
                    StatefulOperation("add_task", ["task3", 5, "medium"], None, "Add medium priority task"),
                    StatefulOperation("run_next", [], "task2", "Should run highest priority"),
                    StatefulOperation("run_next", [], "task3", "Should run medium priority"),
                    StatefulOperation("run_next", [], "task1", "Should run low priority"),
                    StatefulOperation("get_pending", [], 0, "No pending tasks"),
                ],
            ),
        ],
    },
    "game_state": {
        "class_name": "GameState",
        "methods": ["__init__", "move", "get_position", "get_score", "is_game_over"],
        "init_args": ["board_size"],
        "scenarios": [
            StatefulScenario(
                name="simple_game",
                initial_state={"board_size": 10},
                operations=[
                    StatefulOperation("move", ["up"], True, "Move up"),
                    StatefulOperation("move", ["up"], True, "Move up"),
                    StatefulOperation("move", ["right"], True, "Move right"),
                    StatefulOperation("get_position", [], (0, 2), "Position should be (0, 2)"),
                    StatefulOperation("get_score", [], 3, "Score should be 3"),
                    StatefulOperation("move", ["down"], True, "Move down"),
                    StatefulOperation("move", ["left"], True, "Move left"),
                    StatefulOperation("get_position", [], (1, 1), "Position should be (1, 1)"),
                ],
            ),
        ],
    },
    "inventory": {
        "class_name": "Inventory",
        "methods": ["__init__", "add_item", "remove_item", "get_quantity", "list_items"],
        "init_args": [],
        "scenarios": [
            StatefulScenario(
                name="inventory_management",
                initial_state={},
                operations=[
                    StatefulOperation("add_item", ["sword", 1], True, "Add sword"),
                    StatefulOperation("add_item", ["potion", 5], True, "Add 5 potions"),
                    StatefulOperation("get_quantity", ["sword"], 1, "Sword count"),
                    StatefulOperation("get_quantity", ["potion"], 5, "Potion count"),
                    StatefulOperation("remove_item", ["potion", 2], True, "Remove 2 potions"),
                    StatefulOperation("get_quantity", ["potion"], 3, "Potion count should be 3"),
                    StatefulOperation("remove_item", ["potion", 5], False, "Not enough potions"),
                    StatefulOperation("list_items", [], ["sword", "potion"], "List all items"),
                ],
            ),
        ],
    },
}


def generate_stateful_test_code(scenario: StatefulScenario, class_name: str) -> str:
    """Generate test code for a stateful scenario."""
    lines = [
        f"# Test scenario: {scenario.name}",
        f"obj = {class_name}(**{scenario.initial_state})",
    ]

    for op in scenario.operations:
        args_str = ", ".join(repr(arg) for arg in op.args)
        if op.expected_return is not None:
            exp_str = repr(op.expected_return)
            lines.append(f"assert obj.{op.method}({args_str}) == {exp_str}, '{op.description}'")
        else:
            lines.append(f"obj.{op.method}({args_str})  # {op.description}")

    return "\n".join(lines)


def create_stateful_problem(
    template_key: str,
    scenario_name: str = None,
    task_id: str = None,
    difficulty: int = 4,
) -> Problem:
    """Create a stateful task problem from template."""
    if template_key not in STATEFUL_TEMPLATES:
        raise ValueError(f"Unknown template: {template_key}")

    template = STATEFUL_TEMPLATES[template_key]
    class_name = template["class_name"]

    if scenario_name:
        scenario = next((s for s in template["scenarios"] if s.name == scenario_name), None)
        if not scenario:
            raise ValueError(f"Scenario {scenario_name} not found in {template_key}")
        scenarios = [scenario]
    else:
        scenarios = template["scenarios"]

    # Build prompt with class skeleton
    methods = template["methods"]
    prompt_lines = [
        f"class {class_name}_{task_id or template_key}:",
        f'    """{template_key.replace("_", " ").title()} implementation."""',
    ]

    for method in methods:
        if method == "__init__":
            args = ", ".join(template["init_args"])
            prompt_lines.append(f"    def __init__(self, {args}):")
            prompt_lines.append("        pass")
        else:
            prompt_lines.append(f"    def {method}(self, *args, **kwargs):")
            prompt_lines.append("        pass")

    prompt = "\n".join(prompt_lines)

    # Build test code
    test_parts = []
    for scenario in scenarios:
        test_parts.append(generate_stateful_test_code(scenario, f"{class_name}_{task_id or template_key}"))

    public_test = "\n\n".join(test_parts)

    problem = Problem(
        task_id=task_id or f"Rockman/Stateful_{template_key}",
        category="Stateful Systems",
        subcategory=template_key.replace("_", "/").title(),
        difficulty=difficulty,
        prompt=prompt,
        public_test=public_test,
        hidden_test_encrypted="",
        hidden_test_nonce="",
        hidden_test_tag="",
        time_limit=2.0,
        memory_limit=256,
        language="python",
        tags=["stateful", template_key, "class-design", "oop"],
        source_type="generated",
        expected_complexity="O(1) per operation",
        deterministic=True,
        task_type=TaskType.STATEFUL.value,
        version="v0.2",
        metadata={
            "template": template_key,
            "class_name": class_name,
            "scenarios": [s.name for s in scenarios],
        }
    )
    return problem


def create_all_stateful_problems() -> List[Problem]:
    """Create all standard stateful problems."""
    problems = []
    for template_key in STATEFUL_TEMPLATES:
        for scenario in STATEFUL_TEMPLATES[template_key]["scenarios"]:
            problem = create_stateful_problem(template_key, scenario.name)
            problems.append(problem)
    return problems