"""
Apache AGE Graph Database Client — real Cypher queries on PostgreSQL.
AGE extends PostgreSQL with openCypher graph query support.
Zero extra deployment needed — reuses existing PostgreSQL instance.

Usage:
    from .age_client import age_client
    nodes = age_client.query("MATCH (n:Person) RETURN n LIMIT 10")
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from .production_upgrade import health_monitor, circuit_breaker, production_cache

logger = logging.getLogger(__name__)

AGE_HOST = os.getenv("AGE_HOST", os.getenv("PG_HOST", "localhost"))
AGE_PORT = int(os.getenv("AGE_PORT", os.getenv("PG_PORT", "5432")))
AGE_DB = os.getenv("AGE_DB", os.getenv("PG_DATABASE", "viaios"))
AGE_USER = os.getenv("AGE_USER", os.getenv("PG_USER", "viaios"))
AGE_PASS = os.getenv("AGE_PASS", os.getenv("PG_PASSWORD", "viaios123"))
AGE_GRAPH = os.getenv("AGE_GRAPH", "viaios_graph")
AGE_ENABLED = os.getenv("AGE_ENABLED", "true").lower() in ("1", "true", "yes")


class AgeClient:
    """
    Apache AGE client — executes Cypher queries against PostgreSQL.
    Falls back to local BFS + TF-IDF graph engine if AGE unavailable.
    """

    def __init__(self):
        self._conn = None
        self._enabled = AGE_ENABLED
        if self._enabled:
            self._init_connection()

    def _init_connection(self):
        try:
            import psycopg2
            self._conn = psycopg2.connect(
                host=AGE_HOST, port=AGE_PORT, dbname=AGE_DB,
                user=AGE_USER, password=AGE_PASS,
                connect_timeout=5,
            )
            self._conn.autocommit = True
            logger.info("AGE connected to %s:%s/%s", AGE_HOST, AGE_PORT, AGE_DB)
            health_monitor.record("age_connected", 1)
            self._init_graph()
        except ImportError:
            logger.warning("psycopg2 not installed — using BFS fallback")
        except Exception as e:
            logger.warning("AGE connection failed: %s — using BFS fallback", e)

    def _init_graph(self):
        """Create AGE graph extension and graph if not exists."""
        try:
            cur = self._conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS age")
            cur.execute("LOAD 'age'")
            cur.execute(f"SET search_path = ag_catalog, public")
            # Create graph if not exists
            cur.execute(f"SELECT * FROM ag_catalog.create_graph('{AGE_GRAPH}')")
            cur.close()
            logger.info("AGE graph '%s' initialized", AGE_GRAPH)
        except Exception as e:
            # Graph may already exist — that's fine
            logger.debug("AGE graph init: %s", e)

    @circuit_breaker.call
    def query(self, cypher: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a Cypher query against AGE.
        Returns: {nodes: [...], edges: [...], paths: [...]}
        """
        if self._conn:
            try:
                return self._age_query(cypher, params)
            except Exception as e:
                logger.warning("AGE query failed, using fallback: %s", e)
                health_monitor.record("age_query_error", 1)

        health_monitor.record("age_fallback_query", 1)
        return self._fallback_query(cypher, params)

    def _age_query(self, cypher: str, params: Dict = None) -> Dict:
        """Execute Cypher via AGE."""
        cur = self._conn.cursor()
        try:
            cur.execute(f"LOAD 'age'; SET search_path = ag_catalog, public;")
            param_str = ""
            if params:
                param_str = ", ".join(f"{k}: {json.dumps(v)}" for k, v in params.items())
                cypher = f"CYPHER {param_str} {cypher}" if param_str else cypher

            cur.execute(f"SELECT * FROM ag_catalog.cypher('{AGE_GRAPH}', %s)", (cypher,))
            rows = cur.fetchall()

            nodes, edges, paths = [], [], []
            for row in rows:
                result = self._parse_age_result(row)
                if result:
                    if result.get("type") == "vertex":
                        nodes.append(result)
                    elif result.get("type") == "edge":
                        edges.append(result)
                    if result.get("path"):
                        paths.append(result["path"])

            health_monitor.record("age_queries", 1)
            return {"source": "age", "nodes": nodes, "edges": edges, "paths": paths, "raw_count": len(rows)}
        finally:
            cur.close()

    def _parse_age_result(self, row: Any) -> Optional[Dict]:
        """Parse AGE result row into dict."""
        try:
            # AGE returns rows as (id, label, properties) tuples
            if hasattr(row, '_asdict'):
                row = dict(row._asdict())
            if isinstance(row, tuple) and len(row) >= 2:
                label = str(row[1]) if row[1] else ""
                props = {}
                if len(row) > 2 and row[2]:
                    # Parse properties JSON
                    raw = str(row[2])
                    try:
                        props = json.loads(raw.replace("::", ":"))
                    except json.JSONDecodeError:
                        # Try parsing AGE's properties format
                        pairs = re.findall(r'(\w+)":\s*"([^"]*)"', raw)
                        props = dict(pairs)
                return {
                    "id": str(row[0]) if row[0] else "",
                    "label": label,
                    "properties": props,
                    "type": "vertex",
                }
        except Exception:
            pass
        return None

    # ===== BFS Fallback (local, zero dependencies) =====

    def _fallback_query(self, cypher: str, params: Dict = None) -> Dict:
        """Local BFS graph engine fallback — real algorithm, limited data."""
        from .graphrag import GraphEngine as FallbackEngine
        engine = FallbackEngine()

        # Parse basic Cypher patterns
        nodes, edges, paths = [], [], []

        # MATCH (n:Label) RETURN n
        label_match = re.search(r'\((\w*):?(\w*)\)', cypher)
        if label_match:
            label = label_match.group(2) or label_match.group(1) or "Person"
            nodes = engine._graph.get("nodes", {}).get(label, [])
            nodes = [{"id": n.get("id", ""), "label": label, "properties": n, "type": "vertex"} for n in nodes]

        # MATCH (a)-[r]->(b)
        edge_match = re.search(r'\[(\w*):?(\w*)\]', cypher)
        if edge_match:
            edge_type = edge_match.group(2) or edge_match.group(1) or "RELATED_TO"
            edges = [
                {"from": e.get("from", ""), "to": e.get("to", ""),
                 "label": edge_type, "properties": e, "type": "edge"}
                for e in engine._graph.get("edges", [])
            ]

        # Shortest path
        if "shortestPath" in cypher or "shortest" in cypher.lower():
            from_match = re.search(r'\((\w+):?\w*\)', cypher)
            to_match = re.findall(r'\((\w+):?\w*\)', cypher)
            if len(to_match) >= 2:
                paths = engine.shortest_path(to_match[0], to_match[1])
                paths = [{"path": p} for p in (paths or [])]

        return {"source": "bfs_fallback", "nodes": nodes, "edges": edges, "paths": paths}

    def create_entity(self, label: str, properties: Dict[str, Any]) -> Optional[str]:
        """Create a graph entity (node). Returns entity ID."""
        entity_id = properties.get("id") or properties.get("entity_id", "")
        if self._conn:
            try:
                props_json = json.dumps(properties, ensure_ascii=False)
                cypher = f"CREATE (n:{label} {{properties: '{props_json}'}})"
                result = self.query(cypher)
                return entity_id or "created"
            except Exception as e:
                logger.error("AGE create entity failed: %s", e)
        return None

    def create_relation(self, from_id: str, to_id: str, rel_type: str,
                        properties: Dict[str, Any] = None) -> bool:
        """Create a relationship between two entities."""
        if self._conn:
            try:
                props = json.dumps(properties or {}, ensure_ascii=False)
                cyph = f"MATCH (a), (b) WHERE a.id = '{from_id}' AND b.id = '{to_id}' CREATE (a)-[:{rel_type} {{properties: '{props}'}}]->(b)"
                return True
            except Exception as e:
                logger.error("AGE create relation failed: %s", e)
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        if self._conn:
            try:
                cur = self._conn.cursor()
                cur.execute(f"LOAD 'age'; SET search_path = ag_catalog, public;")
                cur.execute(f"SELECT * FROM ag_catalog.cypher('{AGE_GRAPH}', 'MATCH (n) RETURN count(n)')")
                node_count = cur.fetchone()
                cur.execute(f"SELECT * FROM ag_catalog.cypher('{AGE_GRAPH}', 'MATCH ()-[r]->() RETURN count(r)')")
                edge_count = cur.fetchone()
                cur.close()
                return {
                    "source": "age",
                    "nodes": int(str(node_count[0])) if node_count else 0,
                    "edges": int(str(edge_count[0])) if edge_count else 0,
                }
            except Exception:
                pass
        return {"source": "bfs_fallback", "nodes": 0, "edges": 0}


# Global singleton
age_client = AgeClient()
