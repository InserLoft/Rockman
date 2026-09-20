"""Human baseline evaluation framework"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class ExperienceLevel(str, Enum):
    NOVICE = "novice"           # < 1 year
    JUNIOR = "junior"           # 1-3 years
    MID = "mid"                 # 3-7 years
    SENIOR = "senior"           # 7-15 years
    EXPERT = "expert"           # 15+ years
    COMPETITIVE = "competitive" # Competitive programming background


class Domain(str, Enum):
    GENERAL = "general"
    ALGORITHMS = "algorithms"
    SYSTEMS = "systems"
    ML = "ml"
    WEB = "web"
    EMBEDDED = "embedded"


@dataclass
class HumanParticipant:
    """A human participant in baseline evaluation."""
    participant_id: str  # Anonymized
    experience_level: ExperienceLevel
    years_experience: int
    domains: List[Domain]
    competitive_programming: bool = False
    competitive_rating: Optional[int] = None  # Codeforces/AtCoder rating
    primary_languages: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class HumanAttempt:
    """A single human attempt at a problem."""
    participant_id: str
    problem_id: str
    language: str
    time_minutes: float
    passed: bool
    compilation_errors: int = 0
    runtime_errors: int = 0
    wrong_answer: int = 0
    time_limit_exceeded: int = 0
    memory_limit_exceeded: int = 0
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class HumanBaselineResult:
    """Results of human baseline evaluation."""
    benchmark_version: str
    date: str
    participants: List[HumanParticipant]
    attempts: List[HumanAttempt]
    summary: Dict[str, Any] = field(default_factory=dict)

    def compute_summary(self):
        """Compute summary statistics."""
        if not self.attempts:
            self.summary = {}
            return

        # Overall
        total_attempts = len(self.attempts)
        passed_attempts = sum(1 for a in self.attempts if a.passed)
        self.summary["overall_pass_rate"] = passed_attempts / total_attempts

        # By participant
        by_participant = {}
        for a in self.attempts:
            if a.participant_id not in by_participant:
                by_participant[a.participant_id] = {"total": 0, "passed": 0, "time": []}
            by_participant[a.participant_id]["total"] += 1
            if a.passed:
                by_participant[a.participant_id]["passed"] += 1
            by_participant[a.participant_id]["time"].append(a.time_minutes)

        self.summary["by_participant"] = {
            pid: {
                "pass_rate": d["passed"] / d["total"],
                "avg_time": sum(d["time"]) / len(d["time"]) if d["time"] else 0,
                "problems_solved": d["passed"],
            }
            for pid, d in by_participant.items()
        }

        # By difficulty
        # Would need problem metadata - placeholder
        self.summary["by_difficulty"] = {}

        # By experience level
        by_experience = defaultdict(lambda: {"total": 0, "passed": 0})
        for a in self.attempts:
            # Find participant
            p = next((p for p in self.participants if p.participant_id == a.participant_id), None)
            if p:
                exp = p.experience_level.value
                by_experience[exp]["total"] += 1
                if a.passed:
                    by_experience[exp]["passed"] += 1

        self.summary["by_experience"] = {
            exp: d["passed"] / d["total"] if d["total"] > 0 else 0
            for exp, d in by_experience.items()
        }

        # By domain background
        by_domain = defaultdict(lambda: {"total": 0, "passed": 0})
        for a in self.attempts:
            p = next((p for p in self.participants if p.participant_id == a.participant_id), None)
            if p:
                for domain in p.domains:
                    by_domain[domain.value]["total"] += 1
                    if a.passed:
                        by_domain[domain.value]["passed"] += 1

        self.summary["by_domain"] = {
            dom: d["passed"] / d["total"] if d["total"] > 0 else 0
            for dom, d in by_domain.items()
        }

        # Time statistics
        times = [a.time_minutes for a in self.attempts if a.passed]
        if times:
            self.summary["time_stats"] = {
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "stdev": statistics.stdev(times) if len(times) > 1 else 0,
                "min": min(times),
                "max": max(times),
            }

    def to_dict(self) -> Dict[str, Any]:
        self.compute_summary()
        return {
            "benchmark_version": self.benchmark_version,
            "date": self.date,
            "participants": [p.__dict__ for p in self.participants],
            "attempts": [a.__dict__ for a in self.attempts],
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HumanBaselineResult":
        participants = [HumanParticipant(**p) for p in data.get("participants", [])]
        attempts = [HumanAttempt(**a) for a in data.get("attempts", [])]
        return cls(
            benchmark_version=data["benchmark_version"],
            date=data["date"],
            participants=participants,
            attempts=attempts,
            summary=data.get("summary", {}),
        )

    def save(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "HumanBaselineResult":
        with open(filepath) as f:
            data = json.load(f)
        return cls.from_dict(data)


class HumanBaselineEvaluator:
    """Manages human baseline evaluation sessions."""

    def __init__(self, benchmark_version: str):
        self.benchmark_version = benchmark_version
        self.participants: List[HumanParticipant] = []
        self.attempts: List[HumanAttempt] = []

    def add_participant(self, participant: HumanParticipant):
        self.participants.append(participant)

    def record_attempt(self, attempt: HumanAttempt):
        self.attempts.append(attempt)

    def get_result(self) -> HumanBaselineResult:
        return HumanBaselineResult(
            benchmark_version=self.benchmark_version,
            date=datetime.utcnow().isoformat() + "Z",
            participants=self.participants,
            attempts=self.attempts,
        )

    def print_summary(self):
        result = self.get_result()
        result.compute_summary()
        s = result.summary

        print(f"\n{'='*70}")
        print(f"Human Baseline Evaluation - {self.benchmark_version}")
        print(f"{'='*70}")
        print(f"Participants: {len(self.participants)}")
        print(f"Total Attempts: {len(self.attempts)}")
        print(f"Overall Pass Rate: {s.get('overall_pass_rate', 0):.1%}")

        print(f"\nBy Experience Level:")
        for exp, rate in s.get("by_experience", {}).items():
            print(f"  {exp}: {rate:.1%}")

        print(f"\nBy Domain Background:")
        for dom, rate in s.get("by_domain", {}).items():
            print(f"  {dom}: {rate:.1%}")

        if "time_stats" in s:
            ts = s["time_stats"]
            print(f"\nTime to Solve (passed only):")
            print(f"  Mean: {ts['mean']:.1f} min, Median: {ts['median']:.1f} min")
            print(f"  Range: {ts['min']:.1f} - {ts['max']:.1f} min")

        print(f"\nParticipants:")
        for p in self.participants:
            pid = p.participant_id
            pd = s.get("by_participant", {}).get(pid, {})
            print(f"  {pid} ({p.experience_level.value}, {p.years_experience}y): "
                  f"{pd.get('pass_rate', 0):.1%} pass rate, "
                  f"{pd.get('avg_time', 0):.1f} min avg")

        print(f"{'='*70}")


import statistics
from collections import defaultdict