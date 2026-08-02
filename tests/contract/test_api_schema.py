"""
VIAIOS API Contract Tests — P4-3
Validates all API responses against expected schemas.
Run: pytest tests/contract/test_api_schema.py -v
"""
import json
import os
import sys
import urllib.request

BASE = os.getenv("VIAIOS_TEST_URL", "http://ry3.9gpu.com:18006")
ADMIN_USER = os.getenv("VIAIOS_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("VIAIOS_ADMIN_PASS", "changeme")

def login():
    data = json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/auth/login", data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    return resp["accessToken"]

TOKEN = login()
AUTH = {"Authorization": f"Bearer {TOKEN}"}

def get(path, auth=True):
    h = {**AUTH} if auth else {}
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{BASE}{path}", headers=h), timeout=10).read())

def post(path, body, auth=True):
    h = {**(AUTH if auth else {}), "Content-Type": "application/json"}
    data = json.dumps(body).encode()
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method="POST"), timeout=10).read())


class TestAuthContract:
    def test_login_response_schema(self):
        data = json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}).encode()
        req = urllib.request.Request(f"{BASE}/api/v1/auth/login", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=10).read())
        assert "accessToken" in r
        assert "refreshToken" in r
        assert r["role"] == "ADMIN"
        assert isinstance(r["expiresIn"], int)

class TestKernelContract:
    def test_health_schema(self):
        r = get("/api/v1/kernel/health", auth=False)
        assert r["kernel"].startswith("VIAIOS")
        assert isinstance(r["totalManagers"], int)
        assert isinstance(r["managers"], dict)
        assert len(r["managers"]) == 11

    def test_capabilities_schema(self):
        r = get("/api/v1/kernel/capabilities", auth=False)
        assert isinstance(r["total"], int)
        assert isinstance(r["capabilities"], list)
        for cap in r["capabilities"]:
            assert "id" in cap or "domain" in cap

    def test_models_schema(self):
        r = get("/api/v1/kernel/models", auth=False)
        assert isinstance(r["total"], int)
        for m in r.get("models", []):
            assert "name" in m
            assert "status" in m

class TestMeshContract:
    def test_stats_schema(self):
        r = get("/api/v1/mesh/stats")
        assert "total_endpoints" in r
        assert isinstance(r["healthy_endpoints"], int)

class TestGovernanceContract:
    def test_policies_schema(self):
        r = get("/api/v1/governance/policies")
        assert isinstance(r["policies"], list)
        for p in r["policies"]:
            assert "name" in p or "rule_id" in p

class TestEvidencesContract:
    def test_stats_schema(self):
        r = get("/api/v1/evidence/stats")
        assert "total_chains" in r

class TestTritonContract:
    def test_health_schema(self):
        r = get("/api/v1/triton/health")
        assert "ready" in r
        assert "live" in r

class TestSurveillanceContract:
    def test_stats_schema(self):
        r = get("/api/v1/surveillance/stats")
        assert "total_alarms" in r
        assert "active_alarms" in r

class TestGB28181Contract:
    def test_stats_schema(self):
        r = get("/api/v1/cameras/gb28181/stats")
        assert "registered_devices" in r

class TestTelemetryContract:
    def test_stats_schema(self):
        r = get("/api/v1/telemetry/stats")
        assert "uptime_seconds" in r

class TestToolsContract:
    def test_stats_schema(self):
        r = get("/api/v1/tools/stats")
        assert "total_tools" in r

class TestMemoryContract:
    def test_stats_schema(self):
        r = get("/api/v1/memory/stats")
        assert "working_size" in r

class TestVideoContract:
    def test_stats_schema(self):
        r = get("/api/v1/video/stats")
        assert "total_streams" in r

class TestPolicyContract:
    def test_rules_schema(self):
        r = get("/api/v1/policies/rules")
        assert "rules" in r

class TestEndToEndContract:
    def test_full_flow_schema(self):
        r = post("/api/v1/graphrag/search", {"query": "test", "mode": "hybrid"})
        assert "answer" in r
        assert "confidence" in r
        r2 = get("/api/v1/governance/stats")
        assert "total_policies" in r2
