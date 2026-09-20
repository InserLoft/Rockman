"""Rockman Dataset Generation and Management"""

from rockman.dataset.categories import (
    CATEGORIES,
    get_category_info,
    get_subcategories,
    get_difficulty_range,
    validate_category,
    get_all_categories,
    get_all_subcategories,
    suggest_difficulty,
    get_category_tags,
    get_edge_case_tags,
    get_difficulty_label,
    EDGE_CASE_TAGS,
    DIFFICULTY_LABELS,
)

from rockman.dataset.validators import (
    TaskValidator,
    ValidationResult,
    validate_task,
    validate_dataset,
    generate_validation_report,
)

from rockman.dataset.generator import (
    TaskTemplate,
    TaskGenerator,
    get_all_templates,
    create_dp_templates,
    create_graph_templates,
    create_debugging_templates,
    create_stateful_templates,
    create_complexity_templates,
    generate_benchmark_dataset,
)

from rockman.dataset.splits import (
    DatasetSplit,
    SplitManager,
    create_canary_strings,
    check_contamination,
)

__all__ = [
    "CATEGORIES",
    "get_category_info",
    "get_subcategories",
    "get_difficulty_range",
    "validate_category",
    "get_all_categories",
    "get_all_subcategories",
    "suggest_difficulty",
    "get_category_tags",
    "get_edge_case_tags",
    "get_difficulty_label",
    "EDGE_CASE_TAGS",
    "DIFFICULTY_LABELS",
    "TaskValidator",
    "ValidationResult",
    "validate_task",
    "validate_dataset",
    "generate_validation_report",
    "TaskTemplate",
    "TaskGenerator",
    "get_all_templates",
    "create_dp_templates",
    "create_graph_templates",
    "create_debugging_templates",
    "create_stateful_templates",
    "create_complexity_templates",
    "generate_benchmark_dataset",
    "DatasetSplit",
    "SplitManager",
    "create_canary_strings",
    "check_contamination",
]