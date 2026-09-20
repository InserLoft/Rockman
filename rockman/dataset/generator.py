"""Task generation for Rockman benchmark"""

import random
import string
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from rockman.benchmark.schema import Problem, TaskType, Language, DifficultyLevel, SourceType
from rockman.dataset.categories import (
    CATEGORIES, get_subcategories, get_difficulty_range,
    suggest_difficulty, get_category_tags, EDGE_CASE_TAGS
)


@dataclass
class TaskTemplate:
    """Template for generating parametric task families."""
    category: str
    subcategory: str
    prompt_template: str
    public_test_template: str
    hidden_test_template: str = ""
    reference_solution: str = ""
    buggy_solutions: List[str] = None
    default_difficulty: int = 3
    tags: List[str] = None
    expected_complexity: str = ""
    task_type: str = TaskType.GENERATION.value
    parameters: Dict[str, List[Any]] = None

    def __post_init__(self):
        if self.buggy_solutions is None:
            self.buggy_solutions = []
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = {}


class TaskGenerator:
    """Generates tasks from templates with parameter variation."""

    def __init__(self, encryption=None):
        self.encryption = encryption
        self.templates: List[TaskTemplate] = []
        self.generated_count = 0

    def add_template(self, template: TaskTemplate):
        self.templates.append(template)

    def generate_from_template(self, template: TaskTemplate, param_values: Dict[str, Any],
                               task_index: int) -> Problem:
        """Generate a single task from template with specific parameters."""
        self.generated_count += 1
        task_id = f"Rockman/{template.category[:4].upper()}_{self.generated_count:04d}"
        # Sanitize task_id for use in function names (replace / and - with _)
        func_suffix = task_id.replace("/", "_").replace("-", "_")

        prompt = template.prompt_template.format(**param_values, task_id=task_id, func_suffix=func_suffix)
        public_test = template.public_test_template.format(**param_values, task_id=task_id, func_suffix=func_suffix)
        hidden_test = template.hidden_test_template.format(**param_values, task_id=task_id, func_suffix=func_suffix) if template.hidden_test_template else ""

        difficulty = param_values.get("difficulty", template.default_difficulty)
        tags = template.tags + param_values.get("extra_tags", [])

        problem = Problem(
            task_id=task_id,
            category=template.category,
            subcategory=template.subcategory,
            difficulty=difficulty,
            prompt=prompt,
            public_test=public_test,
            hidden_test_encrypted="",
            hidden_test_nonce="",
            hidden_test_tag="",
            time_limit=param_values.get("time_limit", 2.0),
            memory_limit=param_values.get("memory_limit", 256),
            language=param_values.get("language", "python"),
            tags=tags,
            source_type=SourceType.GENERATED.value,
            expected_complexity=template.expected_complexity,
            deterministic=param_values.get("deterministic", True),
            task_type=template.task_type,
            version="v0.2",
            metadata={
                "generator": "TaskGenerator",
                "template_category": template.category,
                "template_subcategory": template.subcategory,
                "parameters": param_values,
                "_hidden_test_raw": hidden_test,
            }
        )

        if self.encryption and hidden_test:
            problem = self.encryption.encrypt_problem_hidden_tests(problem)

        return problem

    def generate_family(self, template: TaskTemplate, count: int) -> List[Problem]:
        """Generate multiple tasks by varying parameters."""
        problems = []
        param_names = list(template.parameters.keys())

        for i in range(count):
            param_values = {}
            for param_name, values in template.parameters.items():
                param_values[param_name] = random.choice(values)
            param_values["difficulty"] = suggest_difficulty(template.category, template.subcategory)
            problem = self.generate_from_template(template, param_values, i)
            problems.append(problem)

        return problems


def create_dp_templates() -> List[TaskTemplate]:
    """Create Dynamic Programming task templates."""
    return [
        TaskTemplate(
            category="Algorithms",
            subcategory="Dynamic Programming",
            prompt_template="""def knapsack_{func_suffix}(weights: list[int], values: list[int], capacity: int) -> int:
    \"\"\"
    0/1 Knapsack Problem.
    Given weights and values of n items, put these items in a knapsack of capacity W
    to get the maximum total value in the knapsack.
    \"\"\"
""",
            public_test_template="""weights = [10, 20, 30]
values = [60, 100, 120]
capacity = 50
assert knapsack_{func_suffix}(weights, values, capacity) == 220

weights = [1, 2, 3]
values = [10, 20, 30]
capacity = 5
assert knapsack_{func_suffix}(weights, values, capacity) == 50
""",
            hidden_test_template="""# Edge cases
assert knapsack_{func_suffix}([], [], 10) == 0
assert knapsack_{func_suffix}([5], [10], 4) == 0
assert knapsack_{func_suffix}([5], [10], 5) == 10
# Large case
import random
weights = [random.randint(1, 100) for _ in range(100)]
values = [random.randint(1, 100) for _ in range(100)]
result = knapsack_{func_suffix}(weights, values, 1000)
assert result >= 0
""",
            reference_solution="""def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [0] * (capacity + 1)
    for i in range(n):
        for w in range(capacity, weights[i] - 1, -1):
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[capacity]""",
            buggy_solutions=[
                """def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [0] * (capacity + 1)
    for i in range(n):
        for w in range(weights[i], capacity + 1):  # Wrong direction
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[capacity]""",
                """def knapsack(weights, values, capacity):
    return sum(values)  # Always wrong""",
            ],
            default_difficulty=4,
            tags=["dp", "optimization", "knapsack"],
            expected_complexity="O(nW)",
            parameters={
                "n": [10, 20, 50, 100],
                "capacity": [50, 100, 500, 1000],
            },
        ),
        TaskTemplate(
            category="Algorithms",
            subcategory="Dynamic Programming",
            prompt_template="""def longest_increasing_subsequence_{func_suffix}(nums: list[int]) -> int:
    \"\"\"
    Find the length of the longest strictly increasing subsequence.
    \"\"\"
""",
            public_test_template="""assert longest_increasing_subsequence_{func_suffix}([10,9,2,5,3,7,101,18]) == 4
assert longest_increasing_subsequence_{func_suffix}([0,1,0,3,2,3]) == 4
assert longest_increasing_subsequence_{func_suffix}([7,7,7,7,7,7,7]) == 1
""",
            hidden_test_template="""assert longest_increasing_subsequence_{func_suffix}([]) == 0
assert longest_increasing_subsequence_{func_suffix}([1]) == 1
assert longest_increasing_subsequence_{func_suffix}([5,4,3,2,1]) == 1
import random
nums = [random.randint(1, 1000) for _ in range(2000)]
result = longest_increasing_subsequence_{func_suffix}(nums)
assert 1 <= result <= 2000
""",
            reference_solution="""def longest_increasing_subsequence(nums):
    if not nums:
        return 0
    dp = []
    for num in nums:
        import bisect
        i = bisect.bisect_left(dp, num)
        if i == len(dp):
            dp.append(num)
        else:
            dp[i] = num
    return len(dp)""",
            buggy_solutions=[
                """def longest_increasing_subsequence(nums):
    return len(set(nums))  # Wrong: counts unique, not increasing""",
            ],
            default_difficulty=3,
            tags=["dp", "binary-search", "lis"],
            expected_complexity="O(n log n)",
            parameters={},
        ),
    ]


def create_graph_templates() -> List[TaskTemplate]:
    """Create Graph algorithm templates."""
    return [
        TaskTemplate(
            category="Graphs",
            subcategory="Shortest Path",
            prompt_template="""def dijkstra_{func_suffix}(n: int, edges: list[tuple[int, int, int]], start: int) -> list[int]:
    \"\"\"
    Dijkstra's algorithm for single-source shortest paths.
    n: number of vertices (0-indexed)
    edges: list of (u, v, weight) for directed edges
    start: source vertex
    Returns list of distances, use -1 for unreachable.
    \"\"\"
""",
            public_test_template="""n = 5
edges = [(0,1,10), (0,2,3), (1,2,1), (1,3,2), (2,1,4), (2,3,8), (2,4,2), (3,4,7), (4,3,9)]
assert dijkstra_{func_suffix}(n, edges, 0) == [0, 7, 3, 9, 5]

n = 4
edges = [(0,1,1), (1,2,1), (2,3,1)]
assert dijkstra_{func_suffix}(n, edges, 0) == [0, 1, 2, 3]
""",
            hidden_test_template="""# Disconnected
assert dijkstra_{func_suffix}(3, [], 0) == [0, -1, -1]
# Negative weight (should handle or detect)
try:
    dijkstra_{func_suffix}(3, [(0,1,-1)], 0)
except:
    pass
# Large graph
import random
n = 1000
edges = []
for _ in range(5000):
    u = random.randint(0, n-1)
    v = random.randint(0, n-1)
    w = random.randint(1, 100)
    edges.append((u,v,w))
result = dijkstra_{func_suffix}(n, edges, 0)
assert len(result) == n
""",
            reference_solution="""def dijkstra(n, edges, start):
    import heapq
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [-1] * n
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            if dist[v] == -1 or dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                heapq.heappush(pq, (dist[v], v))
    return dist""",
            buggy_solutions=[
                """def dijkstra(n, edges, start):
    dist = [-1] * n
    dist[start] = 0
    for _ in range(n):
        for u, v, w in edges:
            if dist[u] != -1 and (dist[v] == -1 or dist[u] + w < dist[v]):
                dist[v] = dist[u] + w
    return dist  # Missing priority queue - O(nm) not O(m log n)""",
            ],
            default_difficulty=4,
            tags=["graph", "shortest-path", "dijkstra", "priority-queue"],
            expected_complexity="O((V+E) log V)",
            parameters={},
        ),
    ]


def create_debugging_templates() -> List[TaskTemplate]:
    """Create debugging task templates."""
    return [
        TaskTemplate(
            category="Debugging",
            subcategory="Off-by-One",
            prompt_template="""# Buggy code - fix the off-by-one error
def binary_search_{func_suffix}(arr: list[int], target: int) -> int:
    \"\"\"
    Binary search for target in sorted array arr.
    Returns index if found, -1 otherwise.
    \"\"\"
    left, right = 0, len(arr)
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
""",
            public_test_template="""assert binary_search_{func_suffix}([1,2,3,4,5], 3) == 2
assert binary_search_{func_suffix}([1,2,3,4,5], 6) == -1
assert binary_search_{func_suffix}([1], 1) == 0
assert binary_search_{func_suffix}([], 1) == -1
""",
            hidden_test_template="""assert binary_search_{func_suffix}([1,3,5,7,9], 1) == 0
assert binary_search_{func_suffix}([1,3,5,7,9], 9) == 4
assert binary_search_{func_suffix}([2,4,6,8], 5) == -1
# Duplicate elements
assert binary_search_{func_suffix}([1,2,2,2,3], 2) in [1,2,3]
""",
            reference_solution="""def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1""",
            buggy_solutions=[
                """def binary_search(arr, target):
    left, right = 0, len(arr)
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1""",
            ],
            default_difficulty=2,
            tags=["debugging", "off-by-one", "binary-search", "logic-bug"],
            expected_complexity="O(log n)",
            task_type=TaskType.DEBUGGING.value,
            parameters={},
        ),
        TaskTemplate(
            category="Debugging",
            subcategory="Edge Cases",
            prompt_template="""# Buggy code - fix the edge case handling
def max_subarray_sum_{func_suffix}(nums: list[int]) -> int:
    \"\"\"
    Kadane's algorithm - maximum subarray sum.
    \"\"\"
    max_sum = nums[0]
    current_sum = nums[0]
    for num in nums[1:]:
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    return max_sum
""",
            public_test_template="""assert max_subarray_sum_{func_suffix}([-2,1,-3,4,-1,2,1,-5,4]) == 6
assert max_subarray_sum_{func_suffix}([1]) == 1
assert max_subarray_sum_{func_suffix}([5,4,-1,7,8]) == 23
""",
            hidden_test_template="""assert max_subarray_sum_{func_suffix}([-1,-2,-3]) == -1
assert max_subarray_sum_{func_suffix}([-5]) == -5
assert max_subarray_sum_{func_suffix}([0,0,0]) == 0
""",
            reference_solution="""def max_subarray_sum(nums):
    if not nums:
        return 0
    max_sum = current_sum = nums[0]
    for num in nums[1:]:
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    return max_sum""",
            buggy_solutions=[
                """def max_subarray_sum(nums):
    max_sum = nums[0]
    current_sum = nums[0]
    for num in nums[1:]:
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    return max_sum  # Crashes on empty list""",
            ],
            default_difficulty=2,
            tags=["debugging", "edge-case", "kadane", "empty-input"],
            expected_complexity="O(n)",
            task_type=TaskType.DEBUGGING.value,
            parameters={},
        ),
    ]


def create_stateful_templates() -> List[TaskTemplate]:
    """Create stateful system templates."""
    return [
        TaskTemplate(
            category="Stateful Systems",
            subcategory="Cache/LRU",
            prompt_template="""class LRUCache_{func_suffix}:
    \"\"\"
    LRU Cache implementation with O(1) get and put.
    \"\"\"
    def __init__(self, capacity: int):
        pass
    def get(self, key: int) -> int:
        pass
    def put(self, key: int, value: int) -> None:
        pass
""",
            public_test_template="""cache = LRUCache_{func_suffix}(2)
cache.put(1, 1)
cache.put(2, 2)
assert cache.get(1) == 1
cache.put(3, 3)
assert cache.get(2) == -1
cache.put(4, 4)
assert cache.get(1) == -1
assert cache.get(3) == 3
assert cache.get(4) == 4
""",
            hidden_test_template="""# Single capacity
cache = LRUCache_{func_suffix}(1)
cache.put(1, 1)
assert cache.get(1) == 1
cache.put(2, 2)
assert cache.get(1) == -1
assert cache.get(2) == 2
# Update existing
cache = LRUCache_{func_suffix}(2)
cache.put(1, 1)
cache.put(1, 10)
assert cache.get(1) == 10
# Eviction order
cache = LRUCache_{func_suffix}(3)
for i in range(5):
    cache.put(i, i*10)
assert cache.get(0) == -1
assert cache.get(4) == 40
""",
            reference_solution="""class LRUCache:
    def __init__(self, capacity):
        from collections import OrderedDict
        self.cache = OrderedDict()
        self.capacity = capacity
    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)""",
            buggy_solutions=[
                """class LRUCache:
    def __init__(self, capacity):
        self.cache = {}
        self.capacity = capacity
    def get(self, key):
        return self.cache.get(key, -1)
    def put(self, key, value):
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.pop(next(iter(self.cache)))  # Not LRU!""",
            ],
            default_difficulty=4,
            tags=["stateful", "cache", "lru", "data-structure", "design"],
            expected_complexity="O(1)",
            task_type=TaskType.STATEFUL.value,
            parameters={},
        ),
    ]


def create_complexity_templates() -> List[TaskTemplate]:
    """Create complexity-constrained task templates."""
    return [
        TaskTemplate(
            category="Complexity",
            subcategory="O(n log n)",
            prompt_template="""def count_inversions_{func_suffix}(arr: list[int]) -> int:
    \"\"\"
    Count inversions in array using O(n log n) algorithm.
    An inversion is a pair (i, j) where i < j and arr[i] > arr[j].
    \"\"\"
""",
            public_test_template="""assert count_inversions_{func_suffix}([2, 4, 1, 3, 5]) == 3
assert count_inversions_{func_suffix}([5, 4, 3, 2, 1]) == 10
assert count_inversions_{func_suffix}([1, 2, 3, 4, 5]) == 0
""",
            hidden_test_template="""assert count_inversions_{func_suffix}([]) == 0
assert count_inversions_{func_suffix}([1]) == 0
assert count_inversions_{func_suffix}([1, 1, 1]) == 0
import random, time
arr = [random.randint(1, 100000) for _ in range(50000)]
start = time.time()
result = count_inversions_{func_suffix}(arr)
elapsed = time.time() - start
assert elapsed < 2.0  # Should be fast with O(n log n)
""",
            reference_solution="""def count_inversions(arr):
    def merge_sort_count(arr):
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        left, inv_left = merge_sort_count(arr[:mid])
        right, inv_right = merge_sort_count(arr[mid:])
        merged = []
        inv = inv_left + inv_right
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
                inv += len(left) - i
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged, inv
    _, count = merge_sort_count(arr)
    return count""",
            buggy_solutions=[
                """def count_inversions(arr):
    count = 0
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] > arr[j]:
                count += 1
    return count  # O(n^2) - too slow for large inputs""",
            ],
            default_difficulty=4,
            tags=["complexity", "divide-conquer", "inversions", "merge-sort"],
            expected_complexity="O(n log n)",
            task_type=TaskType.OPTIMIZATION.value,
            parameters={},
        ),
    ]


def get_all_templates() -> List[TaskTemplate]:
    """Get all built-in templates."""
    templates = []
    templates.extend(create_dp_templates())
    templates.extend(create_graph_templates())
    templates.extend(create_debugging_templates())
    templates.extend(create_stateful_templates())
    templates.extend(create_complexity_templates())
    return templates


def generate_benchmark_dataset(
    target_count: int = 500,
    version: str = "v0.2",
    encryption=None,
    category_distribution: Dict[str, int] = None
) -> List[Problem]:
    """Generate a full benchmark dataset."""
    if category_distribution is None:
        category_distribution = {
            "Fundamentals": 60,
            "Data Structures": 50,
            "Algorithms": 50,
            "Graphs": 60,
            "Trees": 40,
            "Math": 40,
            "Debugging": 50,
            "Complexity": 30,
            "Software Engineering": 40,
            "Stateful Systems": 30,
            "Multi-step": 30,
        }

    templates = get_all_templates()
    generator = TaskGenerator(encryption)
    all_problems = []

    for category, count in category_distribution.items():
        cat_templates = [t for t in templates if t.category == category]
        if not cat_templates:
            continue
        per_template = max(1, count // len(cat_templates))
        for template in cat_templates:
            problems = generator.generate_family(template, per_template)
            all_problems.extend(problems)
            if len(all_problems) >= target_count:
                break
        if len(all_problems) >= target_count:
            break

    return all_problems[:target_count]