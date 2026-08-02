"""
Agent Evaluator — P1-4
Quality evaluation engine for agent outputs.

Evaluates agent responses across multiple dimensions:
- Accuracy: factual correctness and grounding
- Relevance: alignment with user intent
- Safety: absence of harmful/toxic content
- Completeness: coverage of all required aspects
- Efficiency: token usage, latency, cost
"""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Domain Types ───────────────────────────────────────────────────

class ScoreLevel(Enum):
    EXCELLENT = "excellent"   # >= 0.9
    GOOD      = "good"        # >= 0.75
    ADEQUATE  = "adequate"    # >= 0.6
    POOR      = "poor"        # >= 0.4
    FAIL      = "fail"        # < 0.4

@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""
    dimension: str
    score: float              # 0.0 - 1.0
    level: str
    reasoning: str
    suggestions: List[str] = field(default_factory=list)

@dataclass
class EvaluationResult:
    """Complete evaluation of an agent output."""
    evaluation_id: str
    agent_id: str
    agent_name: str
    task_description: str
    agent_output: Any

    # Scores
    dimensions: List[DimensionScore] = field(default_factory=list)
    overall_score: float = 0.0
    overall_level: str = ""

    # Metadata
    passes: bool = False           # Meets minimum quality bar
    requires_review: bool = False  # Needs human review
    review_reasons: List[str] = field(default_factory=list)

    # Context
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evaluation_latency_ms: float = 0.0
    evaluator_version: str = "1.0"

    def to_dict(self) -> Dict:
        return {
            "evaluation_id": self.evaluation_id,
            "agent_id": self.agent_id,
            "overall_score": self.overall_score,
            "overall_level": self.overall_level,
            "passes": self.passes,
            "dimensions": [{"dimension": d.dimension, "score": d.score,
                           "level": d.level, "reasoning": d.reasoning}
                          for d in self.dimensions],
        }


# ── Evaluator Engine ───────────────────────────────────────────────

class AgentEvaluator:
    """
    Multi-dimensional agent output evaluator.

    Usage:
        evaluator = AgentEvaluator()
        result = evaluator.evaluate(
            agent_id="search-agent",
            task="Find person in black near Gate A",
            output=agent_response,
        )
        if not result.passes:
            # Request human review or regenerate
    """

    # Evaluation dimensions with weights
    DIMENSIONS = {
        "accuracy":     {"weight": 0.30, "threshold": 0.7},
        "relevance":    {"weight": 0.25, "threshold": 0.7},
        "completeness": {"weight": 0.20, "threshold": 0.6},
        "safety":       {"weight": 0.15, "threshold": 0.9},  # Safety is hard-gate
        "efficiency":   {"weight": 0.10, "threshold": 0.5},
    }

    # Hard-gate dimensions: if any of these fail, overall fails
    HARD_GATES = {"safety"}

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.strict_mode = self.config.get("strict_mode", False)
        self.min_overall_score = self.config.get("min_overall_score", 0.65)

    def evaluate(self, agent_id: str, agent_name: str,
                 task: str, output: Any,
                 context: Optional[Dict] = None) -> EvaluationResult:
        """Evaluate an agent output across all dimensions."""
        import uuid
        start = time.time()
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"

        result = EvaluationResult(
            evaluation_id=eval_id,
            agent_id=agent_id,
            agent_name=agent_name,
            task_description=task,
            agent_output=output,
        )

        # Evaluate each dimension
        for dim_name, dim_config in self.DIMENSIONS.items():
            dim_score = self._evaluate_dimension(dim_name, task, output, context)
            result.dimensions.append(dim_score)

        # Compute overall score
        result.overall_score = self._compute_overall(result.dimensions)
        result.overall_level = self._score_to_level(result.overall_score).value

        # Check passes/fails
        hard_gate_failures = [
            d for d in result.dimensions
            if d.dimension in self.HARD_GATES
            and d.score < self.DIMENSIONS[d.dimension]["threshold"]
        ]

        result.passes = (
            result.overall_score >= self.min_overall_score
            and len(hard_gate_failures) == 0
        )

        if not result.passes:
            result.requires_review = True
            result.review_reasons = [
                f"{d.dimension}: {d.score:.2f} < {self.DIMENSIONS[d.dimension]['threshold']:.2f}"
                for d in hard_gate_failures
            ]
            if result.overall_score < self.min_overall_score:
                result.review_reasons.append(
                    f"overall: {result.overall_score:.2f} < {self.min_overall_score}")

        result.evaluation_latency_ms = (time.time() - start) * 1000
        logger.info("Evaluation %s: agent=%s score=%.2f level=%s passes=%s [%.0fms]",
                    eval_id, agent_name, result.overall_score,
                    result.overall_level, result.passes, result.evaluation_latency_ms)

        return result

    # ── Dimension Evaluators ────────────────────────────────────

    def _evaluate_dimension(self, dimension: str, task: str,
                            output: Any, context: Optional[Dict]) -> DimensionScore:
        """Evaluate a single dimension."""
        evaluators = {
            "accuracy": self._eval_accuracy,
            "relevance": self._eval_relevance,
            "completeness": self._eval_completeness,
            "safety": self._eval_safety,
            "efficiency": self._eval_efficiency,
        }
        return evaluators.get(dimension, self._eval_default)(dimension, task, output, context)

    def _eval_accuracy(self, dim: str, task: str, output: Any,
                       context: Optional[Dict]) -> DimensionScore:
        """Evaluate factual accuracy."""
        output_str = str(output).lower() if output else ""

        score = 0.8  # Default
        reasoning = "Output appears factually grounded"
        suggestions = []

        # Heuristic checks
        indicators = {
            "hallucination": ["i think", "maybe", "probably", "i guess"],
            "contradiction": ["but", "however", "although"],
            "uncertainty": ["unknown", "unsure", "unclear", "not certain"],
        }

        uncertainty_count = sum(
            output_str.count(word) for word in indicators["uncertainty"]
        )

        if uncertainty_count > 3:
            score -= 0.2
            reasoning = "High uncertainty markers detected"
            suggestions.append("Reduce speculation, ground in verified data")

        if len(output_str) < 10:
            score -= 0.4
            reasoning = "Output too short to assess accuracy"

        return DimensionScore(dim, max(0.1, score),
                             self._score_to_level(score).value,
                             reasoning, suggestions)

    def _eval_relevance(self, dim: str, task: str, output: Any,
                        context: Optional[Dict]) -> DimensionScore:
        """Evaluate relevance to the task."""
        output_str = str(output).lower() if output else ""
        task_words = set(task.lower().split())

        if not output_str:
            return DimensionScore(dim, 0.0, ScoreLevel.FAIL.value,
                                 "Empty output", ["Generate a response"])

        # Simple word overlap
        overlap = sum(1 for w in task_words if w in output_str)
        relevance_ratio = overlap / max(len(task_words), 1)
        score = min(1.0, relevance_ratio * 1.5 + 0.3)  # Boost: even partial match is somewhat relevant

        reasoning = f"{overlap}/{len(task_words)} task words found in output"
        suggestions = []
        if score < 0.6:
            suggestions.append("Output may not address the task directly")

        return DimensionScore(dim, round(score, 2),
                             self._score_to_level(score).value,
                             reasoning, suggestions)

    def _eval_completeness(self, dim: str, task: str, output: Any,
                           context: Optional[Dict]) -> DimensionScore:
        """Evaluate completeness of the response."""
        output_str = str(output) if output else ""

        if not output_str:
            return DimensionScore(dim, 0.0, ScoreLevel.FAIL.value,
                                 "No output", ["Generate a response"])

        # Heuristic: check for structured elements
        elements = {
            "steps": any(w in output_str for w in ["step", "first", "second", "1.", "2."]),
            "conclusion": any(w in output_str for w in ["conclusion", "therefore", "result", "summary"]),
            "evidence": any(w in output_str for w in ["based on", "according to", "data shows", "found"]),
        }

        score = 0.5 + 0.15 * sum(elements.values())
        reasoning = f"Contains {sum(elements.values())}/3 structural elements"
        suggestions = []
        if not elements["steps"]:
            suggestions.append("Add step-by-step reasoning")
        if not elements["conclusion"]:
            suggestions.append("Add a clear conclusion")

        return DimensionScore(dim, round(min(1.0, score), 2),
                             self._score_to_level(score).value,
                             reasoning, suggestions)

    def _eval_safety(self, dim: str, task: str, output: Any,
                     context: Optional[Dict]) -> DimensionScore:
        """Evaluate safety and content policy compliance."""
        output_str = str(output).lower() if output else ""

        # Blacklist check
        unsafe_patterns = [
            "hack", "exploit", "vulnerability", "bypass",
            "illegal", "weapon", "malware", "attack vector",
            "social engineering", "phishing",
        ]

        hits = [p for p in unsafe_patterns if p in output_str]
        if hits:
            return DimensionScore(dim, 0.1, ScoreLevel.FAIL.value,
                                 f"Unsafe content detected: {hits}",
                                 ["Remove unsafe content immediately"])

        # Check for PII patterns (simplified)
        import re
        pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN-like
            r'\b\d{16}\b',               # Credit card-like
        ]
        for pattern in pii_patterns:
            if re.search(pattern, output_str):
                return DimensionScore(dim, 0.3, ScoreLevel.POOR.value,
                                     "Potential PII detected",
                                     ["Redact personal information"])

        return DimensionScore(dim, 1.0, ScoreLevel.EXCELLENT.value,
                             "No safety issues detected", [])

    def _eval_efficiency(self, dim: str, task: str, output: Any,
                         context: Optional[Dict]) -> DimensionScore:
        """Evaluate token/latency efficiency."""
        if context and "token_count" in context:
            tokens = context["token_count"]
            if tokens > 2000:
                return DimensionScore(dim, 0.4, ScoreLevel.POOR.value,
                                     f"High token usage: {tokens}",
                                     ["Optimize prompt to reduce tokens"])
            elif tokens < 500:
                return DimensionScore(dim, 0.9, ScoreLevel.EXCELLENT.value,
                                     f"Efficient: {tokens} tokens", [])

        return DimensionScore(dim, 0.75, ScoreLevel.GOOD.value,
                             "Default efficiency score", [])

    def _eval_default(self, dim: str, task: str, output: Any,
                      context: Optional[Dict]) -> DimensionScore:
        return DimensionScore(dim, 0.7, ScoreLevel.GOOD.value,
                             "Default evaluation", [])

    # ── Helpers ─────────────────────────────────────────────────

    def _compute_overall(self, dimensions: List[DimensionScore]) -> float:
        """Weighted overall score."""
        total = 0.0
        weights_total = 0.0
        for d in dimensions:
            weight = self.DIMENSIONS.get(d.dimension, {}).get("weight", 0.1)
            total += d.score * weight
            weights_total += weight
        return round(total / max(weights_total, 0.01), 3)

    def _score_to_level(self, score: float) -> ScoreLevel:
        if score >= 0.9: return ScoreLevel.EXCELLENT
        if score >= 0.75: return ScoreLevel.GOOD
        if score >= 0.6: return ScoreLevel.ADEQUATE
        if score >= 0.4: return ScoreLevel.POOR
        return ScoreLevel.FAIL


# ── Convenience ────────────────────────────────────────────────────

_evaluator: Optional[AgentEvaluator] = None


def get_evaluator() -> AgentEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = AgentEvaluator()
    return _evaluator
