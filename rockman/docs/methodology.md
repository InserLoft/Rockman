# Rockman Benchmark v0.2 - Methodology

## Overview

Rockman is a comprehensive benchmark for evaluating Large Language Models (LLMs) on code generation, debugging, optimization, and software engineering tasks. This document describes the methodology, design principles, and evaluation protocols.

## Design Principles

### 1. **Realistic Software Engineering Tasks**
Beyond simple function generation, Rockman evaluates:
- **Debugging**: Fixing bugs in existing code (logic bugs, off-by-one, edge cases, etc.)
- **Optimization**: Achieving specific complexity targets (O(n log n), O(1), etc.)
- **Stateful Systems**: Classes with persistent state (caches, ledgers, schedulers)
- **Multi-step Reasoning**: Parse → Build → Solve pipelines
- **Software Engineering**: Refactoring, API implementation, parser design

### 2. **Hidden Tests & Contamination Prevention**
- **Public tests**: Visible to models during evaluation
- **Private tests**: Encrypted, only decrypted on evaluation server
- **Hidden tests**: Never published, used for final leaderboard
- **Canary strings**: Unique identifiers embedded in each problem to detect training data contamination
- **Content hashing**: SHA256 hashes verify problem integrity

### 3. **Multi-Language Evaluation**
Problems can be evaluated in Python, C++, Java, JavaScript, TypeScript, Rust, and Go.
Language-specific runners with consistent resource limits.

### 4. **Difficulty Calibration**
- 7 difficulty levels (1=Introductory → 7=Research)
- Calibrated using reference models and human baselines
- Empirically validated separation between levels

## Problem Schema

Each problem contains:

```json
{
  "task_id": "Rockman/DP_041",
  "category": "Dynamic Programming",
  "subcategory": "Knapsack",
  "difficulty": 4,
  "prompt": "def knapsack(...) -> int:\n    \"\"\"...\"\"\"",
  "public_test": "assert knapsack(...) == ...",
  "hidden_test_encrypted": "...",
  "time_limit": 2.0,
  "memory_limit": 256,
  "language": "python",
  "tags": ["dp", "optimization", "knapsack"],
  "source_type": "original",
  "expected_complexity": "O(nW)",
  "deterministic": true,
  "task_type": "generation",
  "version": "v0.2",
  "creation_date": "2024-09-19T...",
  "content_hash": "abc123...",
  "canary": "ROCKMAN_CANARY_..."
}
```

## Task Types

| Type | Description | Evaluation |
|------|-------------|------------|
| `generation` | Implement function from signature | Standard I/O tests |
| `debugging` | Fix bug in provided code | Standard I/O tests |
| `completion` | Complete partial implementation | Standard I/O tests |
| `refactoring` | Improve code quality | Tests + style checks |
| `optimization` | Meet complexity target | Tests + performance tests |
| `api_implementation` | Implement interface/class | Integration tests |
| `parsing` | Parse structured input | I/O + validation |
| `file_io` | Read/write files | Temporary filesystem |
| `stateful` | Class with persistent state | Sequential operations |
| `multi_step` | Multi-phase problem | Step-wise validation |

## Categories (12 Main Categories)

1. **Fundamentals**: Arrays, Strings, Hash Tables, Sorting, Searching, Two Pointers, Sliding Window, Prefix Sum, Difference Array, Binary Search
2. **Data Structures**: Stack, Queue, Deque, Linked List, Heap, Hash Map, Union-Find, Segment Tree, Fenwick Tree, Trie, Sparse Table, Monotonic Stack/Queue
3. **Algorithms**: Greedy, Divide & Conquer, Backtracking, Recursion, DP, Bit Manipulation, Randomized, Computational Geometry
4. **Graphs**: BFS, DFS, Shortest Path, Dijkstra, Bellman-Ford, Floyd-Warshall, MST, Kruskal, Prim, Topological Sort, SCC, Bipartite, Flow, Matching, Eulerian, Hamiltonian
5. **Trees**: Binary Trees, BST, AVL, Tree DP, LCA, Traversal, Subtree Queries, Heavy-Light
6. **Math**: Number Theory, Primes, GCD/LCM, Modular Arithmetic, Combinatorics, Probability, Matrix Ops, Linear Algebra, Numerical Methods, Geometry
7. **Debugging**: Logic Bugs, Off-by-One, Edge Cases, Type Errors, State Mutation, Infinite Loops, Complexity Bugs, Recursion Bugs
8. **Complexity**: O(1), O(log n), O(n), O(n log n), O(n²), Space Complexity
9. **Software Engineering**: Class Design, Inheritance, Refactoring, Feature Addition, Backwards Compatibility, Exception Handling, Parser, Interface, Regression Fix, Performance
10. **Stateful Systems**: Cache/LRU, Banking Ledger, Event Processor, Task Scheduler, Game State, Inventory, Session Manager, Transaction System
11. **Multi-step**: Parse→Build→Solve, Multi-phase Algorithm, Pipeline Processing

## Difficulty Levels

| Level | Label | Description |
|-------|-------|-------------|
| 1 | Introductory | Basic syntax, simple loops/conditionals |
| 2 | Easy | Standard algorithms, direct application |
| 3 | Intermediate | Algorithm combination, moderate reasoning |
| 4 | Advanced | Complex algorithms, optimization required |
| 5 | Hard | Novel algorithm design, heavy optimization |
| 6 | Expert | Research-level, unsolved variants |
| 7 | Research | Open problems, novel contributions |

## Evaluation Protocol

### Pass@k Metric

For each problem, we generate `n` samples from the model and count `c` correct solutions:

$$\text{Pass@k} = 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}$$

If $n - c < k$, Pass@k = 1.0.

**Overall Score**: Mean Pass@1 across all problems.

### Efficiency Score

Pass rate on problems tagged with `complexity` or `efficiency`, measuring ability to produce asymptotically optimal solutions.

### Robustness Score

Pass rate on problems tagged with `edge-case` or `robustness`, measuring handling of boundary conditions.

### Statistical Rigor

- **Confidence Intervals**: Wilson score interval (95%) for binomial proportions
- **Significance Testing**: Two-proportion z-test for model comparisons
- **Minimum Samples**: At least 10 samples per problem for reliable Pass@k

## Execution Environment

### Sandbox Security

Code execution uses containerized sandbox:
- No network access
- Read-only root filesystem
- CPU/memory limits enforced via cgroups
- Process limits (pids_limit)
- Temporary filesystem with size limits
- Non-root user execution

### Determinism

- Fixed random seeds for reproducible execution
- Multiple runs (default 3) to verify determinism
- Environment capture: OS, compiler versions, hardware, environment variables
- Reproducibility manifest generated for each evaluation

### Resource Limits

| Limit | Default | Configurable |
|-------|---------|--------------|
| Time | 2.0s | Per-problem |
| Memory | 256 MB | Per-problem |
| CPU | 1 core | Global |
| Processes | 64 | Global |

## Quality Assurance

### Validation Pipeline

Each problem passes 13 validation checks:
1. Valid prompt with signature and docstring
2. Parsable test cases
3. Reference solution passes
4. Tests detect known buggy solutions (negative testing)
5. No ambiguous language
6. Difficulty consistent with category
7. Runtime within 50% of limit
8. Memory within 50% of limit
9. Deterministic execution
10. Appropriate tags
11. Hidden tests exist
12. Complexity notation valid
13. No contamination detected

### Version Management

- **Immutable versions**: Published versions never modified
- **Version registry**: Tracks all versions with task IDs and hashes
- **Integrity verification**: SHA256 hashes for each version

## Contamination Prevention

1. **Canary Strings**: Each problem has unique `ROCKMAN_CANARY_<hash>` embedded
2. **Source Attribution**: `source_type` (original/adapted/generated/contributed) + `source_url`
3. **Derivation Tracking**: `derived_from` lists original problem IDs
4. **Generation Metadata**: `generation_method`, `generator_version`
5. **Content Hashing**: SHA256 of prompt+tests for integrity verification
6. **Split Management**: Public/Private/Hidden with no overlap

## Reporting

### Standard Metrics Reported

- Overall Pass@1
- Per-difficulty breakdown (1-7)
- Per-category breakdown (12 categories)
- Per-task-type breakdown (10 types)
- Per-language breakdown
- Efficiency score
- Robustness score
- 95% Confidence intervals

### Leaderboard Format

| Model | Version | Temp | Tokens | Attempts | Hardware | Date | Overall | DP | Graphs | Debug | Adv |
|-------|---------|------|--------|----------|----------|------|---------|-----|--------|-------|-----|

### Human Baselines

Human evaluation with documented participants:
- Experience level (novice → competitive)
- Domain background
- Years of experience
- Competitive programming rating
- Time-to-solve statistics

## References

- Chen et al., "Evaluating Large Language Models Trained on Code" (HumanEval)
- Austin et al., "Program Synthesis with Large Language Models" (MBPP)
- Li et al., "Competition-Level Code Generation with AlphaCode"