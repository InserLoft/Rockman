# Rockman Benchmark v0.2 - Contamination Prevention

## Overview

Contamination occurs when evaluation data appears in a model's training corpus, leading to inflated performance that doesn't reflect true capability. This document describes Rockman's multi-layered contamination prevention strategy.

## Contamination Types

| Type | Description | Severity |
|------|-------------|----------|
| **Direct Memorization** | Problem text/solutions in training data | Critical |
| **Near-Duplicate** | Slightly modified variants in training | High |
| **Pattern Memorization** | Common solution templates learned | Medium |
| **Data Leakage** | Hidden tests exposed during development | Critical |

## Prevention Layers

### Layer 1: Content Hashing & Integrity

Each problem has a content hash:

```python
content_hash = SHA256(prompt + public_test + hidden_test_encrypted)[:16]
```

- Verified on load: `problem.verify_integrity()`
- Stored in manifest for audit trail
- Any modification detectable

### Layer 2: Canary Strings

Unique canary embedded in each problem:

```python
canary = "ROCKMAN_CANARY_" + SHA256(task_id + content_hash + creation_date)[:16]
```

Properties:
- **Unique per problem**: Different for every task
- **Temporal**: Includes creation date
- **Unguessable**: 128-bit entropy
- **Detectable**: Simple substring search

Detection:
```python
def check_contamination(model_output: str, canaries: Dict[str, str]) -> List[str]:
    found = []
    for task_id, canary in canaries.items():
        if canary in model_output:
            found.append(task_id)
    return found
```

### Layer 3: Dataset Splits

Three disjoint splits with no overlap:

| Split | Purpose | Public | Size |
|-------|---------|--------|------|
| **Public** | Development, debugging | Yes | 70% |
| **Private** | Evaluation server | No (encrypted) | 20% |
| **Hidden** | Final leaderboard | Never | 10% |

Verification:
```python
def verify_no_overlap(splits: Dict[str, Split]) -> List[str]:
    overlaps = []
    for name1, name2 in combinations(splits.keys(), 2):
        overlap = set(splits[name1].task_ids) & set(splits[name2].task_ids)
        if overlap:
            overlaps.append(f"{name1} ∩ {name2}: {overlap}")
    return overlaps
```

### Layer 4: Source Attribution & Metadata

Each problem tracks provenance:

```json
{
  "source_type": "original|adapted|generated|contributed",
  "source_url": "https://...",
  "source_license": "MIT|CC-BY|...",
  "derived_from": ["original_task_id"],
  "generation_method": "synthetic|human|llm|template",
  "generator_version": "v0.2",
  "creation_date": "2024-09-19T...",
  "publication_date": "2024-09-20T..."
}
```

### Layer 5: Encrypted Hidden Tests

Hidden tests encrypted with AES-256-GCM:

```python
encryption = HiddenTestEncryption(master_secret, benchmark_version)
encrypted, nonce, tag = encryption.encrypt(task_id, hidden_test_content)
```

- Key derived from: master_secret + benchmark_version + task_id
- Only evaluation server has master secret
- Public datasets contain only ciphertext

### Layer 6: Temporal Controls

- **Creation date**: When problem was authored
- **Publication date**: When added to public dataset
- **Embargo period**: Minimum 30 days before evaluation use
- **Version pinning**: Evaluation locked to specific version

## Detection Strategies

### 1. Canary Scanning

```bash
# Scan model outputs for canaries
python -m rockman.cli detect --outputs model_outputs.json --canaries canaries.json
```

### 2. N-gram Overlap

Compute n-gram similarity between:
- Problem prompts + model outputs
- Public dataset + model training data (if accessible)

Threshold: >80% 13-gram overlap = suspicious

### 3. Solution Similarity

Compare model solutions against:
- Known public solutions (GitHub, LeetCode, etc.)
- Reference implementations
- Other model outputs (collusion detection)

### 4. Statistical Anomaly Detection

Flag if:
- Pass@1 >> Pass@5 (memorized exact solutions)
- Perfect score on hidden but not public
- Unusual time-to-solve patterns

## Contamination Response

### Detection Workflow

```
1. Automated scan on every evaluation
2. Flag suspicious task_ids
3. Manual review of flagged cases
4. If confirmed:
   - Quarantine affected problems
   - Regenerate/replace problems
   - Increment benchmark version
   - Publish contamination report
```

### Quarantine Process

1. Move affected task_ids to `quarantined` split
2. Generate replacement problems (different structure, same category/difficulty)
3. Update version registry
4. Notify downstream users

### Version Management

```
v0.2.0 (original)
    ↓ contamination detected in 3 problems
v0.2.1 (quarantined 3, replaced 3)
    ↓ new evaluation
v0.2.2 (clean)
```

## Best Practices for Model Developers

### Training Data Filtering

1. **Remove canary strings**: Filter any text containing `ROCKMAN_CANARY_`
2. **Deduplicate**: Remove exact/near-duplicate problem statements
3. **Source tracking**: Tag data with provenance (LeetCode, Codeforces, etc.)
4. **Temporal holdout**: Don't train on data newer than model cutoff

### Evaluation Protocol

1. **Use private/hidden splits**: Never evaluate on public only
2. **Report split used**: "Evaluated on Rockman v0.2 private split"
3. **Multiple seeds**: Report variance across seeds
4. **No prompt engineering on test**: Fixed prompts per problem

### Reporting Requirements

When publishing results, include:
- Benchmark version (e.g., "Rockman v0.2")
- Split evaluated (public/private/hidden)
- Canary scan result: "No canaries detected"
- Contamination check date
- Training data cutoff date

## Auditing

### Internal Audit (Pre-Release)

```python
def pre_release_audit(benchmark_version: str):
    problems = load_problems(benchmark_version)
    
    # 1. Verify no canary in public artifacts
    public_text = get_public_documentation()
    for p in problems:
        assert p.canary not in public_text
    
    # 2. Verify split integrity
    splits = load_splits(benchmark_version)
    assert verify_no_overlap(splits) == []
    
    # 3. Verify hidden tests encrypted
    for p in problems:
        if p.hidden_test_encrypted:
            assert p.hidden_test_nonce and p.hidden_test_tag
    
    # 4. Verify content hashes
    for p in problems:
        assert p.verify_integrity()
    
    # 5. Scan for known contamination sources
    known_sources = load_known_sources()
    for p in problems:
        assert not is_contaminated(p, known_sources)
```

### External Audit

Third-party auditors can:
1. Verify split integrity independently
2. Scan model outputs for canaries
3. Validate encryption implementation
4. Review generation methodology

## Tooling

### CLI Commands

```bash
# Generate canaries
rockman generate-canaries --dataset rockman_v0.2.jsonl --output canaries.json

# Scan for contamination
rockman detect-contamination --outputs model_outputs.json --canaries canaries.json

# Verify dataset integrity
rockman verify --dataset rockman_v0.2.jsonl --version v0.2

# Create splits
rockman split --dataset rockman_v0.2.jsonl --output-dir splits/
```

### CI Integration

```yaml
# .github/workflows/contamination.yml
on: [push, schedule]
jobs:
  contamination-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check canaries in repo
        run: |
          if grep -r "ROCKMAN_CANARY_" .; then
            echo "CANARY FOUND IN REPO!"
            exit 1
          fi
      - name: Verify dataset integrity
        run: python -m rockman.cli verify --dataset data/rockman_v0.2.jsonl
```

## References

- Carlini et al., "Extracting Training Data from Large Language Models" (2021)
- Brown et al., "Language Models are Few-Shot Learners" (GPT-3, 2020)
- Chen et al., "Evaluating Large Language Models Trained on Code" (HumanEval, 2021)
- OpenAI, "Grade School Math" dataset contamination analysis
- BigCode, "The Stack" data contamination prevention

## Checklist for Release

- [ ] All problems have unique canaries
- [ ] Content hashes computed and stored
- [ ] Splits verified disjoint (public/private/hidden)
- [ ] Hidden tests encrypted with fresh master secret
- [ ] Source metadata complete for all problems
- [ ] Canary scan on all public artifacts passes
- [ ] Contamination scan against known sources passes
- [ ] Version registry updated with integrity hashes
- [ ] Embargo period respected for new problems
- [ ] Documentation includes contamination check date