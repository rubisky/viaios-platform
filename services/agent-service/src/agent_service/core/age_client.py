"""
Graph Database Client — Apache AGE with PostgreSQL native fallback.
When AGE extension is unavailable, uses PG adjacency tables (graph_nodes/graph_edges).
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from .production_upgrade import health_monitor, production_cache

logger = logging.getLogger(__name__)

AGE_HOST = os.getenv("AGE_HOST", os.getenv("PG_HOST", "localhost"))
AGE_PORT = int(os.getenv("AGE_PORT", os.getenv("PG_PORT", "5432")))
AGE_DB = os.getenv("AGE_DB", os.getenv("PG_DATABASE", "viaios"))
AGE_USER = os.getenv("AGE_USER", os.getenv("PG_USER", "viaios"))
AGE_PASS = os.getenv("AGE_PASS", os.getenv("PG_PASSWORD", "viaios123"))
AGE_GRAPH = os.getenv("AGE_GRAPH", "viaios_graph")

# PG native tables
NODES_TABLE = "graph_nodes"
EDGES_TABLE = "graph_edges"


class AgeClient:
    """Graph client — tries AGE then falls back to PG native adjacency."""

    def __init__(self):
        self._conn = None
        self._age_available = False
        self._pg_available = False
        self._init_connection()

    def _init_connection(self):
        try:
            import psycopg2
            self._conn = psycopg2.connect(
                host=AGE_HOST, port=AGE_PORT, dbname=AGE_DB,
                user=AGE_USER, password=AGE_PASS, connect_timeout=5)
            self._conn.autocommit = True
            self._pg_available = True
            logger.info("PG connected to %s:%s/%s", AGE_HOST, AGE_PORT, AGE_DB)
            health_monitor.record("pg_connected", 1)

            # Check AGE availability
            try:
                cur = self._conn.cursor()
                cur.execute("SELECT 1 FROM ag_catalog.ag_graph LIMIT 1")
                cur.close()
                self._age_available = True
                logger.info("AGE extension available")
            except Exception:
                self._age_available = False
                logger.info("AGE not available — using PG native graph")
                self._ensure_native_tables()

        except ImportError:
            logger.warning("psycopg2 not installed — graph disabled")
        except Exception as e:
            logger.warning("PG connection failed: %s", e)

    def _ensure_native_tables(self):
        """Create PG native graph tables if not exist."""
        try:
            cur = self._conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {NODES_TABLE} (
                    id VARCHAR(64) PRIMARY KEY, label VARCHAR(64) NOT NULL,
                    properties JSONB DEFAULT '{{}}', created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS {EDGES_TABLE} (
                    id SERIAL PRIMARY KEY, from_id VARCHAR(64) REFERENCES {NODES_TABLE}(id),
                    to_id VARCHAR(64) REFERENCES {NODES_TABLE}(id), rel_type VARCHAR(64) NOT NULL,
                    properties JSONB DEFAULT '{{}}', created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_edges_from ON {EDGES_TABLE}(from_id);
                CREATE INDEX IF NOT EXISTS idx_edges_to ON {EDGES_TABLE}(to_id);
                CREATE INDEX IF NOT EXISTS idx_nodes_label ON {NODES_TABLE}(label);
            """)
            cur.close()
            health_monitor.record("graph_tables_ready", 1)
            logger.info("PG native graph tables ensured")
        except Exception as e:
            logger.error("Failed to create graph tables: %s", e)

    def query(self, cypher: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute graph query — AGE first, PG native fallback."""
        if self._age_available:
            try:
                return self._age_query(cypher, params)
            except Exception as e:
                logger.debug("AGE query failed: %s", e)

        if self._pg_available:
            return self._pg_query(cypher, params)

        return self._local_fallback(cypher, params)

    # === AGE ===

    def _age_query(self, cypher: str, params: Dict = None) -> Dict:
        if not self._conn:
            return {"source": "none", "nodes": [], "edges": [], "paths": []}
        cur = self._conn.cursor()
        try:
            cur.execute(f"LOAD 'age'; SET search_path = ag_catalog, public;")
            cur.execute(f"SELECT * FROM ag_catalog.cypher('{AGE_GRAPH}', %s)", (cypher,))
            rows = cur.fetchall()
            nodes, edges, paths = [], [], []
            for row in rows[:200]:
                result = self._parse_age_vertex(row)
                if result:
                    if result.get("_type") == "vertex":
                        nodes.append(result)
                    elif result.get("_type") == "edge":
                        edges.append(result)
            health_monitor.record("graph_queries", 1)
            return {"source": "age", "nodes": nodes, "edges": edges, "paths": paths, "count": len(rows)}
        finally:
            cur.close()

    def _parse_age_vertex(self, row) -> Optional[Dict]:
        try:
            if isinstance(row, tuple) and len(row) >= 2:
                label = str(row[1]) if row[1] else ""
                props = {}
                if len(row) > 2 and row[2]:
                    try:
                        raw = str(row[2])
                        props = json.loads(raw.replace("::", ":")) if "{" in raw else {"value": raw}
                    except json.JSONDecodeError:
                        pass
                return {
                    "id": str(row[0]) if row[0] else "",
                    "label": label.split("::")[0] if "::" in label else label,
                    "properties": props, "_type": "vertex",
                }
        except Exception:
            pass
        return None

    # === PG Native ===

    def _pg_query(self, cypher: str, params: Dict = None) -> Dict:
        """Translate Cypher-like queries to SQL on PG native tables."""
        cypher_upper = cypher.upper().strip()
        nodes, edges, paths = [], [], []

        try:
            cur = self._conn.cursor()

            # MATCH (n:Label) RETURN n
            label_match = re.search(r'\([^)]*:(\w+)\)', cypher)
            if label_match and ("RETURN" in cypher_upper or not any(k in cypher_upper for k in ["MATCH ()-", "-[", "CREATE"])):
                label = label_match.group(1)
                cur.execute(
                    f"SELECT id, label, properties FROM {NODES_TABLE} WHERE label = %s LIMIT 200",
                    (label,))
                for row in cur.fetchall():
                    nodes.append({
                        "id": row[0], "label": row[1],
                        "properties": row[2] if isinstance(row[2], dict) else {},
                        "_type": "vertex",
                    })

            # MATCH ()-[r:REL]->() RETURN r
            edge_match = re.search(r'\[[^]]*:(\w+)\]', cypher)
            if edge_match:
                rel_type = edge_match.group(1)
                cur.execute(
                    f"SELECT id, from_id, to_id, rel_type, properties FROM {EDGES_TABLE} WHERE rel_type = %s LIMIT 200",
                    (rel_type,))
                for row in cur.fetchall():
                    edges.append({
                        "id": str(row[0]), "from_id": row[1], "to_id": row[2],
                        "label": row[3],
                        "properties": row[4] if isinstance(row[4], dict) else {},
                        "_type": "edge",
                    })

            # MATCH (a)-[*..N]-(b) RETURN path → BFS via recursive CTE
            person_matches = re.findall(r"\((\w+):?\w*\)", cypher)
            if ("SHORTEST" in cypher_upper or "PATH" in cypher_upper) and len(person_matches) >= 2:
                start, end = person_matches[0], person_matches[1]
                depth = 3
                depth_match = re.search(r'\.\.(\d+)', cypher)
                if depth_match:
                    depth = int(depth_match.group(1))
                cur.execute(f"""
                    WITH RECURSIVE path AS (
                        SELECT from_id, to_id, ARRAY[from_id, to_id] AS nodes, 1 AS depth
                        FROM {EDGES_TABLE} WHERE from_id = %s
                        UNION ALL
                        SELECT e.from_id, e.to_id, p.nodes || e.to_id, p.depth + 1
                        FROM {EDGES_TABLE} e JOIN path p ON e.from_id = p.to_id
                        WHERE p.depth < %s AND NOT (e.to_id = ANY(p.nodes))
                    )
                    SELECT DISTINCT nodes[depth] AS node, depth
                    FROM path
                    ORDER BY depth LIMIT 50
                """, (start, depth))
                for row in cur.fetchall():
                    paths.append({"node": row[0], "depth": row[1]})

            # Entity neighbors
            entity_match = re.search(r"\{\s*id:\s*['\"](\w+)['\"]", cypher)
            if entity_match:
                eid = entity_match.group(1)
                cur.execute(f"""
                    SELECT e.rel_type, n.label, n.properties->>'name' AS name
                    FROM {EDGES_TABLE} e
                    JOIN {NODES_TABLE} n ON e.to_id = n.id
                    WHERE e.from_id = %s LIMIT 50
                """, (eid,))
                for row in cur.fetchall():
                    nodes.append({
                        "id": "", "label": "", "rel_type": row[0],
                        "target_label": row[1], "target_name": row[2] or "",
                        "_type": "neighbor",
                    })

            cur.close()
            health_monitor.record("graph_queries", 1)
            return {
                "source": "pg_native",
                "nodes": nodes, "edges": edges, "paths": paths,
                "count": len(nodes) + len(edges) + len(paths),
            }
        except Exception as e:
            logger.error("PG graph query failed: %s", e)
            return {"source": "pg_error", "nodes": [], "edges": [], "paths": [], "error": str(e)}

    def _local_fallback(self, cypher, params=None) -> Dict:
        """Pure Python BFS fallback (no DB)."""
        return {"source": "local_bfs", "nodes": [], "edges": [], "paths": []}

    # === CRUD ===

    def create_entity(self, label: str, properties: Dict[str, Any]) -> Optional[str]:
        eid = properties.get("id") or properties.get("entity_id", "")
        if not eid:
            return None
        if self._pg_available and self._conn:
            try:
                cur = self._conn.cursor()
                cur.execute(
                    f"INSERT INTO {NODES_TABLE} (id, label, properties) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET properties = %s",
                    (eid, label, json.dumps(properties, ensure_ascii=False), json.dumps(properties, ensure_ascii=False)))
                cur.close()
                return eid
            except Exception as e:
                logger.error("Create entity failed: %s", e)
        return None

    def create_relation(self, from_id: str, to_id: str, rel_type: str,
                        properties: Dict[str, Any] = None) -> bool:
        if self._pg_available and self._conn:
            try:
                cur = self._conn.cursor()
                cur.execute(
                    f"INSERT INTO {EDGES_TABLE} (from_id, to_id, rel_type, properties) VALUES (%s, %s, %s, %s)",
                    (from_id, to_id, rel_type, json.dumps(properties or {}, ensure_ascii=False)))
                cur.close()
                return True
            except Exception as e:
                logger.error("Create relation failed: %s", e)
        return False

    def get_stats(self) -> Dict[str, Any]:
        if self._pg_available and self._conn:
            try:
                cur = self._conn.cursor()
                cur.execute(f"SELECT count(*) FROM {NODES_TABLE}")
                nc = cur.fetchone()[0]
                cur.execute(f"SELECT count(*) FROM {EDGES_TABLE}")
                ec = cur.fetchone()[0]
                cur.close()
                return {"source": "pg_native", "nodes": nc, "edges": ec}
            except Exception:
                pass
        return {"source": "none", "nodes": 0, "edges": 0}


age_client = AgeClient()
