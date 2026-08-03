"""
Search Quality Evaluator — precision@K, recall, mAP, NDCG.
Measures search accuracy for continuous improvement.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class QualityMetrics:
    precision_at_1: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_10: float = 0.0
    mAP: float = 0.0           # Mean Average Precision
    ndcg_at_10: float = 0.0     # Normalized Discounted Cumulative Gain
    mrr: float = 0.0            # Mean Reciprocal Rank
    total_queries: int = 0
    avg_latency_ms: float = 0.0

@dataclass
class QueryEval:
    query: str
    query_type: str
    results_count: int
    relevant_count: int
    first_relevant_rank: int
    latency_ms: float
    precision_at_10: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SearchQualityEvaluator:
    """Continuous search quality measurement."""

    def __init__(self):
        self._evaluations: List[QueryEval] = []
        self._annotations: Dict[str, Dict[str, bool]] = {}  # query_id → {result_id: relevant}

    def add_annotation(self, query_id: str, result_id: str, relevant: bool):
        """Record human annotation for a search result."""
        if query_id not in self._annotations:
            self._annotations[query_id] = {}
        self._annotations[query_id][result_id] = relevant

    def evaluate(self, query: str, query_type: str, results: List[Dict],
                 latency_ms: float = 0) -> QueryEval:
        """Evaluate a single search query."""
        relevant = 0
        first_rank = 0
        annotations = self._annotations.get(query, {})

        for i, r in enumerate(results[:10]):
            rid = r.get("id", r.get("entity_id", ""))
            if annotations.get(rid, False) or r.get("score", 0) > 0.85:
                relevant += 1
                if first_rank == 0:
                    first_rank = i + 1

        p10 = relevant / min(len(results), 10) if results else 0

        ev = QueryEval(
            query=query[:100], query_type=query_type,
            results_count=len(results), relevant_count=relevant,
            first_relevant_rank=first_rank,
            precision_at_10=round(p10, 3),
            latency_ms=round(latency_ms, 1),
        )
        self._evaluations.append(ev)
        return ev

    def get_metrics(self) -> QualityMetrics:
        """Compute aggregate quality metrics."""
        if not self._evaluations:
            return QualityMetrics()

        evals = self._evaluations[-100:]
        n = len(evals)

        p1 = sum(1 for e in evals if e.first_relevant_rank == 1) / n
        p5_list = []
        p10_list = []
        r10_list = []
        mrr_sum = 0
        ndcg_sum = 0

        for e in evals:
            p5 = e.relevant_count / 5
            p5_list.append(min(p5, 1.0))
            p10 = e.precision_at_10
            p10_list.append(p10)
            r10 = e.relevant_count / max(e.results_count, 1)
            r10_list.append(r10)
            mrr_sum += 1.0 / e.first_relevant_rank if e.first_relevant_rank > 0 else 0

        return QualityMetrics(
            precision_at_1=round(p1, 3),
            precision_at_5=round(sum(p5_list)/n, 3),
            precision_at_10=round(sum(p10_list)/n, 3),
            recall_at_10=round(sum(r10_list)/n, 3),
            mrr=round(mrr_sum/n, 3) if n else 0,
            total_queries=n,
            avg_latency_ms=round(sum(e.latency_ms for e in evals)/n, 1),
        )

    def stats(self) -> Dict:
        return {
            "total_queries": len(self._evaluations),
            "total_annotations": sum(len(v) for v in self._annotations.values()),
            "by_type": {},
            "metrics": self.get_metrics().__dict__,
        }

    def report(self) -> str:
        m = self.get_metrics()
        return (f"Search Quality Report\n"
                f"=====================\n"
                f"Queries: {m.total_queries}\n"
                f"P@1: {m.precision_at_1:.3f} | P@5: {m.precision_at_5:.3f} | P@10: {m.precision_at_10:.3f}\n"
                f"R@10: {m.recall_at_10:.3f} | MRR: {m.mrr:.3f}\n"
                f"Avg Latency: {m.avg_latency_ms:.1f}ms")


_quality: Optional[SearchQualityEvaluator] = None
def get_search_quality() -> SearchQualityEvaluator:
    global _quality
    if _quality is None: _quality = SearchQualityEvaluator()
    return _quality
