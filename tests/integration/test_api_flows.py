"""
VIAIOS Integration Tests — End-to-end API flow validation.
Run: pytest tests/integration/test_api_flows.py -v
Requires: Server running at VIAIOS_TEST_URL (default: http://ry3.9gpu.com:18006)
"""
import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = os.getenv("VIAIOS_TEST_URL", "http://ry3.9gpu.com:18006")
ADMIN_USER = os.getenv("VIAIOS_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("VIAIOS_ADMIN_PASS", "changeme")

# Add agent-service to path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/agent-service/src'))


class TestAuthFlow:
    """Test: Login → Token → Authenticated API access"""

    def test_login(self):
        data = json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}).encode()
        req = urllib.request.Request(f"{BASE_URL}/api/v1/auth/login", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=10)
        assert resp.getcode() == 200
        body = json.loads(resp.read())
        assert "accessToken" in body
        assert body["role"] == "ADMIN"

    def test_login_invalid(self):
        data = json.dumps({"username": "noone", "password": "wrong"}).encode()
        req = urllib.request.Request(f"{BASE_URL}/api/v1/auth/login", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=10)
            assert False, "Should have failed"
        except urllib.error.HTTPError as e:
            assert e.code in (400, 401, 500)


class TestHealthCheck:
    """Test: All health endpoints respond"""

    def test_gateway_health(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/actuator/health", timeout=5)
        assert resp.getcode() == 200

    def test_frontend(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/", timeout=5)
        assert resp.getcode() == 200


class TestKernelAPI:
    """Test: AI Kernel endpoints"""

    def test_kernel_health(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/kernel/health", timeout=10)
        assert resp.getcode() == 200
        body = json.loads(resp.read())
        assert body["kernel"] == "VIAIOS AI Kernel 4.0"
        assert body["totalManagers"] == 11

    def test_kernel_capabilities(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/kernel/capabilities", timeout=10)
        assert resp.getcode() == 200
        body = json.loads(resp.read())
        assert body["total"] >= 16

    def test_kernel_models(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/kernel/models", timeout=10)
        assert resp.getcode() == 200
        body = json.loads(resp.read())
        assert body["total"] >= 10


class TestVideoAPI:
    """Test: Video service endpoints"""

    def test_video_health(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/video/stats", timeout=10)
        assert resp.getcode() == 200


class TestEvidenceAPI:
    """Test: Evidence chain endpoints"""

    def test_evidence_stats(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/evidence/stats", timeout=10)
        assert resp.getcode() == 200


class TestGovernanceAPI:
    """Test: Governance endpoints"""

    def test_governance_policies(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/governance/policies", timeout=10)
        assert resp.getcode() == 200
        body = json.loads(resp.read())
        assert body["policies"] is not None

    def test_governance_stats(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/governance/stats", timeout=10)
        assert resp.getcode() == 200


class TestGB28181API:
    """Test: GB28181 endpoints"""

    def test_gb_stats(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/cameras/gb28181/stats", timeout=10)
        assert resp.getcode() == 200


class TestTritonAPI:
    """Test: Triton client endpoints"""

    def test_triton_health(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/triton/health", timeout=10)
        assert resp.getcode() == 200


class TestMeshAPI:
    """Test: Runtime Mesh endpoints"""

    def test_mesh_stats(self):
        resp = urllib.request.urlopen(f"{BASE_URL}/api/v1/mesh/stats", timeout=10)
        assert resp.getcode() == 200
        body = json.loads(resp.read())
        assert body["total_endpoints"] >= 0


class TestEndToEndFlow:
    """Test: Complete user flow — Login → Search → Evidence"""

    def test_full_flow(self):
        # 1. Login
        data = json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}).encode()
        req = urllib.request.Request(f"{BASE_URL}/api/v1/auth/login", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=10)
        token = json.loads(resp.read())["accessToken"]
        auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 2. Search (requires auth)
        data2 = json.dumps({"query": "test query", "mode": "hybrid"}).encode()
        req2 = urllib.request.Request(f"{BASE_URL}/api/v1/graphrag/search", data=data2,
            headers=auth, method="POST")
        resp2 = urllib.request.urlopen(req2, timeout=15)
        assert resp2.getcode() == 200
        assert "answer" in json.loads(resp2.read())

        # 3. Evidence chain
        req3 = urllib.request.Request(f"{BASE_URL}/api/v1/evidence/stats",
            headers=auth)
        resp3 = urllib.request.urlopen(req3, timeout=10)
        assert resp3.getcode() == 200

        # 4. Governance audit
        req4 = urllib.request.Request(f"{BASE_URL}/api/v1/governance/stats",
            headers=auth)
        resp4 = urllib.request.urlopen(req4, timeout=10)
        assert resp4.getcode() == 200
