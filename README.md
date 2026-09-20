# Rockman Benchmark v0.2

> A contamination-resistant benchmark for evaluating LLMs on code generation, debugging, optimization, and software engineering tasks.

Rockman is an evaluation benchmark designed to measure how reliably language models solve executable software-engineering problems.

Unlike benchmarks focused only on code completion, Rockman evaluates multiple classes of programming tasks, including generation, debugging, algorithms, data structures, complexity constraints, stateful systems, and multi-step problems.

---

## 🎯 Overview

Rockman evaluates models using executable tests rather than relying on textual similarity or human judgment.

### Task types

| Task Type    | Description                                  | Examples                                    |
| ------------ | -------------------------------------------- | ------------------------------------------- |
| Generation   | Implement functionality from a specification | Algorithms, utilities, data structures      |
| Debugging    | Repair defective code                        | Edge cases, incorrect logic, runtime errors |
| Optimization | Satisfy computational constraints            | Time or memory complexity                   |
| Stateful     | Maintain persistent state across operations  | Caches, ledgers, processors                 |
| Multi-step   | Solve a sequence of dependent operations     | Parse → Build → Solve                       |

---

## 📊 Benchmark Composition

Rockman v0.2 contains **220 evaluation tasks** distributed across three evaluation splits.

| Split   | Tasks | Hidden Tests | Purpose                               |
| ------- | ----: | ------------ | ------------------------------------- |
| Public  |   154 | No           | Development and local experimentation |
| Private |    44 | Yes          | Official model evaluation             |
| Hidden  |    22 | Yes          | Additional leaderboard integrity      |

**Total: 220 tasks**

The **44-task private split** is the primary official evaluation set for v0.2.

The hidden split is not published and is reserved for controlled evaluation.

### Difficulty

Rockman tasks are assigned difficulty levels from **1 to 7**:

| Level | Description    |
| ----: | -------------- |
|     1 | Introductory   |
|     2 | Basic          |
|     3 | Intermediate   |
|     4 | Advanced       |
|     5 | Hard           |
|     6 | Very Hard      |
|     7 | Research-level |

Difficulty is intended to describe task complexity, not model performance.

---

## 🔐 Contamination Resistance

Rockman v0.2 incorporates multiple mechanisms intended to reduce benchmark contamination and preserve evaluation integrity.

| Layer | Mechanism                                  |
| ----- | ------------------------------------------ |
| 1     | Canary strings                             |
| 2     | SHA-256 task/content hashing               |
| 3     | Public / Private / Hidden split isolation  |
| 4     | AES-256-GCM encrypted hidden tests         |
| 5     | Source attribution metadata                |
| 6     | Temporal metadata and publication controls |

### Canary strings

Tasks may contain unique identifiers following the form:

```text
ROCKMAN_CANARY_<hash>
```

These canaries can be used to detect unexpected exposure or contamination.

### Hidden tests

Private and hidden evaluation relies on tests that are not exposed as part of the public benchmark interface.

The hidden evaluation material is encrypted and intended to remain under evaluator control.

---

## 🚀 Quick Start

### Clone

```bash
git clone https://github.com/InserLoft/Rockman
cd Rockman
```

### Install

```bash
pip install -e .
```

Optional dependencies for report generation:

```bash
pip install matplotlib
```

---

## 🧪 Evaluation

Rockman evaluates model-generated completions against executable tests.

A typical evaluation uses:

```text
Temperature: 0.0
Top-p: 1.0
Max tokens: 4096
Pass@k: 1
Timeout: 2 seconds
Memory limit: 256 MB
```

### Official evaluation split

The primary official v0.2 evaluation consists of:

```text
44 private tasks
```

Each task produces an executable result.

Typical outcomes include:

```text
PASS
FAIL
TIMEOUT
RATE_LIMITED
API_ERROR
```

API and network failures are separated from actual code failures.

| Result                   | Counted as code failure? |
| ------------------------ | ------------------------ |
| PASS                     | No                       |
| Assertion / test failure | Yes                      |
| Runtime error            | Yes                      |
| Timeout                  | Yes                      |
| API rate limit           | No                       |
| API/payment error        | No                       |
| Server/API error         | No                       |

This distinction prevents external provider failures from being incorrectly interpreted as model failures.

---

## 📈 Metrics

Rockman reports model performance using executable task results.

### Pass@1

For the official v0.2 evaluation:

```text
Pass@1 = solved tasks / evaluated tasks
```

The benchmark also supports additional statistical reporting, including:

* Difficulty breakdowns
* Category breakdowns
* Task-type breakdowns
* Per-task results
* Wilson confidence intervals
* Statistical comparisons

---

## 📊 v0.2 Baselines

Reference baselines have been evaluated on the 44-task private split.

| Baseline  | Pass@1 | Solved |
| --------- | -----: | -----: |
| Template  | 13.64% | 6 / 44 |
| Heuristic |  0.00% | 0 / 44 |
| Random    |  0.00% | 0 / 44 |

These baselines are provided as reference points and are not intended to represent modern LLM performance.

---

## 🏗️ Repository Structure

```text
Rockman/
├── demo_splits/
├── rockman/
├── rockman_v0.2_splits/
│
├── rockman_v0.2_public.jsonl
├── rockman_v0.2_private.jsonl
├── rockman_v0.2_hidden.jsonl
│
├── rockman_v0.2_manifest.json
├── rockman_v0.2_task_hashes.json
├── rockman_v0.2_canaries.json
│
├── rockman_v0.2_leaderboard.json
├── rockman_v0.2_leaderboard_baselines.json
├── human_baseline_results.json
│
├── rockman_benchmark.py
├── rockman_cli.py
├── rockman_versions.json
└── README.md
```

The `rockman/` package contains the benchmark implementation and evaluation infrastructure.

---

## 📦 Dataset

Rockman is available through Hugging Face for dataset access and through GitHub for the benchmark implementation and release artifacts.

**Hugging Face**

```python
from datasets import load_dataset

dataset = load_dataset("Inserloft/Rockman")
```

The availability of individual splits depends on their release status and access controls.

The private and hidden evaluation material is intentionally not equivalent to the public development split.

---

## 📜 License

The Rockman benchmark software is released under the **MIT License**.

See [`LICENSE`](LICENSE) for the complete license text.

Dataset licensing and evaluation access may differ by split.

---

## 🏷️ Citation

```bibtex
@misc{rockman2026,
  title={Rockman: A Contamination-Resistant Benchmark for Code Generation and Software Engineering},
  author={Inserloft},
  year={2026},
  version={v0.2},
  url={https://github.com/InserLoft/Rockman}
}
```

---

## 🤝 Contributing

Contributions to the benchmark infrastructure and public evaluation tasks are welcome.

When contributing:

1. Fork the repository.
2. Create a feature branch.
3. Add or modify public benchmark components.
4. Run the available validation checks.
5. Document changes affecting evaluation methodology.
6. Submit a pull request.

Private and hidden evaluation material must not be exposed through contributions.

---

## 🔗 Links

* **GitHub:** https://github.com/InserLoft/Rockman
* **Hugging Face:** https://huggingface.co/datasets/Inserloft/Rockman
* **Inserloft:** https://inserloft.com

---

## About Rockman

Rockman is developed by **Inserloft** as part of its work on AI evaluation and software-engineering benchmarks.

**Rockman v0.2**
