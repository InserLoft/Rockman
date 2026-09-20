# Rockman Benchmark v0.2 - Scoring Methodology

## Overview

This document provides complete technical details on how Rockman scores are calculated, including Pass@k, category breakdowns, efficiency/robustness scores, confidence intervals, and statistical significance testing.

## Pass@k Metric

### Definition

Pass@k measures the probability that at least one of k sampled solutions is correct, given n total samples with c correct.

### Formula

$$\text{Pass@k}(n, c, k) = \begin{cases} 
1.0 & \text{if } n - c < k \\
1 - \frac{\binom{n-c}{k}}{\binom{n}{k}} & \text{otherwise}
\end{cases}$$

### Implementation

```python
def estimate_pass_at_k(n: int, c: int, k: int) -> float:
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)
```

### Properties

- **Pass@1** = c/n (simple accuracy)
- **Pass@k** ≥ **Pass@1** for k > 1
- As k → n, Pass@k → 1 if c > 0
- Requires n ≥ k for meaningful results

### Per-Problem vs Aggregate

**Per-Problem**: Each problem evaluated with n samples → Pass@k per problem
**Aggregate**: Mean of per-problem Pass@k values

$$\text{Overall} = \frac{1}{N}\sum_{i=1}^N \text{Pass@k}_i$$

## Category-Level Scoring

### Weighted Mean Pass@k

For each category C:

$$\text{Score}_C = \frac{1}{|C|}\sum_{p \in C} \text{Pass@k}_p$$

This ensures each problem contributes equally regardless of sample count.

### Subcategory Scoring

Same formula applied at subcategory level for finer granularity.

## Specialized Scores

### Efficiency Score

Measures ability to produce asymptotically optimal solutions.

$$\text{Efficiency} = \frac{1}{|E|}\sum_{p \in E} \text{Pass@1}_p$$

Where E = {problems tagged with "complexity" or "efficiency"}

Includes problems requiring:
- O(1), O(log n), O(n), O(n log n) algorithms
- Explicit complexity constraints
- Performance tests that fail slow solutions

### Robustness Score

Measures handling of edge cases and boundary conditions.

$$\text{Robustness} = \frac{1}{|R|}\sum_{p \in R} \text{Pass@1}_p$$

Where R = {problems tagged with "edge-case" or "robustness"}

Includes problems testing:
- Empty inputs, single elements
- Duplicates, negative values
- Very large inputs, overflow
- Unicode, cycles, disconnected graphs

## Difficulty Scoring

### Difficulty-Level Pass Rate

$$\text{Difficulty}_d = \frac{1}{|D_d|}\sum_{p \in D_d} \text{Pass@1}_p$$

Where $D_d$ = problems at difficulty level d.

### Calibration Validation

A well-calibrated benchmark should show:
- **Monotonicity**: Score(d) ≥ Score(d+1) for all d
- **Separation**: Score(1) - Score(7) ≥ 0.5 (50% gap)
- **Statistical separation**: Non-overlapping confidence intervals between adjacent levels

### Expected Score Ranges (Human Calibrated)

| Difficulty | Expected Range | Notes |
|------------|----------------|-------|
| 1 (Intro) | 90-100% | Near-ceiling for competent models |
| 2 (Easy) | 75-95% | Standard algorithms |
| 3 (Intermediate) | 60-85% | Multi-step reasoning |
| 4 (Advanced) | 40-70% | Optimization required |
| 5 (Hard) | 20-50% | Novel algorithm design |
| 6 (Expert) | 5-30% | Research-level |
| 7 (Research) | 0-15% | Open/unsolved variants |

## Confidence Intervals

### Wilson Score Interval

For binomial proportion with n trials, c successes, 95% CI:

$$\hat{p} = \frac{c + z^2/2}{n + z^2}$$
$$\text{margin} = \frac{z}{n + z^2}\sqrt{\frac{c(n-c)}{n} + \frac{z^2}{4}}$$
$$\text{CI} = [\hat{p} - \text{margin}, \hat{p} + \text{margin}]$$

Where $z = 1.96$ for 95% confidence.

### Implementation

```python
def calculate_confidence_interval(passed: int, total: int, confidence: float = 0.95):
    if total == 0:
        return (0.0, 0.0)
    z = 1.96 if confidence == 0.95 else 2.576
    p = passed / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return (max(0, centre - half) * 100, min(1, centre + half) * 100)
```

### Reporting

- Overall score: CI based on (passed_tasks, total_tasks)
- Per-category: CI based on samples in that category
- Per-difficulty: CI based on samples at that level

## Statistical Significance

### Two-Proportion Z-Test

Comparing model A (n₁, c₁) vs model B (n₂, c₂):

$$p_1 = c_1/n_1, \quad p_2 = c_2/n_2$$
$$p_{pool} = (c_1 + c_2)/(n_1 + n_2)$$
$$SE = \sqrt{p_{pool}(1-p_{pool})(1/n_1 + 1/n_2)}$$
$$z = (p_1 - p_2) / SE$$
$$p\text{-value} = 2(1 - \Phi(|z|))$$

Significant if p < 0.05.

### Implementation

```python
def statistical_significance(score1, score2):
    n1, c1 = score1.total_tasks, score1.passed_tasks
    n2, c2 = score2.total_tasks, score2.passed_tasks
    p1, p2 = c1/n1, c2/n2
    p_pool = (c1 + c2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    z = (p1 - p2) / se if se > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "significant": p_value < 0.05,
        "p_value": p_value,
        "z_score": z,
        "diff": (p1 - p2) * 100
    }
```

### Multiple Comparison Correction

When comparing k models against a baseline, apply Bonferroni correction:
- Adjusted α = 0.05 / k
- Or use Benjamini-Hochberg FDR control

## Leaderboard Scoring

### Composite Score

Overall leaderboard rank by Overall Score (mean Pass@1).

### Tie-Breaking

1. Higher Overall Score
2. Higher Advanced+ Score (difficulty ≥ 4)
3. Higher Efficiency Score
4. Higher Robustness Score
5. More problems attempted

### Required Metadata

Each leaderboard entry must include:
- Model name & version
- Temperature, max_tokens, num_attempts
- Hardware specification
- Evaluation date
- Benchmark version
- Confidence intervals

## Human Baseline Scoring

### Participant Scoring

Individual human: fraction of problems solved within time limit.

### Group Aggregation

Mean of individual pass rates (not pooled attempts):

$$\text{Human Score} = \frac{1}{N}\sum_{i=1}^N \text{pass\_rate}_i$$

### Experience-Level Breakdown

Report pass rates by:
- Novice (<1 yr)
- Junior (1-3 yr)
- Mid (3-7 yr)
- Senior (7-15 yr)
- Expert (15+ yr)
- Competitive (CP background)

## Reporting Standards

### Required Report Sections

1. **Executive Summary**: Overall score, key metrics
2. **Difficulty Breakdown**: Table with 95% CIs
3. **Category Breakdown**: All 12 categories
4. **Task Type Breakdown**: 10 types
5. **Language Breakdown**: If multi-language
6. **Efficiency/Robustness**: Specialized scores
7. **Calibration Results**: Reference model comparison
8. **Human Baseline**: If available
9. **Statistical Significance**: Model comparisons
10. **Reproducibility**: Environment, seeds, manifest

### Visualization Recommendations

- Bar charts with error bars (95% CI)
- Difficulty progression line chart
- Category heatmap
- Model comparison grouped bar chart
- Pass@k curve (k=1,5,10,20,50)