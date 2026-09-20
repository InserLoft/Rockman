"""Professional evaluation report generation"""

import json
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

from rockman.benchmark.schema import Problem, RockmanScore, ModelEvaluation
from rockman.baselines.calibration import CalibrationResult
from rockman.baselines.human_baseline import HumanBaselineResult


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    title: str = "Rockman Benchmark Evaluation Report"
    benchmark_version: str = "v0.2"
    include_charts: bool = False  # Requires matplotlib
    output_format: str = "markdown"  # markdown, html, json
    show_confidence_intervals: bool = True
    show_statistical_significance: bool = True
    compare_with_baselines: bool = True
    compare_with_human: bool = False


class ReportGenerator:
    """Generates professional evaluation reports."""
    
    def __init__(self, config: ReportConfig = None):
        self.config = config or ReportConfig()
    
    def generate_model_report(
        self,
        evaluation: ModelEvaluation,
        problems: List[Problem] = None,
        calibration: CalibrationResult = None,
        human_baseline: HumanBaselineResult = None,
        baseline_comparisons: Dict[str, ModelEvaluation] = None
    ) -> str:
        """Generate a comprehensive model evaluation report."""
        if self.config.output_format == "json":
            return self._generate_json(evaluation, problems, calibration, human_baseline, baseline_comparisons)
        elif self.config.output_format == "html":
            return self._generate_html(evaluation, problems, calibration, human_baseline, baseline_comparisons)
        else:
            return self._generate_markdown(evaluation, problems, calibration, human_baseline, baseline_comparisons)
    
    def _generate_markdown(
        self,
        evaluation: ModelEvaluation,
        problems: List[Problem] = None,
        calibration: CalibrationResult = None,
        human_baseline: HumanBaselineResult = None,
        baseline_comparisons: Dict[str, ModelEvaluation] = None
    ) -> str:
        lines = []
        score = evaluation.score
        
        # Header
        lines.append(f"# {self.config.title}")
        lines.append("")
        lines.append(f"**Benchmark Version:** {self.config.benchmark_version}")
        lines.append(f"**Model:** {evaluation.model_name} ({evaluation.model_version})")
        lines.append(f"**Evaluation Date:** {evaluation.date}")
        lines.append(f"**Hardware:** {evaluation.hardware}")
        lines.append(f"**Settings:** Temperature={evaluation.temperature}, Max Tokens={evaluation.max_tokens}, Attempts={evaluation.num_attempts}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"**Overall Rockman Score: {score.overall:.1f}%**")
        lines.append(f"**Tasks Evaluated:** {score.total_tasks} | **Tasks Passed (Pass@1=1.0):** {score.passed_tasks}")
        
        if self.config.show_confidence_intervals:
            ci = evaluation.confidence_interval if hasattr(evaluation, 'confidence_interval') else score.confidence_interval
            if hasattr(evaluation, 'confidence_interval') and evaluation.confidence_interval != (0.0, 0.0):
                lines.append(f"**95% Confidence Interval:** [{evaluation.confidence_interval[0]:.1f}%, {evaluation.confidence_interval[1]:.1f}%]")
        lines.append("")
        
        # Key Metrics
        lines.append("## Key Metrics")
        lines.append("")
        lines.append("| Metric | Score |")
        lines.append("|--------|-------|")
        lines.append(f"| Overall Pass Rate | {score.overall:.1f}% |")
        lines.append(f"| Efficiency Score | {score.efficiency_score:.1f}% |")
        lines.append(f"| Robustness Score | {score.robustness_score:.1f}% |")
        lines.append("")
        
        # Difficulty Breakdown
        lines.append("## Performance by Difficulty")
        lines.append("")
        lines.append("| Difficulty | Level | Pass Rate |")
        lines.append("|------------|-------|-----------|")
        difficulty_labels = {
            1: "Introductory", 2: "Easy", 3: "Intermediate", 
            4: "Advanced", 5: "Hard", 6: "Expert", 7: "Research"
        }
        for d in sorted(score.by_difficulty.keys()):
            label = difficulty_labels.get(d, f"Level {d}")
            lines.append(f"| {d} | {label} | {score.by_difficulty[d]:.1f}% |")
        lines.append("")
        
        # Category Breakdown
        lines.append("## Performance by Category")
        lines.append("")
        lines.append("| Category | Pass Rate |")
        lines.append("|----------|-----------|")
        for cat in sorted(score.by_category.keys(), key=lambda x: -score.by_category[x]):
            lines.append(f"| {cat} | {score.by_category[cat]:.1f}% |")
        lines.append("")
        
        # Task Type Breakdown
        if score.by_task_type:
            lines.append("## Performance by Task Type")
            lines.append("")
            lines.append("| Task Type | Pass Rate |")
            lines.append("|-----------|-----------|")
            for tt in sorted(score.by_task_type.keys(), key=lambda x: -score.by_task_type[x]):
                lines.append(f"| {tt} | {score.by_task_type[tt]:.1f}% |")
            lines.append("")
        
        # Language Breakdown
        if score.by_language:
            lines.append("## Performance by Language")
            lines.append("")
            lines.append("| Language | Pass Rate |")
            lines.append("|----------|-----------|")
            for lang in sorted(score.by_language.keys(), key=lambda x: -score.by_language[x]):
                lines.append(f"| {lang} | {score.by_language[lang]:.1f}% |")
            lines.append("")
        
        # Calibration Results
        if calibration:
            lines.append("## Difficulty Calibration")
            lines.append("")
            lines.append(f"**Reference Model:** {calibration.model_name} v{calibration.model_version}")
            lines.append(f"**Overall Pass Rate:** {calibration.overall_pass_rate:.1%}")
            lines.append("")
            lines.append("| Difficulty | Pass Rate | 95% CI |")
            lines.append("|------------|-----------|--------|")
            for d in sorted(calibration.difficulty_scores.keys()):
                rate = calibration.difficulty_scores[d]
                ci = calibration.confidence_intervals.get(f"difficulty_{d}", (0, 0))
                lines.append(f"| {d} | {rate:.1%} | [{ci[0]:.1f}%, {ci[1]:.1f}%] |")
            lines.append("")
            
            lines.append("### Difficulty Separation (should be positive)")
            lines.append("")
            for k, v in calibration.difficulty_separation.items():
                status = "✓" if v > 0 else "✗"
                lines.append(f"- {k}: {v:.3f} {status}")
            
            if calibration.notes:
                lines.append("")
                lines.append("**Calibration Notes:**")
                for note in calibration.notes:
                    lines.append(f"- {note}")
            lines.append("")
        
        # Human Baseline Comparison
        if human_baseline and human_baseline.summary:
            lines.append("## Human Baseline Comparison")
            lines.append("")
            hb = human_baseline.summary
            lines.append(f"**Human Participants:** {len(human_baseline.participants)}")
            lines.append(f"**Human Overall Pass Rate:** {hb.get('overall_pass_rate', 0):.1%}")
            lines.append(f"**Model vs Human Gap:** {score.overall/100 - hb.get('overall_pass_rate', 0):.1%}")
            lines.append("")
            
            if "by_experience" in hb:
                lines.append("### Human Performance by Experience")
                lines.append("")
                for exp, rate in hb["by_experience"].items():
                    lines.append(f"- {exp}: {rate:.1%}")
                lines.append("")
        
        # Baseline Comparisons
        if self.config.compare_with_baselines and baseline_comparisons:
            lines.append("## Comparison with Baselines")
            lines.append("")
            lines.append("| Model | Version | Overall |")
            lines.append("|-------|---------|---------|")
            lines.append(f"| {evaluation.model_name} | {evaluation.model_version} | {score.overall:.1f}% |")
            for name, baseline in baseline_comparisons.items():
                bscore = baseline.score
                lines.append(f"| {name} | {baseline.model_version} | {bscore.overall:.1f}% |")
            lines.append("")
        
        # Statistical Significance
        if self.config.show_statistical_significance and baseline_comparisons:
            lines.append("## Statistical Significance")
            lines.append("")
            from rockman.benchmark.metrics import statistical_significance
            for name, baseline in baseline_comparisons.items():
                sig = statistical_significance(score, baseline.score)
                if sig.get("significant"):
                    lines.append(f"- **{name}**: Significant difference (p={sig['p_value']:.4f}, diff={sig['diff']:.1f}%)")
                else:
                    lines.append(f"- **{name}**: Not significantly different (p={sig['p_value']:.4f})")
            lines.append("")
        
        # Methodology
        lines.append("## Methodology")
        lines.append("")
        lines.append("### Evaluation Protocol")
        lines.append("- Each problem evaluated with multiple samples (Pass@k)")
        lines.append("- Hidden tests used to prevent memorization")
        lines.append("- Time and memory limits enforced")
        lines.append("- Deterministic execution verified")
        lines.append("")
        
        lines.append("### Scoring")
        lines.append("- **Overall Score**: Mean Pass@1 across all problems")
        lines.append("- **Efficiency Score**: Pass rate on complexity-tagged problems")
        lines.append("- **Robustness Score**: Pass rate on edge-case-tagged problems")
        lines.append("- **Confidence Intervals**: Wilson score interval (95%)")
        lines.append("")
        
        # Reproducibility
        lines.append("## Reproducibility")
        lines.append("")
        lines.append(f"- Benchmark Version: {self.config.benchmark_version}")
        lines.append(f"- Evaluation Date: {evaluation.date}")
        lines.append(f"- Hardware: {evaluation.hardware}")
        lines.append(f"- Full environment captured in reproducibility manifest")
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json(
        self,
        evaluation: ModelEvaluation,
        problems: List[Problem] = None,
        calibration: CalibrationResult = None,
        human_baseline: HumanBaselineResult = None,
        baseline_comparisons: Dict[str, ModelEvaluation] = None
    ) -> str:
        """Generate JSON report."""
        data = {
            "title": self.config.title,
            "benchmark_version": self.config.benchmark_version,
            "model": {
                "name": evaluation.model_name,
                "version": evaluation.model_version,
            },
            "settings": {
                "temperature": evaluation.temperature,
                "max_tokens": evaluation.max_tokens,
                "num_attempts": evaluation.num_attempts,
            },
            "hardware": evaluation.hardware,
            "date": evaluation.date,
            "score": evaluation.score.to_dict(),
            "confidence_interval": evaluation.confidence_interval if hasattr(evaluation, 'confidence_interval') else None,
        }
        
        if calibration:
            data["calibration"] = {
                "model": f"{calibration.model_name} {calibration.model_version}",
                "difficulty_scores": calibration.difficulty_scores,
                "category_scores": calibration.category_scores,
                "overall_pass_rate": calibration.overall_pass_rate,
                "difficulty_separation": calibration.difficulty_separation,
                "confidence_intervals": calibration.confidence_intervals,
                "notes": calibration.notes,
            }
        
        if human_baseline:
            data["human_baseline"] = human_baseline.to_dict()
        
        if baseline_comparisons:
            data["baseline_comparisons"] = {
                name: {
                    "score": baseline.score.to_dict(),
                    "model_version": baseline.model_version,
                }
                for name, baseline in baseline_comparisons.items()
            }
        
        return json.dumps(data, indent=2)
    
    def _generate_html(
        self,
        evaluation: ModelEvaluation,
        problems: List[Problem] = None,
        calibration: CalibrationResult = None,
        human_baseline: HumanBaselineResult = None,
        baseline_comparisons: Dict[str, ModelEvaluation] = None
    ) -> str:
        """Generate HTML report."""
        markdown = self._generate_markdown(evaluation, problems, calibration, human_baseline, baseline_comparisons)
        
        # Simple markdown to HTML conversion
        html = markdown.replace("\n## ", "\n<h2>").replace("## ", "<h2>").replace("</h2>", "</h2>")
        html = html.replace("\n# ", "\n<h1>").replace("# ", "<h1>").replace("</h1>", "</h1>")
        html = html.replace("\n\n", "<br><br>")
        html = html.replace("| ", "<td>").replace(" |", "</td>").replace("|", "")
        
        template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.config.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        code {{ background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
{html}
</body>
</html>
"""
        return template
    
    def save_report(self, report: str, filepath: str):
        """Save report to file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(report)
        print(f"Report saved to {filepath}")


def generate_leaderboard_report(
    evaluations: List[ModelEvaluation],
    output_path: str,
    benchmark_version: str = "v0.2"
) -> str:
    """Generate a leaderboard report comparing multiple models."""
    lines = []
    lines.append(f"# Rockman {benchmark_version} Leaderboard")
    lines.append("")
    lines.append(f"**Generated:** {datetime.utcnow().isoformat()}Z")
    lines.append("")
    
    # Sort by overall score
    sorted_evals = sorted(evaluations, key=lambda e: e.score.overall, reverse=True)
    
    lines.append("| Rank | Model | Version | Overall | Efficiency | Robustness | Date |")
    lines.append("|------|-------|---------|---------|------------|------------|------|")
    for i, eval in enumerate(sorted_evals, 1):
        score = eval.score
        lines.append(f"| {i} | {eval.model_name} | {eval.model_version} | {score.overall:.1f}% | {score.efficiency_score:.1f}% | {score.robustness_score:.1f}% | {eval.date[:10]} |")
    lines.append("")
    
    # Detailed breakdown
    lines.append("## Detailed Breakdown")
    lines.append("")
    for eval in sorted_evals:
        score = eval.score
        lines.append(f"### {eval.model_name} v{eval.model_version}")
        lines.append(f"**Overall: {score.overall:.1f}%**  \n")
        
        lines.append("| Difficulty | Pass Rate |")
        lines.append("|------------|-----------|")
        for d in sorted(score.by_difficulty.keys()):
            lines.append(f"| Level {d} | {score.by_difficulty[d]:.1f}% |")
        lines.append("")
        
        lines.append("| Category | Pass Rate |")
        lines.append("|----------|-----------|")
        for cat in sorted(score.by_category.keys(), key=lambda x: -score.by_category[x]):
            lines.append(f"| {cat} | {score.by_category[cat]:.1f}% |")
        lines.append("")
    
    report = "\n".join(lines)
    with open(output_path, "w") as f:
        f.write(report)
    print(f"Leaderboard saved to {output_path}")
    return report