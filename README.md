# Rockman Benchmark v0.2

> **A comprehensive, contamination-resistant benchmark for evaluating LLMs on code generation, debugging, optimization, and software engineering tasks.**

[![Benchmark Version](https://img.shields.io/badge/version-v0.2-blue)](https://github.com/InserLoft/Rockman)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Hugging Face Dataset](https://img.shields.io/badge/🤗%20Hugging%20Face-Rockman-yellow)](https://huggingface.co/datasets/Inserloft/Rockman)
[![Python](https://img.shields.io/badge/python-3.8+-blue)](https://python.org)

---

## 🎯 Overview

Rockman is a **production-ready benchmark** designed to rigorously evaluate Large Language Models on realistic software engineering tasks. Unlike simple code generation benchmarks, Rockman covers the full spectrum of developer workflows:

| Task Type | Description | Examples |
|-----------|-------------|----------|
| **Generation** | Implement function from signature + docstring | "Implement Dijkstra's algorithm" |
| **Debugging** | Fix bugs in provided code | Off-by-one, edge cases, infinite loops |
| **Optimization** | Meet specific complexity targets | O(n log n), O(1) space |
| **Stateful** | Classes with persistent state | LRU cache, banking ledger, event processor |
| **Multi-step** | Parse → Build → Solve pipelines | Parse graph → build adjacency → find path |

---

## 📊 Benchmark Composition (v0.2)

| Split | Tasks | Hidden Tests | Purpose |
|-------|-------|--------------|---------|
| **Public** | 154 | ❌ | Development, debugging |
| **Private** | 44 | ✅ (encrypted) | Official evaluation |
| **Hidden** | 22 | ✅ (never published) | Final leaderboard integrity |

| Category | Tasks | Difficulty Range |
|----------|-------|------------------|
| Fundamentals | 60 | 1–3 |
| Data Structures | 50 | 2–4 |
| Algorithms | 50 | 2–5 |
| Graphs | 60 | 3–6 |
| Trees | 40 | 3–5 |
| Math | 40 | 2–5 |
| **Debugging** | 50 | 2–4 |
| **Complexity** | 30 | 3–5 |
| **Software Engineering** | 40 | 3–5 |
| **Stateful Systems** | 30 | 4–6 |
| **Multi-step** | 30 | 4–6 |
| **Total** | **520** | **1–7** |

**Difficulty Levels:** 1=Introductory → 7=Research

---

## 🔐 Contamination Prevention

Rockman implements **six layers** of contamination protection:

| Layer | Mechanism |
|-------|-----------|
| **1. Canary Strings** | Unique `ROCKMAN_CANARY_<hash>` per task |
| **2. Content Hashing** | SHA256 of prompt + tests for integrity |
| **3. Split Isolation** | Public/Private/Hidden with zero overlap |
| **4. Encrypted Hidden Tests** | AES-256-GCM, keys held by evaluator only |
| **5. Source Attribution** | `source_type`, `source_url`, `derived_from` metadata |
| **6. Temporal Controls** | Creation/publication dates, embargo periods |

**Verification:** Run `rockman verify --dataset rockman_v0.2.jsonl` to audit integrity.

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/InserLoft/Rockman
cd Rockman
pip install -e .
pip install matplotlib  # for PNG reports
```

### Run Baseline Evaluation

```bash
# Phase 1: Reference baselines (always works offline)
python phase1_evaluate_baselines.py

# Phase 2: Model evaluation via OpenRouter
python phase2_evaluate_openrouter.py
```

### Programmatic Usage

```python
from rockman import (
    Evaluator, Problem, load_problems_from_jsonl,
    RockmanResultsReporter, generate_benchmark_dataset
)

# Load dataset
problems = load_problems_from_jsonl("rockman_v0.2_private.jsonl")

# Evaluate model
evaluator = Evaluator(benchmark_version="v0.2")
completions = {p.task_id: [your_model(p.prompt)] for p in problems}
results = evaluator.evaluate_dataset(problems, completions, k=1)

# Generate reports
reporter = RockmanResultsReporter("results")
reporter.generate_full_report(leaderboard, detailed_results)
```

---

## 📈 Evaluation Protocol

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Temperature** | 0.0 | Deterministic generation |
| **Top-p** | 1.0 | No nucleus sampling |
| **Max Tokens** | 4096 | Sufficient for complex tasks |
| **k (Pass@k)** | 1 | Single sample per task |
| **Timeout** | 2.0s | Per-task execution limit |
| **Memory** | 256 MB | Per-task memory limit |
| **Sandbox** | Containerized | Docker (or local fallback) |

### Required Metadata per Evaluation

```json
{
  "model_name": "qwen/qwen3.8-27b:free",
  "model_version": "qwen3.8-27b:free",
  "provider": "openrouter",
  "temperature": 0.0,
  "top_p": 1.0,
  "max_tokens": 4096,
  "k": 1,
  "hardware": "openrouter-cloud",
  "date": "2024-09-20T01:48:31Z",
  "evaluator_version": "0.2.0",
  "benchmark_version": "v0.2"
}
```

### API Error Handling

**Critical:** Network/API errors are **not** counted as code failures.

| Error Type | Recorded As | Counted as Failure |
|------------|-------------|-------------------|
| Code assertion failure | `FAIL` | ✅ Yes |
| Runtime error | `FAIL` | ✅ Yes |
| Timeout | `TIMEOUT` | ✅ Yes |
| **API 429 (rate limit)** | `RATE_LIMITED` | ❌ No |
| **API 402/400 (payment)** | `API_ERROR` | ❌ No |
| **API 404/500** | `API_ERROR` | ❌ No |

---

## 📊 Official Reports

Every evaluation automatically generates:

| Format | Description |
|--------|-------------|
| **`results/*.csv`** | Complete breakdown: overall, difficulty, category, task type, language, per-problem |
| **`results/*.png`** | Professional charts (black bg, white primary): leaderboard, difficulty bars, category bars, task type donut |

### Sample Leaderboard Output

```
ROCKMAN BENCHMARK v0.2
Private Evaluation — 44 Tasks

Model                    Pass@1    Solved
------------------------------------------------
Template                 13.64%     6/44
Heuristic                 0.00%     0/44
Random                    0.00%     0/44
qwen3.8-27b:free          4.55%     2/44  (41 rate limited)
Claude Sonnet 4             —       API LIMIT
GPT-4o                        ?       ?
```

---

## 🏗️ Architecture

```
rockman/
├── benchmark/           # Core evaluation engine
│   ├── schema.py        # Problem, Score, Result dataclasses
│   ├── evaluator.py     # Unified evaluator (all task types)
│   ├── metrics.py       # Pass@k, Wilson CI, statistical tests
│   ├── runners/         # Language runners (Py, C++, Java, JS, TS, Rust, Go)
│   ├── sandbox.py       # Docker sandbox + local fallback
│   ├── encryption.py    # AES-256-GCM hidden test encryption
│   ├── versioning.py    # Immutable version registry
│   └── determinism.py   # Reproducibility tracking
├── dataset/             # Dataset generation & management
│   ├── generator.py     # Template-based task generation
│   ├── categories.py    # 12 categories, 50+ subcategories
│   ├── validators.py    # 13 validation checks (incl. negative testing)
│   └── splits.py        # Public/Private/Hidden splits + canaries
├── tasks/               # Specialized task types
│   ├── debugging.py     # Bug injection (8 bug types)
│   ├── complexity.py    # Performance test generation
│   ├── stateful.py      # LRU, banking, event processor, etc.
│   └── multi_step.py    # Parse→Build→Solve pipelines
├── baselines/           # Reference baselines
│   ├── calibration.py   # Difficulty calibration
│   ├── human_baseline.py # Human evaluation framework
│   └── reference_models.py # Random, Heuristic, Template
├── reports/             # Report generation
│   └── generate.py      # Markdown/HTML/JSON reports
├── visualization/       # CSV + PNG report generation
│   └── results_reporter.py # Black-theme professional charts
├── cli/                 # CLI commands (generate, eval, leaderboard, publish)
├── docs/                # Methodology, scoring, security, contamination
│   ├── methodology.md
│   ├── scoring.md
│   ├── security.md
│   └── contamination.md
├── phase1_evaluate_baselines.py
├── phase2_evaluate_openrouter.py
├── freeze_v0.2.py
├── rockman_benchmark.py   # Backward-compatible facade
├── rockman_cli.py
└── rockman_v0.2_manifest.json
```

---

## 🔧 CLI Commands

```bash
# Generate dataset
rockman generate --count 500 --encrypt-hidden --output rockman_v0.2.jsonl

# Evaluate model
rockman evaluate --dataset rockman_v0.2_private.jsonl --completions-file model_outputs.json --k 1

# Generate leaderboard
rockman leaderboard --results-file eval_results.json

# Publish dataset
rockman publish --dataset rockman_v0.2.jsonl --public-output public.jsonl --private-output private.jsonl

# Validate dataset
rockman validate --dataset rockman_v0.2.jsonl --solutions-file refs.json
```

---

## 📦 Dataset Access

| Platform | Link | Access |
|----------|------|--------|
| **Hugging Face** | [Inserloft/Rockman](https://huggingface.co/datasets/Inserloft/Rockman) | `datasets.load_dataset("Inserloft/Rockman")` |
| **GitHub** | [InserLoft/Rockman](https://github.com/InserLoft/Rockman) | `git clone` + releases |

```python
from datasets import load_dataset
ds = load_dataset("Inserloft/Rockman", split="private")
# Note: Private split requires authentication + master secret for hidden tests
```

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

Dataset splits:
- **Public**: CC-BY-4.0
- **Private/Hidden**: Restricted (evaluation only)

---

## 🏷️ Citation

```bibtex
@misc{rockman2024,
  title={Rockman: A Comprehensive Benchmark for Code Generation and Software Engineering},
  author={Inserloft},
  year={2024},
  version={v0.2},
  url={https://github.com/InserLoft/Rockman}
}
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tasks via `rockman generate` or PR new task templates
4. Ensure all 13 validation checks pass
5. Submit PR with validation report

---

## 📞 Contact

| Platform | Link |
|----------|------|
| **Website** | [Inserloft.com](https://Inserloft.com) |
| **Benchmarks** | [Inserloft.com/benchmarks/RockMan](https://Inserloft.com/benchmarks/RockMan) |
| **GitHub** | [InserLoft/Rockman](https://github.com/InserLoft/Rockman) |
| **Hugging Face** | [Inserloft/Rockman](https://huggingface.co/datasets/Inserloft/Rockman) |
| **Email** | benchmarks@inserloft.com |

---

**Built with ❤️ by [Inserloft](https://Inserloft.com)** — Advancing the science of code intelligence evaluation.