"""Apache AGE Graph Database — Cypher Query Templates."""
from typing import Any, Dict, List, Optional

# Standard Cypher query templates for VIAIOS knowledge graph
QUERY_TEMPLATES = {
    "entity_neighbors": """
        MATCH (n {{id: '{entity_id}'}})-[r]-(m)
        RETURN n.name, type(r), m.name, m.type
        LIMIT {limit}
    """,

    "shortest_path": """
        MATCH p=shortestPath((a {{id: '{from_id}'}})-[*..{max_depth}]-(b {{id: '{to_id}'}}))
        RETURN [n in nodes(p) | n.name] as path, length(p) as hops
    """,

    "entity_by_type": """
        MATCH (n:{entity_type})
        RETURN n.id, n.name, n.properties
        {where_clause}
        LIMIT {limit}
    """,

    "relationship_count": """
        MATCH (a)-[r]->(b)
        RETURN type(r) as relation_type, count(*) as count
        ORDER BY count DESC
    """,

    "subgraph": """
        MATCH (n {{id: '{entity_id}'}})-[r*1..{depth}]-(related)
        RETURN DISTINCT n.name as source, related.name as target, related.type as type
    """,

    "co_occurrence": """
        MATCH (a)-[:APPEARED_AT]->(c:Camera)<-[:APPEARED_AT]-(b)
        WHERE a.id = '{entity_id}'
        RETURN b.name, b.type, count(*) as co_occurrences
        ORDER BY co_occurrences DESC
        LIMIT {limit}
    """,

    "alarm_chain": """
        MATCH (alarm:Alarm)-[:TRIGGERED_AT]->(camera:Camera)
        WHERE alarm.severity = '{severity}' AND alarm.timestamp > '{since}'
        OPTIONAL MATCH (camera)<-[:APPEARED_AT]-(entity)
        RETURN alarm.id, camera.name, collect(entity.name) as related_entities
    """,

    "case_evidence_graph": """
        MATCH (case:Case {{id: '{case_id}'}})-[:CONTAINS]->(evidence:Evidence)
        OPTIONAL MATCH (evidence)-[:RELATES_TO]->(related)
        RETURN evidence.id, evidence.type, collect(related.name) as connections
    """,
}


class GraphQueryBuilder:
    """Builds and executes Cypher queries against Apache AGE."""

    def __init__(self):
        self._query_cache: Dict[str, Any] = {}
        self._demo_data = self._init_demo()

    def _init_demo(self) -> Dict[str, List]:
        return {
            "entity_neighbors": [
                {"source": "Suspect A", "relation": "DRIVES", "target": "Vehicle ABC123", "target_type": "Vehicle"},
                {"source": "Suspect A", "relation": "ACCOMPANIED_BY", "target": "Companion B", "target_type": "Person"},
                {"source": "Suspect A", "relation": "APPEARED_AT", "target": "Camera A3", "target_type": "Camera"},
            ],
            "shortest_path": {"path": ["Suspect A", "Vehicle ABC123", "Gate A", "Case #001"], "hops": 3},
            "relationship_count": [
                {"relation_type": "APPEARED_AT", "count": 25},
                {"relation_type": "DRIVES", "count": 8},
                {"relation_type": "ACCOMPANIED_BY", "count": 12},
                {"relation_type": "INVOLVED_IN", "count": 15},
                {"relation_type": "LOCATED_AT", "count": 20},
            ],
            "co_occurrence": [
                {"name": "Companion B", "type": "Person", "co_occurrences": 5},
                {"name": "Witness C", "type": "Person", "co_occurrences": 3},
            ],
        }

    def execute(self, query_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a named query template with parameters."""
        template = QUERY_TEMPLATES.get(query_name)
        if not template:
            return {"error": f"Unknown query: {query_name}"}

        # In production: execute against AGE via psycopg2 or Neo4j driver
        # For now: return demo data
        cache_key = f"{query_name}:{str(sorted(params.items()))}"
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        result = {
            "query": query_name,
            "params": params,
            "cypher": template.format(**{k: v for k, v in params.items() if k in template}),
            "results": self._demo_data.get(query_name, []),
        }
        self._query_cache[cache_key] = result
        return result

    def list_queries(self) -> List[Dict]:
        return [{"name": k, "params": self._extract_params(v)} for k, v in QUERY_TEMPLATES.items()]

    def _extract_params(self, template: str) -> List[str]:
        import re
        return re.findall(r'\{(\w+)\}', template)


graph_query_builder = GraphQueryBuilder()


# ===== Multi-Tenant Isolation =====

class TenantManager:
    """Multi-tenant data isolation manager."""

    def __init__(self):
        self._tenants: Dict[str, Dict] = {
            "default": {"id": "default", "name": "Default Tenant", "tier": "enterprise",
                        "camera_limit": 1000, "storage_gb": 500, "users": 50},
            "tenant-a": {"id": "tenant-a", "name": "Security Dept A", "tier": "professional",
                         "camera_limit": 100, "storage_gb": 100, "users": 20},
            "tenant-b": {"id": "tenant-b", "name": "Parking Management", "tier": "basic",
                         "camera_limit": 50, "storage_gb": 50, "users": 10},
        }
        self._user_tenants: Dict[str, str] = {"admin": "default"}

    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        return self._tenants.get(tenant_id)

    def list_tenants(self) -> List[Dict]:
        return list(self._tenants.values())

    def get_user_tenant(self, user: str) -> str:
        return self._user_tenants.get(user, "default")

    def check_limit(self, tenant_id: str, resource: str, current: int) -> Dict:
        tenant = self._tenants.get(tenant_id, {})
        limit_map = {"cameras": "camera_limit", "storage": "storage_gb", "users": "users"}
        key = limit_map.get(resource, "")
        limit = tenant.get(key, 100)
        return {
            "tenant": tenant_id, "resource": resource,
            "current": current, "limit": limit,
            "within_limit": current <= limit,
            "usage_percent": round(current / limit * 100, 1) if limit > 0 else 0,
        }


tenant_manager = TenantManager()
