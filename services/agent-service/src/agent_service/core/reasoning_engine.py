"""Reasoning Engine — Multi-step inference with logical deduction."""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReasoningStep(Enum):
    OBSERVE = "observe"        # Gather facts
    HYPOTHESIZE = "hypothesize" # Generate hypotheses
    VALIDATE = "validate"       # Test against evidence
    DEDUCE = "deduce"           # Logical deduction
    CONCLUDE = "conclude"       # Final conclusion


@dataclass
class Fact:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""
    source: str = ""         # camera, search, agent, user
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class Hypothesis:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""
    supporting_facts: List[str] = field(default_factory=list)
    confidence: float = 0.5
    status: str = "pending"  # pending, confirmed, rejected

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ReasoningResult:
    query: str = ""
    steps: List[Dict] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    facts_used: int = 0
    hypotheses_evaluated: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class ReasoningEngine:
    """Multi-step reasoning engine with hypothesis generation and validation."""

    def __init__(self, llm_provider=None):
        self._facts: Dict[str, Fact] = {}
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._rules: List[Dict] = []
        self.llm = llm_provider
        self._init_demo_facts()

    def _init_demo_facts(self):
        """Initialize with demo investigation facts."""
        facts = [
            Fact(statement="Person in red jacket observed at Camera A3 at 20:15", source="camera", confidence=0.95),
            Fact(statement="Same person observed at Camera B1 at 20:22", source="camera", confidence=0.88),
            Fact(statement="Vehicle with plate ABC123 entered Gate A at 20:10", source="camera", confidence=0.97),
            Fact(statement="Vehicle ABC123 left through Gate B at 20:30", source="camera", confidence=0.96),
            Fact(statement="Suspect known to drive Vehicle ABC123", source="case", confidence=0.90),
            Fact(statement="Security alarm triggered at Gate A at 20:12", source="alarm", confidence=0.99),
        ]
        for f in facts:
            self._facts[f.id] = f
        logger.info("Reasoning Engine: %d demo facts loaded", len(facts))

    def add_fact(self, statement: str, source: str = "user", confidence: float = 1.0) -> Fact:
        fact = Fact(statement=statement, source=source, confidence=confidence)
        self._facts[fact.id] = fact
        return fact

    def reason(self, query: str, max_steps: int = 5) -> ReasoningResult:
        """Execute multi-step reasoning on a query."""
        result = ReasoningResult(query=query)
        relevant_facts = self._find_relevant(query)

        # Step 1: Observe
        result.steps.append({
            "step": ReasoningStep.OBSERVE.value,
            "action": f"Gathered {len(relevant_facts)} relevant facts",
            "facts": [f.statement[:80] for f in relevant_facts],
        })

        # Step 2: Hypothesize
        hypotheses = self._generate_hypotheses(query, relevant_facts)
        result.steps.append({
            "step": ReasoningStep.HYPOTHESIZE.value,
            "action": f"Generated {len(hypotheses)} hypotheses",
            "hypotheses": [h.statement for h in hypotheses],
        })

        # Step 3: Validate
        for h in hypotheses:
            score = self._validate_hypothesis(h, relevant_facts)
            h.confidence = score
            h.status = "confirmed" if score > 0.7 else "rejected" if score < 0.3 else "pending"
        confirmed = [h for h in hypotheses if h.status == "confirmed"]
        result.steps.append({
            "step": ReasoningStep.VALIDATE.value,
            "action": f"Validated: {len(confirmed)} confirmed, {len(hypotheses)-len(confirmed)} rejected",
        })

        # Step 4: Deduce
        conclusion, confidence = self._deduce(confirmed, relevant_facts, query)
        result.steps.append({
            "step": ReasoningStep.DEDUCE.value,
            "action": "Logical deduction completed",
        })

        # Step 5: Conclude
        result.conclusion = conclusion
        result.confidence = confidence
        result.facts_used = len(relevant_facts)
        result.hypotheses_evaluated = len(hypotheses)
        result.steps.append({
            "step": ReasoningStep.CONCLUDE.value,
            "conclusion": conclusion,
            "confidence": confidence,
        })

        logger.info("Reasoning complete: %s -> confidence %.2f", query[:50], confidence)
        return result

    def _find_relevant(self, query: str) -> List[Fact]:
        """Find facts relevant to the query via keyword matching."""
        ql = query.lower()
        scored = []
        for fact in self._facts.values():
            score = sum(1 for w in ql.split() if w in fact.statement.lower())
            if score > 0:
                scored.append((score * fact.confidence, fact))
        scored.sort(key=lambda x: -x[0])
        return [f for _, f in scored[:10]]

    def _generate_hypotheses(self, query: str, facts: List[Fact]) -> List[Hypothesis]:
        """Generate hypotheses from facts."""
        hyps = []
        if len(facts) >= 2:
            hyps.append(Hypothesis(
                statement=f"Based on {facts[0].statement[:50]} and {facts[-1].statement[:50]}, the subject is likely the same person",
                supporting_facts=[facts[0].id, facts[-1].id],
            ))
        if facts:
            hyps.append(Hypothesis(
                statement=f"Evidence from {facts[0].source} suggests suspicious activity at the reported time",
                supporting_facts=[facts[0].id],
            ))
        if len(facts) >= 3:
            hyps.append(Hypothesis(
                statement=f"Connected events at {facts[0].source} and {facts[1].source} form a timeline of events",
                supporting_facts=[facts[0].id, facts[1].id],
            ))
        for h in hyps:
            self._hypotheses[h.id] = h
        return hyps

    def _validate_hypothesis(self, hypothesis: Hypothesis, facts: List[Fact]) -> float:
        """Validate a hypothesis against supporting facts."""
        if not hypothesis.supporting_facts:
            return 0.3
        total_conf = 0.0
        for fid in hypothesis.supporting_facts:
            fact = self._facts.get(fid)
            if fact:
                total_conf += fact.confidence
        return min(total_conf / len(hypothesis.supporting_facts), 0.99)

    def _deduce(self, hypotheses: List[Hypothesis], facts: List[Fact], query: str) -> Tuple[str, float]:
        """Logical deduction from confirmed hypotheses."""
        if not hypotheses:
            return f"Unable to reach conclusion for: {query}. Insufficient evidence.", 0.2
        if len(hypotheses) >= 2:
            conc = f"Conclusion: {hypotheses[0].statement} Additionally, {hypotheses[1].statement}. Based on {len(facts)} pieces of evidence."
            conf = round(sum(h.confidence for h in hypotheses) / len(hypotheses), 2)
        else:
            conc = f"Conclusion: {hypotheses[0].statement}"
            conf = hypotheses[0].confidence
        return conc, conf

    def get_facts(self) -> List[Dict]:
        return [f.to_dict() for f in self._facts.values()]

    def get_hypotheses(self) -> List[Dict]:
        return [h.to_dict() for h in self._hypotheses.values()]

    def clear(self):
        self._facts.clear()
        self._hypotheses.clear()
        self._init_demo_facts()


reasoning_engine = ReasoningEngine()
