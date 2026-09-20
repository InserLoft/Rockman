# -*- coding: utf-8 -*-
"""Rockman - Benchmark v0.2+
Backward-compatible facade for the new modular Rockman benchmark system.
"""

# Original simple API preserved for backward compatibility
rockman_problems = [
    {
        "task_id": "Rockman/0",
        "prompt": "def return_true():\n    \"\"\" Retorna siempre el valor booleano True.\"\"\"\n",
        "test": "assert return_true() == True"
    },
    {
        "task_id": "Rockman/1",
        "prompt": "def add_two_numbers(a: int, b: int) -> int:\n    \"\"\" Retorna la suma de dos números enteros.\"\"\"\n",
        "test": "assert add_two_numbers(2, 3) == 5\nassert add_two_numbers(-1, 1) == 0"
    }
]

print(f"Cargados {len(rockman_problems)} problemas de ejemplo para el benchmark.")

# --- New modular imports ---
from rockman.benchmark.schema import Problem, TaskType, Language
from rockman.benchmark.evaluator import Evaluator, get_handler
from rockman.benchmark.metrics import estimate_pass_at_k, aggregate_scores, BenchmarkReport
from rockman.benchmark.runners import get_runner
from rockman.dataset.generator import generate_benchmark_dataset
from rockman.dataset.validators import validate_dataset, generate_validation_report
from rockman.dataset.splits import SplitManager
from rockman.benchmark.encryption import HiddenTestEncryption, generate_master_secret
from rockman.benchmark.versioning import VersionRegistry, CURRENT_VERSION

import json
import math


# --- Backward-compatible functions ---

def evaluate_code(completion: str, test_code: str) -> bool:
    """
    Ejecuta el código generado junto con los asserts de prueba para validar si es correcto.
    (Backward compatible - uses new runner internally)
    """
    runner = get_runner("python", time_limit=2.0, memory_limit_mb=256)
    full_code = f"{completion}\n{test_code}"
    result = runner.execute(full_code)
    if not result.success:
        if result.error_type == "AssertionError":
            print("Fallo en los asserts del test.")
        else:
            print(f"Error de ejecución: {result.error_type}: {result.stderr}")
    return result.success


def save_problems_to_jsonl(problems, filename="rockman_dataset.jsonl"):
    """
    Guarda la lista de problemas en un archivo en formato JSON Lines.
    """
    with open(filename, "w", encoding="utf-8") as f:
        for problem in problems:
            if isinstance(problem, Problem):
                f.write(problem.to_jsonl() + "\n")
            else:
                f.write(json.dumps(problem, ensure_ascii=False) + "\n")
    print(f"Se han guardado {len(problems)} problemas en '{filename}'.")


def load_problems_from_jsonl(filename="rockman_dataset.jsonl"):
    """
    Carga los problemas desde un archivo JSON Lines.
    """
    problems = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line.strip())
                if "task_id" in data and "category" in data:
                    problems.append(Problem.from_dict(data))
                else:
                    # Legacy format - convert to Problem
                    problems.append(Problem(
                        task_id=data.get("task_id", ""),
                        category="Legacy",
                        subcategory="Unknown",
                        difficulty=2,
                        prompt=data.get("prompt", ""),
                        public_test=data.get("test", ""),
                        language="python",
                        task_type=TaskType.GENERATION.value,
                    ))
    return problems


def evaluate_benchmark(problems, model_outputs, k=1):
    """
    Evalúa un conjunto de problemas con las respuestas del modelo y calcula el Pass@k promedio.
    (Backward compatible - uses new evaluator internally)
    """
    # Convert to Problem objects if needed
    problem_objects = []
    for p in problems:
        if isinstance(p, Problem):
            problem_objects.append(p)
        elif isinstance(p, dict) and "task_id" in p:
            if "category" in p:
                problem_objects.append(Problem.from_dict(p))
            else:
                # Legacy format - convert
                problem_objects.append(Problem(
                    task_id=p["task_id"],
                    category="Legacy",
                    subcategory="Unknown",
                    difficulty=2,
                    prompt=p.get("prompt", ""),
                    public_test=p.get("test", ""),
                    language="python",
                    task_type=TaskType.GENERATION.value,
                ))

    evaluator = Evaluator()
    results = evaluator.evaluate_dataset(problem_objects, model_outputs, k=k)

    # Print in original format
    for task_id, task_results in results["results"].items():
        passed = sum(1 for r in task_results if r.passed)
        total = len(task_results)
        score = estimate_pass_at_k(total, passed, k)
        print(f"[{task_id}] Correctas: {passed}/{total} | Pass@{k} = {score:.4f}")

    print(f"\n>>> RESULTADO GLOBAL (Pass@{k}): {results['mean_pass_at_k']:.4f} <<<")
    return results['mean_pass_at_k']


# --- Original example evaluation ---
sampled_completion = """def add_two_numbers(a: int, b: int) -> int:
    return a + b
"""

is_correct = evaluate_code(sampled_completion, rockman_problems[1]["test"])
print(f"¿El código generado es correcto?: {is_correct}")

n_samples = 10
c_correct = 3
print(f"Pass@1: {estimate_pass_at_k(n_samples, c_correct, k=1):.4f}")
print(f"Pass@5: {estimate_pass_at_k(n_samples, c_correct, k=5):.4f}")

# Save/load demo
save_problems_to_jsonl(rockman_problems)
loaded_problems = load_problems_from_jsonl()
print(f"Problemas cargados exitosamente: {len(loaded_problems)}")
print("Primer problema cargado:", loaded_problems[0])

# Simulated model outputs
simulated_model_outputs = {
    "Rockman/0": [
        "def return_true():\n    return True",
        "def return_true():\n    return True",
        "def return_true():\n    return False",
        "def return_true():\n    pass",
        "def return_true():\n    return True",
    ],
    "Rockman/1": [
        "def add_two_numbers(a, b):\n    return a + b",
        "def add_two_numbers(a, b):\n    return a - b",
        "def add_two_numbers(a, b):\n    return a * b",
        "def add_two_numbers(a, b):\n    return sum([a, b])",
        "def add_two_numbers(a, b):\n    pass"
    ]
}

_ = evaluate_benchmark(loaded_problems, simulated_model_outputs, k=1)


# --- Frontier Problems (v0.1 style) ---
frontier_problems = [
    {
        "task_id": "Rockman/2",
        "prompt": """def shortest_path_with_key(grid: list[list[str]]) -> int:
    \"\"\"
    Encuentra la longitud del camino más corto desde el inicio 'S' hasta la salida 'E'
    en una cuadrícula de 2D de tamaño M x N.

    La cuadrícula contiene:
    - '.' : Celda transitable.
    - '#' : Obstáculo impenetrable.
    - 'S' : Punto de inicio.
    - 'E' : Punto de salida.
    - 'K' : Una llave única.
    - 'D' : Una puerta cerrada que SOLO se puede atravesar si ya has recogido la llave 'K'.

    Retorna la menor cantidad de pasos necesarios para llegar a 'E'.
    Si es imposible llegar a la salida cumpliendo las reglas, retorna -1.
    \"\"\"
""",
        "test": """grid1 = [
    ['S', '.', '.', '#', 'E'],
    ['.', '#', '.', 'D', '.'],
    ['.', 'K', '.', '#', '.']
]
assert shortest_path_with_key(grid1) == 8

grid2 = [
    ['S', '.', 'D', 'E'],
    ['.', '#', '#', '#'],
    ['.', '.', '.', 'K']
]
assert shortest_path_with_key(grid2) == 13
"""
    },
    {
        "task_id": "Rockman/3",
        "prompt": """def max_sliding_window_product(nums: list[int], k: int) -> list[int]:
    \"\"\"
    Dado un arreglo de enteros 'nums' y un tamaño de ventana 'k',
    encuentra el producto máximo de los elementos dentro de cada ventana deslizante de tamaño k.

    Debido a que el producto puede ser extremadamente grande, realiza los cálculos de manera eficiente
    evitando desbordamientos de tiempo (O(N) esperado).

    Ejemplo:
    nums = [1, 3, -1, -3, 5, 3, 6, 7], k = 3
    Retorna el producto máximo para cada subarreglo de tamaño 3.
    \"\"\"
""",
        "test": """assert max_sliding_window_product([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 9, 15, 45, 90, 126]
assert max_sliding_window_product([1, -2, 3, -4], 2) == [-2, -6, -12]
assert max_sliding_window_product([0, 0, 0], 2) == [0, 0]
"""
    }
]

# Convert to new Problem format
frontier_problem_objects = []
for fp in frontier_problems:
    frontier_problem_objects.append(Problem(
        task_id=fp["task_id"],
        category="Algorithms",
        subcategory="Graphs" if "shortest_path" in fp["prompt"] else "Data Structures",
        difficulty=4,
        prompt=fp["prompt"],
        public_test=fp["test"],
        language="python",
        task_type=TaskType.GENERATION.value,
    ))

# Update dataset
loaded_problems = load_problems_from_jsonl()
base_problems = [p for p in loaded_problems if p.task_id in ["Rockman/0", "Rockman/1"]]
all_problems = base_problems + frontier_problem_objects
save_problems_to_jsonl(all_problems)
print(f"Dataset 'Rockman' actualizado. Total de retos: {len(all_problems)}")


# --- New v0.2 Features Demo ---

def demo_new_features():
    """Demonstrate new v0.2 features."""
    print("\n" + "="*60)
    print("Rockman v0.2 - New Features Demo")
    print("="*60)

    # 1. Generate a larger dataset with new categories
    print("\n1. Generating v0.2 dataset with 500 problems...")
    master_secret = generate_master_secret()
    print(f"   Master secret (save for evaluation): {master_secret}")
    encryption = HiddenTestEncryption(master_secret)

    problems_v02 = generate_benchmark_dataset(
        target_count=100,  # Smaller for demo
        version="v0.2",
        encryption=encryption,
    )
    print(f"   Generated {len(problems_v02)} problems across {len(set(p.category for p in problems_v02))} categories")

    # Show category distribution
    from collections import Counter
    cat_dist = Counter(p.category for p in problems_v02)
    for cat, count in sorted(cat_dist.items()):
        print(f"     {cat}: {count}")

    # 2. Show task type distribution
    task_type_dist = Counter(p.task_type for p in problems_v02)
    print("\n   Task types:")
    for tt, count in sorted(task_type_dist.items()):
        print(f"     {tt}: {count}")

    # 3. Show difficulty distribution
    diff_dist = Counter(p.difficulty for p in problems_v02)
    print("\n   Difficulties:")
    for d in sorted(diff_dist.keys()):
        print(f"     Level {d}: {diff_dist[d]}")

    # 4. Validate a subset
    print("\n2. Validating sample problems...")
    sample = problems_v02[:5]
    results = validate_dataset(sample)
    print(generate_validation_report(results))

    # 5. Create splits
    print("\n3. Creating public/private/hidden splits...")
    split_manager = SplitManager("demo_splits")
    splits = split_manager.create_standard_splits(problems_v02, "v0.2")
    for name, split in splits.items():
        print(f"   {name}: {len(split.task_ids)} tasks")

    # 6. Show leaderboard format
    print("\n4. Leaderboard format example:")
    print("-" * 60)
    dummy_score = aggregate_scores([], problems_v02[:10])
    print(dummy_score.format_leaderboard())

    # 7. Multi-language support
    print("\n5. Supported languages:")
    from rockman.benchmark.runners import list_supported_languages
    for lang in list_supported_languages():
        print(f"   - {lang}")

    # 8. Versioning
    print("\n6. Version registry:")
    registry = VersionRegistry("demo_versions.json")
    try:
        registry.register("v0.2-demo", [p.task_id for p in problems_v02], "Demo version")
    except ValueError:
        pass  # Version already exists
    for v in registry.list_versions():
        print(f"   {v.version}: {v.task_count} tasks - {v.description}")


if __name__ == "__main__":
    demo_new_features()

    # Original Gemini integration (preserved but commented)
    print("\n" + "="*60)
    print("Original Gemini integration available via:")
    print("  from rockman_benchmark import run_live_gemini_evaluation")
    print("  (Requires GOOGLE_API_KEY in environment)")
    print("="*60)