"""GraphRAG Engine — Vector Search + Graph Traversal + LLM Fusion."""
import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: str; type: str; name: str; properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphEdge:
    from_id: str; to_id: str; type: str

@dataclass
class SearchResult:
    source: str  # "vector", "graph", "llm"
    entity: Optional[GraphNode] = None
    path: Optional[List[Tuple[str, str, str]]] = None  # (from, relation, to)
    score: float = 0.0
    explanation: str = ""


class VectorEngine:
    """Simple TF-IDF vector similarity (upgrade to Milvus in production)."""

    def __init__(self):
        self._documents: Dict[str, Dict[str, Any]] = {}  # entity_id -> {text, vector}
        self._vocabulary: Set[str] = set()

    def index_entity(self, node: GraphNode):
        """Index an entity for vector search."""
        text = f"{node.name} {node.type} {' '.join(str(v) for v in node.properties.values())}"
        words = self._tokenize(text)
        self._vocabulary.update(words)
        tf = defaultdict(int)
        for w in words: tf[w] += 1
        self._documents[node.id] = {"node": node, "text": text, "tf": dict(tf)}

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Cosine similarity search."""
        query_words = self._tokenize(query)
        if not query_words:
            return []
        q_tf = defaultdict(int)
        for w in query_words: q_tf[w] += 1
        scores = []
        for doc_id, doc in self._documents.items():
            score = self._cosine_sim(q_tf, doc["tf"], doc_id)
            if score > 0:
                scores.append(SearchResult(
                    source="vector", entity=doc["node"],
                    score=score, explanation=f"Keyword match: {score:.2f}"))
        scores.sort(key=lambda x: -x.score)
        return scores[:top_k]

    def _cosine_sim(self, q_tf: dict, d_tf: dict, doc_id: str) -> float:
        dot = sum(q_tf.get(w, 0) * d_tf.get(w, 0) for w in set(q_tf) | set(d_tf))
        q_norm = math.sqrt(sum(v ** 2 for v in q_tf.values())) or 1
        d_norm = math.sqrt(sum(v ** 2 for v in d_tf.values())) or 1
        return dot / (q_norm * d_norm)


class GraphEngine:
    """Graph traversal engine."""

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # node_id -> [(target_id, edge_type)]

    def add_node(self, node: GraphNode):
        self._nodes[node.id] = node

    def add_edge(self, edge: GraphEdge):
        self._edges.append(edge)
        self._adjacency[edge.from_id].append((edge.to_id, edge.type))
        self._adjacency[edge.to_id].append((edge.from_id, edge.type))

    def get_neighbors(self, node_id: str, max_depth: int = 2) -> List[SearchResult]:
        """BFS traversal from a node."""
        results = []
        visited = {node_id}
        queue = [(node_id, 0, [])]
        while queue:
            current, depth, path = queue.pop(0)
            if depth >= max_depth: continue
            for target_id, edge_type in self._adjacency.get(current, []):
                if target_id in visited: continue
                visited.add(target_id)
                new_path = path + [(current, edge_type, target_id)]
                target_node = self._nodes.get(target_id)
                if target_node:
                    results.append(SearchResult(
                        source="graph", entity=target_node,
                        path=new_path, score=1.0 / (depth + 1),
                        explanation=f"Connected via {edge_type} (depth {depth + 1})"))
                queue.append((target_id, depth + 1, new_path))
        return results

    def find_path(self, from_id: str, to_id: str, max_depth: int = 4) -> Optional[List[Tuple[str, str, str]]]:
        """BFS shortest path between two nodes."""
        if from_id not in self._nodes or to_id not in self._nodes:
            return None
        visited = {from_id}
        queue = [(from_id, [])]
        while queue:
            current, path = queue.pop(0)
            if len(path) >= max_depth: continue
            for target_id, edge_type in self._adjacency.get(current, []):
                if target_id in visited: continue
                new_path = path + [(current, edge_type, target_id)]
                if target_id == to_id: return new_path
                visited.add(target_id)
                queue.append((target_id, new_path))
        return None


class GraphRAGEngine:
    """Fusion engine: Vector Search + Graph Traversal + LLM Reasoning."""

    def __init__(self, llm_provider=None):
        self.vector = VectorEngine()
        self.graph = GraphEngine()
        self.llm = llm_provider

    def load_data(self, entities: List[dict], edges: List[dict]):
        """Load entity and edge data from the knowledge service."""
        for e in entities:
            node = GraphNode(id=e.get("id", ""), type=e.get("type", "Unknown"),
                             name=e.get("name", ""), properties=e.get("properties", {}))
            self.graph.add_node(node)
            self.vector.index_entity(node)
        for ed in edges:
            edge = GraphEdge(from_id=ed.get("from", ""), to_id=ed.get("to", ""), type=ed.get("type", ""))
            self.graph.add_edge(edge)
        logger.info("GraphRAG loaded: %d nodes, %d edges", len(entities), len(edges))

    def query(self, question: str, top_k: int = 5, use_llm: bool = True) -> Dict[str, Any]:
        """Unified query: run all three engines and fuse results."""
        vector_results = self.vector.search(question, top_k)
        graph_results = []
        # For each vector result, also get its graph neighbors
        for vr in vector_results:
            if vr.entity:
                neighbors = self.graph.get_neighbors(vr.entity.id, max_depth=2)
                graph_results.extend(neighbors)

        # Deduplicate
        seen = set(); unique_graph = []
        for gr in graph_results:
            eid = gr.entity.id if gr.entity else ""
            if eid not in seen and eid: seen.add(eid); unique_graph.append(gr)

        # Find paths between top entities
        paths = []
        entity_ids = [vr.entity.id for vr in vector_results[:3] if vr.entity]
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                path = self.graph.find_path(entity_ids[i], entity_ids[j])
                if path: paths.append({"from": entity_ids[i], "to": entity_ids[j], "path": path})

        # LLM synthesis
        synthesis = ""
        if use_llm and self.llm:
            synthesis = self._synthesize(question, vector_results[:3], unique_graph[:5], paths)

        return {
            "question": question,
            "vector_results": [{"entity": r.entity.name if r.entity else "", "type": r.entity.type if r.entity else "", "score": round(r.score, 3), "explanation": r.explanation} for r in vector_results],
            "graph_results": [{"entity": r.entity.name if r.entity else "", "relation_path": " → ".join(f"{f}-[{t}]->{to}" for f, t, to in (r.path or [])) if r.path else "", "score": round(r.score, 3)} for r in unique_graph[:5]],
            "paths": paths,
            "synthesis": synthesis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _synthesize(self, question: str, vec_results: List[SearchResult],
                    graph_results: List[SearchResult], paths: List[dict]) -> str:
        """Use LLM to synthesize a coherent answer."""
        context_parts = []
        for r in vec_results:
            if r.entity: context_parts.append(f"Entity: {r.entity.name} ({r.entity.type}) - match: {r.explanation}")
        for r in graph_results[:3]:
            if r.entity:
                path_str = " → ".join(f"{f}({t})" for f, t, _ in (r.path or [])) if r.path else "direct"
                context_parts.append(f"Related: {r.entity.name} via {path_str}")
        context = "; ".join(context_parts[:6])
        # Rule-based synthesis as fallback
        if vec_results:
            top = vec_results[0]
            direct = [r.entity.name for r in graph_results[:3] if r.entity]
            return f"Based on analysis: {top.entity.name if top.entity else 'Unknown'} is directly relevant. Related entities: {', '.join(direct) if direct else 'none found'}. Context: {context[:200]}"
        return f"No relevant entities found for: {question}"

    def stats(self) -> dict:
        return {"nodes": len(self.graph._nodes), "edges": len(self.graph._edges), "indexed": len(self.vector._documents)}


# Global singleton
graphrag_engine = GraphRAGEngine()
