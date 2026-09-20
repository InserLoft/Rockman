"""Category taxonomy for Rockman benchmark"""

CATEGORIES = {
    "Fundamentals": {
        "subcategories": [
            "Arrays", "Strings", "Hash Tables", "Sorting", "Searching",
            "Two Pointers", "Sliding Window", "Prefix Sum", "Difference Array", "Binary Search"
        ],
        "difficulty_range": (1, 3),
        "tags": ["fundamental", "basic"],
    },
    "Data Structures": {
        "subcategories": [
            "Stack", "Queue", "Deque", "Linked List", "Heap/Priority Queue",
            "Hash Map", "Union-Find/DSU", "Segment Tree", "Fenwick Tree",
            "Trie", "Sparse Table", "Monotonic Stack", "Monotonic Queue"
        ],
        "difficulty_range": (2, 4),
        "tags": ["data-structure"],
    },
    "Algorithms": {
        "subcategories": [
            "Greedy", "Divide & Conquer", "Backtracking", "Recursion",
            "Dynamic Programming", "Bit Manipulation", "Randomized Algorithms",
            "Computational Geometry"
        ],
        "difficulty_range": (2, 5),
        "tags": ["algorithm"],
    },
    "Graphs": {
        "subcategories": [
            "BFS", "DFS", "Shortest Path", "Dijkstra", "Bellman-Ford", "Floyd-Warshall",
            "MST", "Kruskal", "Prim", "Topological Sort", "SCC", "Bipartite Graphs",
            "Flow/Max Flow", "Matching", "Eulerian Paths", "Hamiltonian Problems"
        ],
        "difficulty_range": (3, 6),
        "tags": ["graph"],
    },
    "Trees": {
        "subcategories": [
            "Binary Trees", "BST", "AVL/Balanced Trees", "Tree DP", "LCA",
            "Tree Traversal", "Subtree Queries", "Heavy-Light Decomposition"
        ],
        "difficulty_range": (3, 5),
        "tags": ["tree"],
    },
    "Math": {
        "subcategories": [
            "Number Theory", "Prime Numbers", "GCD/LCM", "Modular Arithmetic",
            "Combinatorics", "Probability", "Matrix Operations", "Linear Algebra",
            "Numerical Methods", "Geometry"
        ],
        "difficulty_range": (2, 5),
        "tags": ["math"],
    },
    "Debugging": {
        "subcategories": [
            "Logic Bugs", "Off-by-One", "Edge Cases", "Type Errors",
            "State Mutation", "Infinite Loops", "Incorrect Complexity", "Recursion Bugs"
        ],
        "difficulty_range": (2, 4),
        "tags": ["debugging", "bug-fix"],
    },
    "Complexity": {
        "subcategories": [
            "O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)", "Space Complexity"
        ],
        "difficulty_range": (3, 5),
        "tags": ["complexity", "optimization"],
    },
    "Software Engineering": {
        "subcategories": [
            "Class Design", "Inheritance/Extension", "Refactoring",
            "Feature Addition", "Backwards Compatibility", "Exception Handling",
            "Parser Implementation", "Interface Implementation",
            "Regression Fix", "Performance Optimization"
        ],
        "difficulty_range": (3, 5),
        "tags": ["software-engineering", "oop"],
    },
    "Stateful Systems": {
        "subcategories": [
            "Cache/LRU", "Banking Ledger", "Event Processor", "Task Scheduler",
            "Game State", "Inventory", "Session Manager", "Transaction System"
        ],
        "difficulty_range": (4, 6),
        "tags": ["stateful", "system-design"],
    },
    "Multi-step": {
        "subcategories": [
            "Parse + Build + Solve", "Multi-phase Algorithm", "Pipeline Processing"
        ],
        "difficulty_range": (4, 6),
        "tags": ["multi-step", "reasoning"],
    },
}


EDGE_CASE_TAGS = [
    "empty-input", "single-element", "duplicates", "negative-values",
    "very-large-values", "very-large-input", "already-sorted", "reverse-sorted",
    "cycles", "disconnected-graphs", "overflow", "unicode", "repeated-patterns",
    "edge-case", "boundary-condition",
]


DIFFICULTY_LABELS = {
    1: "Introductory",
    2: "Easy",
    3: "Intermediate",
    4: "Advanced",
    5: "Hard",
    6: "Expert",
    7: "Research",
}


def get_category_info(category: str) -> Dict:
    return CATEGORIES.get(category, {})


def get_subcategories(category: str) -> List[str]:
    return CATEGORIES.get(category, {}).get("subcategories", [])


def get_difficulty_range(category: str) -> tuple:
    return CATEGORIES.get(category, {}).get("difficulty_range", (1, 5))


def validate_category(category: str, subcategory: str) -> bool:
    return subcategory in get_subcategories(category)


def get_all_categories() -> List[str]:
    return list(CATEGORIES.keys())


def get_all_subcategories() -> List[tuple]:
    result = []
    for cat, info in CATEGORIES.items():
        for sub in info["subcategories"]:
            result.append((cat, sub))
    return result


def suggest_difficulty(category: str, subcategory: str) -> int:
    low, high = get_difficulty_range(category)
    return (low + high) // 2


def get_category_tags(category: str) -> List[str]:
    return CATEGORIES.get(category, {}).get("tags", [])


def get_edge_case_tags() -> List[str]:
    return EDGE_CASE_TAGS


def get_difficulty_label(level: int) -> str:
    return DIFFICULTY_LABELS.get(level, "Unknown")