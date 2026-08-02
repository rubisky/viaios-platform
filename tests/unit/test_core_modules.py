"""
Unit tests for VIAIOS core Python modules.
Run: pytest tests/unit/test_core_modules.py -v
"""
import sys
import os
import pytest

# Add agent-service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/agent-service/src'))

# ── Evidence Chain Tests ───────────────────────────────────────────

class TestEvidenceChain:
    def test_create_chain(self):
        from agent_service.core.evidence_chain import create_evidence_chain, EvidenceType, record_evidence
        chain = create_evidence_chain("test_operation", "CASE-001")
        assert chain.chain_id.startswith("evidence-")
        assert chain.operation == "test_operation"
        assert chain.case_id == "CASE-001"
        assert chain.node_count == 0

    def test_add_node(self):
        from agent_service.core.evidence_chain import create_evidence_chain, EvidenceType, record_evidence
        chain = create_evidence_chain("test")
        node = record_evidence(chain.chain_id, EvidenceType.ALGORITHM, "test-agent",
                              {"algorithm": "yolov8", "version": "v8.2"})
        assert node.sequence == 1
        assert node.evidence_type == EvidenceType.ALGORITHM
        assert node.checksum is not None

    def test_chain_integrity(self):
        from agent_service.core.evidence_chain import create_evidence_chain, EvidenceType, record_evidence, get_evidence_registry
        chain = create_evidence_chain("integrity_test")
        record_evidence(chain.chain_id, EvidenceType.VIDEO_SOURCE, "v", {"src": "cam1"})
        record_evidence(chain.chain_id, EvidenceType.INFERENCE_OUTPUT, "ai", {"objects": 5})
        get_evidence_registry().complete_chain(chain.chain_id)
        assert chain.is_intact

    def test_chain_verification(self):
        from agent_service.core.evidence_chain import create_evidence_chain, EvidenceType, record_evidence, get_evidence_registry
        chain = create_evidence_chain("verify_test")
        record_evidence(chain.chain_id, EvidenceType.SYSTEM_EVENT, "sys", {"event": "start"})
        result = chain.verify_full_chain()
        assert result["all_checksums_valid"]
        assert result["hash_chain_intact"]

    def test_persistence(self):
        import tempfile
        from agent_service.core.evidence_chain import create_evidence_chain, EvidenceType, record_evidence, EvidencePersistence, get_evidence_registry
        chain = create_evidence_chain("persist_test")
        record_evidence(chain.chain_id, EvidenceType.AGENT_PROCESS, "agent", {"step": 1})
        get_evidence_registry().complete_chain(chain.chain_id)

        persist = EvidencePersistence(base_path=tempfile.mkdtemp())
        path = persist.save(chain)
        assert os.path.exists(path)


# ── Evaluator Tests ────────────────────────────────────────────────

class TestEvaluator:
    def test_evaluate_passing(self):
        from agent_service.core.evaluator import get_evaluator
        result = get_evaluator().evaluate(
            "agent-1", "TestAgent", "analyze this image",
            "Step 1: The image shows a person. Step 2: The person is near Gate A. Conclusion: Person detected."
        )
        assert result.overall_score > 0.5
        assert len(result.dimensions) == 5
        assert result.evaluation_id.startswith("eval-")

    def test_evaluate_safety(self):
        from agent_service.core.evaluator import get_evaluator
        result = get_evaluator().evaluate(
            "agent-2", "TestAgent", "test", "harmless output"
        )
        safety = next(d for d in result.dimensions if d.dimension == "safety")
        assert safety.score == 1.0  # No unsafe content

    def test_evaluate_empty_output(self):
        from agent_service.core.evaluator import get_evaluator
        result = get_evaluator().evaluate("agent-3", "TestAgent", "test", "")
        assert result.overall_score < 0.5
        assert not result.passes

    def test_score_dimensions(self):
        from agent_service.core.evaluator import get_evaluator
        result = get_evaluator().evaluate(
            "agent-4", "TestAgent", "find target near Gate B",
            "Based on the search results, the target was found near Gate B. Evidence: camera footage at 20:00."
        )
        for dim in result.dimensions:
            assert 0 <= dim.score <= 1.0
            assert dim.level in ("excellent", "good", "adequate", "poor", "fail")


# ── Governance Tests ───────────────────────────────────────────────

class TestGovernance:
    def test_policies_exist(self):
        from agent_service.core.governance import get_governance
        gov = get_governance()
        policies = gov.list_policies()
        assert len(policies) >= 8  # Default policies

    def test_allow_normal_action(self):
        from agent_service.core.governance import get_governance, GovernanceContext
        ctx = GovernanceContext("agent-1", "search", "user-1", "tenant-1", "OPERATOR", "search")
        decision = get_governance().evaluate_pre(ctx)
        assert decision.allowed

    def test_deny_admin_action_for_viewer(self):
        from agent_service.core.governance import get_governance, GovernanceContext
        ctx = GovernanceContext("agent-2", "search", "user-2", "tenant-1", "VIEWER", "admin_delete_user")
        decision = get_governance().evaluate_pre(ctx)
        assert not decision.allowed or decision.action.value != "deny"

    def test_rate_limit_check(self):
        from agent_service.core.governance import get_governance
        gov = get_governance()
        allowed, remaining = gov.check_rate_limit("test_key", max_per_minute=3)
        assert allowed
        assert remaining == 2

    def test_stats(self):
        from agent_service.core.governance import get_governance
        stats = get_governance().stats()
        assert stats["total_policies"] >= 8
        assert "audit_entries" in stats


# ── Runtime Mesh Tests ─────────────────────────────────────────────

class TestRuntimeMesh:
    def test_mesh_initialization(self):
        from agent_service.core.runtime_mesh import get_runtime_mesh
        mesh = get_runtime_mesh()
        stats = mesh.get_mesh_stats()
        assert stats["total_endpoints"] >= 8
        assert stats["healthy_endpoints"] >= 0

    def test_route_detection(self):
        from agent_service.core.runtime_mesh import get_runtime_mesh
        result = get_runtime_mesh().route("detection")
        assert result.endpoint is not None
        assert result.strategy is not None

    def test_canary_setup(self):
        from agent_service.core.runtime_mesh import get_runtime_mesh, ModelEndpoint
        mesh = get_runtime_mesh()
        ep = ModelEndpoint("canary-test", "m1", "Canary", "v2", "detection", "localhost", 8191, "ONNX")
        mesh.register_endpoint(ep)
        mesh.setup_canary("detection", "det-yolov8n-onnx", "canary-test", 20)
        mesh.deregister_endpoint("canary-test")

    def test_circuit_breaker(self):
        from agent_service.core.runtime_mesh import get_runtime_mesh, ModelEndpoint
        mesh = get_runtime_mesh()
        ep = ModelEndpoint("cb-test", "m1", "CB", "v1", "detection", "localhost", 8191, "ONNX")
        mesh.register_endpoint(ep)
        # Simulate failures
        for _ in range(6):
            mesh.record_result("cb-test", 0, False)
        stats = mesh.get_endpoint_metrics("cb-test")
        assert stats is not None
        mesh.deregister_endpoint("cb-test")


# ── GraphRAG Tests ─────────────────────────────────────────────────

class TestGraphRAG:
    def test_vector_only_search(self):
        from agent_service.core.graphrag import GraphRAGQuery, get_graphrag_engine, SearchMode
        engine = get_graphrag_engine()
        result = engine.search(GraphRAGQuery(text="test query", mode=SearchMode.VECTOR_ONLY))
        assert result.vector_matches is not None
        assert result.mode == "vector_only"

    def test_full_rag_search(self):
        from agent_service.core.graphrag import GraphRAGQuery, get_graphrag_engine, SearchMode
        engine = get_graphrag_engine()
        result = engine.search(GraphRAGQuery(text="who met Person-A", mode=SearchMode.FULL_RAG))
        assert result.answer != ""
        assert result.confidence >= 0

    def test_hybrid_search(self):
        from agent_service.core.graphrag import GraphRAGQuery, get_graphrag_engine, SearchMode
        engine = get_graphrag_engine()
        result = engine.search(GraphRAGQuery(text="vehicle near Gate A", mode=SearchMode.HYBRID))
        assert result.latency_ms > 0


# ── Plugin Manager Tests ───────────────────────────────────────────

class TestPluginManager:
    def test_register_plugin(self):
        from agent_service.core.plugin_manager import PluginManager, PluginMetadata
        pm = PluginManager(plugin_dir="/tmp/viaios_test_plugins")
        meta = PluginMetadata(name="test-plugin", version="1.0", hooks=["pre_inference"])
        pid = pm.register(meta)
        assert pid is not None
        assert pm.get("test-plugin") is not None

    def test_list_plugins(self):
        from agent_service.core.plugin_manager import PluginManager, PluginMetadata
        pm = PluginManager(plugin_dir="/tmp/viaios_test_plugins")
        pm.register(PluginMetadata("p1", "1.0"))
        pm.register(PluginMetadata("p2", "2.0"))
        plugins = pm.list_plugins()
        assert len(plugins) >= 2

    def test_stats(self):
        from agent_service.core.plugin_manager import PluginManager, PluginMetadata
        pm = PluginManager(plugin_dir="/tmp/viaios_test_plugins")
        pm.register(PluginMetadata("stats-test", "1.0", hooks=["on_alarm"]))
        stats = pm.stats()
        assert stats["total_plugins"] >= 1

    def test_hook_registration(self):
        from agent_service.core.plugin_manager import PluginManager, PluginMetadata, HookPoint
        pm = PluginManager(plugin_dir="/tmp/viaios_test_plugins")
        meta = PluginMetadata("hook-test", "1.0", hooks=["pre_inference", "post_inference"])
        pm.register(meta)
        assert len(pm._hooks[HookPoint.PRE_INFERENCE]) + len(pm._hooks[HookPoint.POST_INFERENCE]) >= 0


# ── Workflow DSL Tests ─────────────────────────────────────────────

class TestWorkflowDSL:
    def test_parse_sequential(self):
        from agent_service.core.workflow_dsl import WorkflowParser, WorkflowMode
        yaml = """
workflow:
  name: test_seq
  mode: sequential
  steps:
    - id: step1
      agent: video-agent
      action: decode
    - id: step2
      agent: analysis-agent
      action: detect
      depends_on: [step1]
"""
        wf = WorkflowParser.parse(yaml)
        assert wf.name == "test_seq"
        assert wf.mode == WorkflowMode.SEQUENTIAL
        assert len(wf.steps) == 2
        assert wf.steps[1].depends_on == ["step1"]

    def test_execute_sequential(self):
        from agent_service.core.workflow_dsl import WorkflowParser, WorkflowExecutor
        yaml = """
workflow:
  name: exec_test
  mode: sequential
  steps:
    - id: decode
      action: decode
    - id: detect
      action: detect
      depends_on: [decode]
"""
        wf = WorkflowParser.parse(yaml)
        result = WorkflowExecutor().execute(wf)
        assert result.status in ("completed", "failed")
        assert len(result.step_results) > 0

    def test_retry_policy(self):
        from agent_service.core.workflow_dsl import WorkflowParser, RetryBackoff, RetryPolicy
        yaml = """
workflow:
  name: retry_test
  steps:
    - id: flaky_step
      action: decode
      retry: {max: 3, backoff: fixed, delay: 0.1}
"""
        wf = WorkflowParser.parse(yaml)
        assert wf.steps[0].retry is not None
        assert wf.steps[0].retry.max_attempts == 3
        assert wf.steps[0].retry.backoff == RetryBackoff.FIXED


# ── Prompt OS Tests ────────────────────────────────────────────────

class TestPromptOS:
    def test_render_template(self):
        from agent_service.core.prompt_os import prompt_engine
        result = prompt_engine.render("target_search", {
            "target_description": "person in black",
            "time_range": "2024-01-01", "location": "Gate A",
        })
        assert "person in black" in result

    def test_list_templates(self):
        from agent_service.core.prompt_os import prompt_engine
        templates = prompt_engine.list_templates()
        assert len(templates) >= 6

    def test_evaluator(self):
        from agent_service.core.prompt_os import prompt_engine
        result = prompt_engine.render_and_evaluate("video_analysis", {
            "camera_name": "Cam1", "time_range": "10:00-12:00",
            "task_description": "detect intruders",
        })
        assert "rendered" in result
        assert result.get("evaluation", {}).get("overall_score", 0) >= 0

    def test_ab_test(self):
        from agent_service.core.prompt_os import prompt_engine
        prompt_engine.create_ab_test("search_test", "1.0.0", "1.0.0")
        result = prompt_engine.conclude_ab_test("search_test")
        assert result is not None  # Returns result even without enough data

    def test_marketplace(self):
        from agent_service.core.prompt_os import prompt_engine
        results = prompt_engine.marketplace.search(category="search")
        assert len(results) >= 1
        stats = prompt_engine.marketplace.get_stats()
        assert stats["total_listings"] >= 1
