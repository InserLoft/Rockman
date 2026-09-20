"""CLI commands for Rockman benchmark"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
import argparse

from rockman.benchmark.schema import Problem, TaskType, Language
from rockman.benchmark.evaluator import Evaluator
from rockman.benchmark.metrics import (
    aggregate_scores,
    BenchmarkReport,
    print_leaderboard_header,
    format_leaderboard_row,
)
from rockman.benchmark.versioning import VersionRegistry, CURRENT_VERSION
from rockman.dataset.generator import generate_benchmark_dataset, get_all_templates
from rockman.dataset.validators import validate_dataset, generate_validation_report
from rockman.dataset.splits import SplitManager, create_canary_strings
from rockman.benchmark.encryption import HiddenTestEncryption, generate_master_secret


def load_problems_from_jsonl(filepath: str, include_hidden: bool = False) -> List[Problem]:
    """Load problems from JSONL file."""
    problems = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if not include_hidden:
                data.pop("hidden_test_encrypted", None)
                data.pop("hidden_test_nonce", None)
                data.pop("hidden_test_tag", None)
            problems.append(Problem.from_dict(data))
    return problems


def save_problems_to_jsonl(problems: List[Problem], filepath: str, include_hidden: bool = False):
    """Save problems to JSONL file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for problem in problems:
            f.write(problem.to_jsonl(include_hidden=include_hidden) + "\n")


def cmd_generate(args):
    """Generate benchmark dataset."""
    print(f"Generating Rockman benchmark dataset {args.version}...")

    encryption = None
    if args.encrypt_hidden:
        master_secret = os.environ.get("ROCKMAN_MASTER_SECRET") or generate_master_secret()
        if not os.environ.get("ROCKMAN_MASTER_SECRET"):
            print(f"Generated master secret (save this!): {master_secret}")
            print("Set ROCKMAN_MASTER_SECRET environment variable to use it.")
        encryption = HiddenTestEncryption(master_secret, args.version)

    problems = generate_benchmark_dataset(
        target_count=args.count,
        version=args.version,
        encryption=encryption,
    )

    output_path = args.output or f"rockman_dataset_{args.count}.jsonl"
    # Always include hidden tests when encrypting, otherwise use flag
    include_hidden = args.include_hidden or args.encrypt_hidden
    save_problems_to_jsonl(problems, output_path, include_hidden=include_hidden)
    print(f"Generated {len(problems)} problems -> {output_path}")

    if args.validate:
        print("\nValidating dataset...")
        results = validate_dataset(problems)
        report = generate_validation_report(results)
        print(report)

    if args.create_splits:
        print("\nCreating standard splits...")
        split_manager = SplitManager()
        splits = split_manager.create_standard_splits(problems, args.version)
        for name, split in splits.items():
            print(f"  {name}: {len(split.task_ids)} tasks")


def cmd_evaluate(args):
    """Evaluate model outputs against benchmark."""
    print(f"Loading dataset from {args.dataset}...")
    problems = load_problems_from_jsonl(args.dataset, include_hidden=args.include_hidden)

    if args.problem_ids:
        problem_ids = set(args.problem_ids.split(","))
        problems = [p for p in problems if p.task_id in problem_ids]

    print(f"Evaluating {len(problems)} problems...")

    # Load model completions
    completions = {}
    if args.completions_file:
        with open(args.completions_file) as f:
            completions = json.load(f)
    else:
        print("No completions file provided. Use --completions-file.")
        return

    evaluator = Evaluator(benchmark_version=args.version)
    results = evaluator.evaluate_dataset(
        problems,
        completions,
        include_hidden=args.include_hidden,
        k=args.k,
    )

    print(f"\nMean Pass@{args.k}: {results['mean_pass_at_k']:.4f}")
    print(f"Evaluated: {results['evaluated_count']}/{len(problems)}")

    if args.detailed:
        for task_id, task_results in results["results"].items():
            passed = sum(1 for r in task_results if r.passed)
            total = len(task_results)
            print(f"  {task_id}: {passed}/{total} passed")


def cmd_leaderboard(args):
    """Generate leaderboard from evaluation results."""
    print_leaderboard_header()

    # Load evaluation results
    with open(args.results_file) as f:
        eval_results = json.load(f)

    for model_name, result in eval_results.items():
        score = BenchmarkReport(**result).score
        row = format_leaderboard_row(
            model_name=model_name,
            model_version=result.get("model_version", "unknown"),
            score=score,
            temperature=result.get("temperature", 0.2),
            max_tokens=result.get("max_tokens", 4096),
            attempts=result.get("num_attempts", 1),
            hardware=result.get("hardware", "unknown"),
            date=result.get("date", ""),
        )
        print(row)


def cmd_publish(args):
    """Prepare dataset for publication."""
    print(f"Preparing publication from {args.dataset}...")

    problems = load_problems_from_jsonl(args.dataset, include_hidden=True)

    # Create splits if needed
    split_manager = SplitManager(args.splits_dir)
    if "public" not in split_manager.splits:
        print("Creating standard splits...")
        split_manager.create_standard_splits(problems, args.version)

    # Export public dataset (no hidden tests)
    if args.public_output:
        split_manager.export_public_dataset(
            problems, args.public_output, "public", include_hidden=False
        )
        print(f"Public dataset -> {args.public_output}")

    # Export private dataset (with encrypted hidden tests)
    if args.private_output:
        master_secret = os.environ.get("ROCKMAN_MASTER_SECRET")
        if not master_secret:
            print("ERROR: ROCKMAN_MASTER_SECRET required for private dataset")
            return
        split_manager.export_private_dataset(
            problems, args.private_output, "private", master_secret
        )
        print(f"Private dataset -> {args.private_output}")

    # Export hidden dataset (never published)
    if args.hidden_output:
        split_manager.export_hidden_dataset(
            problems, args.hidden_output, "hidden"
        )
        print(f"Hidden dataset -> {args.hidden_output}")

    # Generate canary strings
    if args.canary_output:
        canaries = create_canary_strings(problems)
        with open(args.canary_output, "w") as f:
            json.dump(canaries, f, indent=2)
        print(f"Canary strings -> {args.canary_output}")

    # Verify no overlap
    overlaps = split_manager.verify_no_overlap()
    if overlaps:
        print("WARNING: Split overlaps detected:")
        for o in overlaps:
            print(f"  {o}")
    else:
        print("Split integrity: OK - no overlaps")

    # Compute hashes
    hashes = split_manager.compute_split_hashes(problems)
    print("Split hashes:")
    for name, h in hashes.items():
        print(f"  {name}: {h}")


def cmd_validate(args):
    """Validate dataset quality."""
    print(f"Validating {args.dataset}...")
    problems = load_problems_from_jsonl(args.dataset, include_hidden=True)

    if args.problem_ids:
        problem_ids = set(args.problem_ids.split(","))
        problems = [p for p in problems if p.task_id in problem_ids]

    print(f"Validating {len(problems)} problems...")

    solutions = {}
    if args.solutions_file:
        with open(args.solutions_file) as f:
            solutions = json.load(f)

    buggy = {}
    if args.buggy_file:
        with open(args.buggy_file) as f:
            buggy = json.load(f)

    results = validate_dataset(problems, solutions, buggy)
    report = generate_validation_report(results)
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            json.dump({k: v.__dict__ for k, v in results.items()}, f, indent=2)


def cmd_encrypt(args):
    """Encrypt hidden tests in dataset."""
    master_secret = os.environ.get("ROCKMAN_MASTER_SECRET")
    if not master_secret:
        print("ERROR: ROCKMAN_MASTER_SECRET environment variable required")
        return

    encryption = HiddenTestEncryption(master_secret, args.version)

    problems = load_problems_from_jsonl(args.input, include_hidden=True)
    for problem in problems:
        if problem.metadata.get("_hidden_test_raw"):
            problem = encryption.encrypt_problem_hidden_tests(problem)

    save_problems_to_jsonl(problems, args.output, include_hidden=True)
    print(f"Encrypted {len(problems)} problems -> {args.output}")


def cmd_decrypt(args):
    """Decrypt hidden tests (for evaluation server)."""
    master_secret = os.environ.get("ROCKMAN_MASTER_SECRET")
    if not master_secret:
        print("ERROR: ROCKMAN_MASTER_SECRET environment variable required")
        return

    encryption = HiddenTestEncryption(master_secret, args.version)

    problems = load_problems_from_jsonl(args.input, include_hidden=True)
    for problem in problems:
        if problem.hidden_test_encrypted:
            hidden = encryption.decrypt_problem_hidden_tests(problem)
            print(f"{problem.task_id}:")
            print(hidden)
            print("---")


def cmd_version(args):
    """Manage benchmark versions."""
    registry = VersionRegistry()

    if args.list:
        for v in registry.list_versions():
            print(f"{v.version}: {v.task_count} tasks - {v.description}")
    elif args.register:
        task_ids = args.task_ids.split(",") if args.task_ids else []
        registry.register(args.register, task_ids, args.description, args.parent)
        print(f"Registered version {args.register}")
    elif args.verify:
        problems = load_problems_from_jsonl(args.dataset)
        task_ids = {p.task_id for p in problems}
        if registry.verify_integrity(args.verify, task_ids):
            print(f"Version {args.verify} integrity: OK")
        else:
            print(f"Version {args.verify} integrity: FAILED")
    else:
        print("Use --list, --register, or --verify")


def main():
    parser = argparse.ArgumentParser(prog="rockman", description="Rockman Benchmark CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate benchmark dataset")
    gen_parser.add_argument("--count", type=int, default=500, help="Number of problems to generate")
    gen_parser.add_argument("--version", default=CURRENT_VERSION, help="Benchmark version")
    gen_parser.add_argument("--output", help="Output JSONL file")
    gen_parser.add_argument("--encrypt-hidden", action="store_true", help="Encrypt hidden tests")
    gen_parser.add_argument("--include-hidden", action="store_true", help="Include hidden tests in output")
    gen_parser.add_argument("--validate", action="store_true", help="Validate after generation")
    gen_parser.add_argument("--create-splits", action="store_true", help="Create public/private/hidden splits")
    gen_parser.set_defaults(func=cmd_generate)

    # evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate model completions")
    eval_parser.add_argument("--dataset", required=True, help="Dataset JSONL file")
    eval_parser.add_argument("--completions-file", required=True, help="Model completions JSON file")
    eval_parser.add_argument("--version", default=CURRENT_VERSION, help="Benchmark version")
    eval_parser.add_argument("--k", type=int, default=1, help="Pass@k value")
    eval_parser.add_argument("--include-hidden", action="store_true", help="Include hidden tests")
    eval_parser.add_argument("--problem-ids", help="Comma-separated problem IDs to evaluate")
    eval_parser.add_argument("--detailed", action="store_true", help="Show per-problem results")
    eval_parser.set_defaults(func=cmd_evaluate)

    # leaderboard
    lb_parser = subparsers.add_parser("leaderboard", help="Generate leaderboard")
    lb_parser.add_argument("--results-file", required=True, help="Evaluation results JSON file")
    lb_parser.set_defaults(func=cmd_leaderboard)

    # publish
    pub_parser = subparsers.add_parser("publish", help="Prepare dataset for publication")
    pub_parser.add_argument("--dataset", required=True, help="Dataset JSONL file")
    pub_parser.add_argument("--version", default=CURRENT_VERSION, help="Benchmark version")
    pub_parser.add_argument("--splits-dir", default="rockman_splits", help="Splits directory")
    pub_parser.add_argument("--public-output", help="Public dataset output path")
    pub_parser.add_argument("--private-output", help="Private dataset output path")
    pub_parser.add_argument("--hidden-output", help="Hidden dataset output path")
    pub_parser.add_argument("--canary-output", help="Canary strings output path")
    pub_parser.set_defaults(func=cmd_publish)

    # validate
    val_parser = subparsers.add_parser("validate", help="Validate dataset quality")
    val_parser.add_argument("--dataset", required=True, help="Dataset JSONL file")
    val_parser.add_argument("--solutions-file", help="Reference solutions JSON file")
    val_parser.add_argument("--buggy-file", help="Buggy solutions JSON file")
    val_parser.add_argument("--problem-ids", help="Comma-separated problem IDs to validate")
    val_parser.add_argument("--output", help="Validation results output file")
    val_parser.set_defaults(func=cmd_validate)

    # encrypt
    enc_parser = subparsers.add_parser("encrypt", help="Encrypt hidden tests")
    enc_parser.add_argument("--input", required=True, help="Input JSONL file")
    enc_parser.add_argument("--output", required=True, help="Output JSONL file")
    enc_parser.add_argument("--version", default=CURRENT_VERSION, help="Benchmark version")
    enc_parser.set_defaults(func=cmd_encrypt)

    # decrypt
    dec_parser = subparsers.add_parser("decrypt", help="Decrypt hidden tests")
    dec_parser.add_argument("--input", required=True, help="Input JSONL file")
    dec_parser.add_argument("--version", default=CURRENT_VERSION, help="Benchmark version")
    dec_parser.set_defaults(func=cmd_decrypt)

    # version
    ver_parser = subparsers.add_parser("version", help="Manage benchmark versions")
    ver_parser.add_argument("--list", action="store_true", help="List all versions")
    ver_parser.add_argument("--register", help="Register new version")
    ver_parser.add_argument("--task-ids", help="Comma-separated task IDs for new version")
    ver_parser.add_argument("--description", help="Version description")
    ver_parser.add_argument("--parent", help="Parent version")
    ver_parser.add_argument("--verify", help="Verify version integrity")
    ver_parser.add_argument("--dataset", help="Dataset for verification")
    ver_parser.set_defaults(func=cmd_version)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()