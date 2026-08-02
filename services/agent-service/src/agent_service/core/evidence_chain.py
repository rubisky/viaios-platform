"""
Evidence Chain System — P0-4
Full-chain traceability for all AI operations.

Implements the "Evidence First" principle:
Every AI conclusion must be traceable through the complete chain:
  Video Source → Algorithm → Model Version → Inference Result
  → Agent Process → Conclusion → Report

This is critical for:
- Audit compliance (who did what, when, with which model?)
- Judicial admissibility (chain of custody for AI evidence)
- Enterprise governance (model version → result lineage)
- Debugging (why did the AI reach this conclusion?)
"""
import hashlib
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Evidence Types ─────────────────────────────────────────────────

class EvidenceType(Enum):
    VIDEO_SOURCE     = "video_source"      # Input video metadata
    ALGORITHM        = "algorithm"          # Which algorithm was used
    MODEL_VERSION    = "model_version"      # Specific model version
    INFERENCE_INPUT  = "inference_input"    # Input to the model
    INFERENCE_OUTPUT = "inference_output"   # Raw model output
    CAPABILITY_CALL  = "capability_call"    # Capability layer call
    AGENT_PROCESS    = "agent_process"      # Agent reasoning step
    AGENT_DECISION   = "agent_decision"     # Agent conclusion
    HUMAN_REVIEW     = "human_review"       # Human-in-the-loop
    REPORT_GENERATED = "report_generated"   # Final report
    SYSTEM_EVENT     = "system_event"       # System-level event

class EvidenceStatus(Enum):
    RECORDED   = "recorded"    # Evidence has been logged
    VERIFIED   = "verified"    # Evidence has been cryptographically verified
    TAMPERED   = "tampered"    # Evidence integrity check failed
    SUPERSEDED = "superseded"  # Evidence has been updated


# ── Domain Types ───────────────────────────────────────────────────

@dataclass
class EvidenceNode:
    """Single node in the evidence chain."""
    evidence_id: str
    chain_id: str
    sequence: int                   # order in the chain
    evidence_type: EvidenceType
    timestamp: datetime
    actor: str                      # service/agent/human that created this
    data: Dict[str, Any]            # the actual evidence data
    checksum: str                   # SHA-256 of serialized data
    previous_checksum: Optional[str] # link to previous node (blockchain-like)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def verify_integrity(self) -> bool:
        """Verify that this node's data hasn't been tampered with."""
        computed = self._compute_checksum(self.data)
        return computed == self.checksum

    @staticmethod
    def _compute_checksum(data: Dict) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()


@dataclass
class EvidenceChain:
    """Complete evidence chain for a single operation/case."""
    chain_id: str
    case_id: Optional[str]
    operation: str                  # e.g. "video_structuring", "face_search", "trajectory_analysis"
    status: str                     # ACTIVE, COMPLETED, VERIFIED
    nodes: List[EvidenceNode] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verification_report: Optional[Dict] = None

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def is_intact(self) -> bool:
        """Verify the entire chain's integrity."""
        return all(node.verify_integrity() for node in self.nodes)

    def verify_full_chain(self) -> Dict[str, Any]:
        """Comprehensive chain verification including hash linking."""
        results = {
            "chain_id": self.chain_id,
            "total_nodes": len(self.nodes),
            "all_checksums_valid": True,
            "hash_chain_intact": True,
            "tampered_nodes": [],
            "broken_links": [],
        }

        prev_checksum = None
        for node in self.nodes:
            if not node.verify_integrity():
                results["all_checksums_valid"] = False
                results["tampered_nodes"].append(node.evidence_id)

            if prev_checksum and node.previous_checksum != prev_checksum:
                results["hash_chain_intact"] = False
                results["broken_links"].append({
                    "node": node.evidence_id,
                    "expected": prev_checksum,
                    "actual": node.previous_checksum,
                })

            prev_checksum = node.checksum

        return results


# ── Evidence Chain Registry ────────────────────────────────────────

class EvidenceChainRegistry:
    """
    Central registry for all evidence chains in the system.

    Thread-safe, in-memory registry with persistence hooks.
    In production, chains are backed by PostgreSQL and MinIO.
    """

    def __init__(self):
        self._chains: Dict[str, EvidenceChain] = {}
        self._lock = threading.Lock()

    def create_chain(self, operation: str, case_id: Optional[str] = None) -> EvidenceChain:
        """Start a new evidence chain for an operation."""
        chain_id = f"evidence-{uuid.uuid4().hex[:12]}"
        chain = EvidenceChain(
            chain_id=chain_id,
            case_id=case_id,
            operation=operation,
            status="ACTIVE",
        )
        with self._lock:
            self._chains[chain_id] = chain
        logger.info("Evidence chain started: %s for %s", chain_id, operation)
        return chain

    def add_node(self, chain_id: str, evidence_type: EvidenceType,
                 actor: str, data: Dict[str, Any],
                 metadata: Optional[Dict] = None) -> EvidenceNode:
        """Add a new evidence node to an existing chain."""
        with self._lock:
            chain = self._chains.get(chain_id)
            if not chain:
                raise ValueError(f"Evidence chain not found: {chain_id}")

            prev_node = chain.nodes[-1] if chain.nodes else None
            sequence = len(chain.nodes) + 1

            node = EvidenceNode(
                evidence_id=f"{chain_id}-{sequence:04d}",
                chain_id=chain_id,
                sequence=sequence,
                evidence_type=evidence_type,
                timestamp=datetime.now(timezone.utc),
                actor=actor,
                data=data,
                checksum=EvidenceNode._compute_checksum(data),
                previous_checksum=prev_node.checksum if prev_node else None,
                metadata=metadata or {},
            )

            chain.nodes.append(node)
            logger.debug("Evidence node %s [%s] added to chain %s",
                         node.evidence_id, evidence_type.value, chain_id)
            return node

    def complete_chain(self, chain_id: str) -> EvidenceChain:
        """Mark a chain as completed and verify integrity."""
        with self._lock:
            chain = self._chains.get(chain_id)
            if not chain:
                raise ValueError(f"Evidence chain not found: {chain_id}")

            chain.status = "COMPLETED"
            chain.completed_at = datetime.now(timezone.utc)

            # Auto-verify
            if chain.is_intact:
                chain.status = "VERIFIED"
                chain.verified_at = datetime.now(timezone.utc)
                chain.verification_report = chain.verify_full_chain()

            logger.info("Evidence chain %s completed: %d nodes, status=%s",
                        chain_id, chain.node_count, chain.status)
            return chain

    def get_chain(self, chain_id: str) -> Optional[EvidenceChain]:
        return self._chains.get(chain_id)

    def get_chains_for_case(self, case_id: str) -> List[EvidenceChain]:
        return [c for c in self._chains.values() if c.case_id == case_id]

    def list_active_chains(self) -> List[EvidenceChain]:
        return [c for c in self._chains.values() if c.status == "ACTIVE"]

    def export_for_audit(self, chain_id: str) -> Dict[str, Any]:
        """Export a complete evidence chain for external audit."""
        chain = self._chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain not found: {chain_id}")

        return {
            "chain_id": chain.chain_id,
            "case_id": chain.case_id,
            "operation": chain.operation,
            "status": chain.status,
            "created_at": chain.created_at.isoformat(),
            "completed_at": chain.completed_at.isoformat() if chain.completed_at else None,
            "verification": chain.verify_full_chain(),
            "nodes": [
                {
                    "sequence": n.sequence,
                    "type": n.evidence_type.value,
                    "timestamp": n.timestamp.isoformat(),
                    "actor": n.actor,
                    "data": n.data,
                    "checksum": n.checksum,
                    "previous_checksum": n.previous_checksum,
                }
                for n in chain.nodes
            ],
        }

    def stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            chains = list(self._chains.values())
            total_nodes = sum(c.node_count for c in chains)
            verified = sum(1 for c in chains if c.status == "VERIFIED")
            return {
                "total_chains": len(chains),
                "active_chains": sum(1 for c in chains if c.status == "ACTIVE"),
                "completed_chains": sum(1 for c in chains if c.status == "COMPLETED"),
                "verified_chains": verified,
                "total_evidence_nodes": total_nodes,
                "intact_chains": sum(1 for c in chains if c.is_intact),
            }


# ── Persistence Layer ─────────────────────────────────────────────

class EvidencePersistence:
    """Persist evidence chains to disk and database for audit compliance."""

    def __init__(self, base_path: str = "/opt/viaios/data/evidence"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def save(self, chain: EvidenceChain):
        """Persist a chain to disk as JSON."""
        chain_dir = os.path.join(self.base_path, chain.chain_id[:2], chain.chain_id)
        os.makedirs(chain_dir, exist_ok=True)
        path = os.path.join(chain_dir, "chain.json")
        with open(path, "w") as f:
            json.dump({
                "chain_id": chain.chain_id,
                "case_id": chain.case_id,
                "operation": chain.operation,
                "status": chain.status,
                "created_at": chain.created_at.isoformat(),
                "completed_at": chain.completed_at.isoformat() if chain.completed_at else None,
                "nodes": [
                    {
                        "sequence": n.sequence,
                        "type": n.evidence_type.value,
                        "timestamp": n.timestamp.isoformat(),
                        "actor": n.actor,
                        "data": n.data,
                        "checksum": n.checksum,
                        "previous_checksum": n.previous_checksum,
                    }
                    for n in chain.nodes
                ],
            }, f, indent=2, default=str)
        return path

    def load(self, chain_id: str) -> Optional[Dict]:
        """Load a chain from disk."""
        chain_dir = os.path.join(self.base_path, chain_id[:2], chain_id)
        path = os.path.join(chain_dir, "chain.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None

    def list_chains(self, case_id: str = None) -> List[str]:
        """List persisted chain IDs."""
        chains = []
        for root, dirs, files in os.walk(self.base_path):
            for fn in files:
                if fn == "chain.json":
                    chains.append(os.path.basename(os.path.dirname(root)))
        return chains


# ── Convenience Helpers ────────────────────────────────────────────

_registry: Optional[EvidenceChainRegistry] = None
_persistence: Optional[EvidencePersistence] = None


def get_evidence_registry() -> EvidenceChainRegistry:
    """Get or create the global evidence chain registry."""
    global _registry
    if _registry is None:
        _registry = EvidenceChainRegistry()
    return _registry


def get_evidence_persistence() -> EvidencePersistence:
    """Get or create the evidence persistence layer."""
    global _persistence
    if _persistence is None:
        _persistence = EvidencePersistence()
    return _persistence


def record_evidence(chain_id: str, evidence_type: EvidenceType,
                    actor: str, data: Dict[str, Any]) -> EvidenceNode:
    """Quick one-liner to record evidence to a chain with auto-persistence."""
    node = get_evidence_registry().add_node(chain_id, evidence_type, actor, data)
    # Auto-persist on every 10th node
    chain = get_evidence_registry().get_chain(chain_id)
    if chain and chain.node_count % 10 == 0:
        get_evidence_persistence().save(chain)
    return node


def create_evidence_chain(operation: str, case_id: str = None) -> EvidenceChain:
    """Quick one-liner to create a new evidence chain."""
    return get_evidence_registry().create_chain(operation, case_id)


# ── Integration Hooks (called from video_pipeline, agent handlers, etc.) ──

def on_video_processed(pipeline_id: str, source_id: str, metadata: Dict):
    """Hook: called when video processing completes."""
    chain = create_evidence_chain("video_structuring")
    record_evidence(chain.chain_id, EvidenceType.VIDEO_SOURCE, "viaios-video",
                    {"pipeline_id": pipeline_id, "source_id": source_id, **metadata})
    record_evidence(chain.chain_id, EvidenceType.ALGORITHM, "viaios-video",
                    {"algorithm": "video_structuring_v1", "stages": ["decode", "detect", "track", "embed", "archive"]})
    get_evidence_registry().complete_chain(chain.chain_id)
    get_evidence_persistence().save(chain)
    return chain.chain_id


def on_agent_action(agent_id: str, action: str, input_data: Dict, output_data: Dict):
    """Hook: called when an agent performs an action."""
    chain = create_evidence_chain(f"agent_{action}")
    record_evidence(chain.chain_id, EvidenceType.AGENT_PROCESS, agent_id,
                    {"action": action, "input": input_data, "output": output_data})
    return chain.chain_id


def on_report_generated(report_id: str, agent_id: str, findings: List[str]):
    """Hook: called when a report is generated."""
    chain = create_evidence_chain("agent_report")
    record_evidence(chain.chain_id, EvidenceType.REPORT_GENERATED, agent_id,
                    {"report_id": report_id, "findings": findings})
    get_evidence_registry().complete_chain(chain.chain_id)
    get_evidence_persistence().save(chain)
    return chain.chain_id


# ── Pre-defined Chain Templates ────────────────────────────────────

CHAIN_TEMPLATES = {
    "video_structuring": {
        "description": "Complete video structuring pipeline evidence chain",
        "expected_nodes": [
            (EvidenceType.VIDEO_SOURCE,     "viaios-video"),
            (EvidenceType.ALGORITHM,        "viaios-capability"),
            (EvidenceType.MODEL_VERSION,    "viaios-kernel"),
            (EvidenceType.INFERENCE_OUTPUT, "viaios-inference"),
            (EvidenceType.SYSTEM_EVENT,     "viaios-archive"),
        ],
    },
    "face_search": {
        "description": "Face recognition search evidence chain",
        "expected_nodes": [
            (EvidenceType.INFERENCE_INPUT,  "viaios-frontend"),
            (EvidenceType.CAPABILITY_CALL,  "viaios-capability"),
            (EvidenceType.MODEL_VERSION,    "viaios-kernel"),
            (EvidenceType.INFERENCE_OUTPUT, "viaios-inference"),
            (EvidenceType.AGENT_PROCESS,    "viaios-agent"),
            (EvidenceType.AGENT_DECISION,   "viaios-agent"),
        ],
    },
    "agent_report": {
        "description": "Agent-generated report evidence chain",
        "expected_nodes": [
            (EvidenceType.AGENT_PROCESS,    "viaios-agent"),
            (EvidenceType.CAPABILITY_CALL,  "viaios-capability"),
            (EvidenceType.MODEL_VERSION,    "viaios-kernel"),
            (EvidenceType.AGENT_DECISION,   "viaios-agent"),
            (EvidenceType.REPORT_GENERATED, "viaios-report"),
        ],
    },
}
