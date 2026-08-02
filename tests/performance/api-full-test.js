/**
 * VIAIOS Full API Test Suite — P3-1
 * Covers all P0+P1+P2 endpoints across 18 services.
 * Run: k6 run tests/performance/api-full-test.js
 */
import http from 'k6/http';
import { check, sleep, group } from 'k6';

const BASE = __ENV.VIAIOS_BASE_URL || 'http://ry3.9gpu.com:18006';
const ADMIN_USER = __ENV.VIAIOS_ADMIN_USER || 'admin';
const ADMIN_PASS = __ENV.VIAIOS_ADMIN_PASS || 'changeme';
const CREDS = JSON.stringify({ username: ADMIN_USER, password: ADMIN_PASS });

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    'http_req_failed': ['rate<0.1'],
    'http_req_duration': ['p(95)<3000'],
  },
};

function getToken() {
  const r = http.post(`${BASE}/api/v1/auth/login`, CREDS,
    { headers: { 'Content-Type': 'application/json' }, tags: { group: 'auth' } });
  check(r, { 'auth ok': (r) => r.status === 200 });
  try { return r.json().accessToken; } catch (e) { return ''; }
}

export default function () {
  const token = getToken();
  if (!token) { console.error('AUTH FAILED — cannot proceed'); return; }
  const auth = { Authorization: `Bearer ${token}` };
  const json = { 'Content-Type': 'application/json' };
  let passed = 0, failed = 0;

  function test(method, path, opts = {}) {
    const h = { ...(opts.auth !== false ? auth : {}), ...(opts.json !== false ? json : {}) };
    const body = opts.body ? (typeof opts.body === 'string' ? opts.body : JSON.stringify(opts.body)) : null;
    const r = method === 'POST'
      ? http.post(`${BASE}${path}`, body, { headers: h, tags: { group: opts.group || 'api' } })
      : http.get(`${BASE}${path}`, { headers: h, tags: { group: opts.group || 'api' } });
    const ok = check(r, { [`${path}: ${opts.expect || 200}`]: (r) => r.status === (opts.expect || 200) });
    ok ? passed++ : failed++;
    if (!opts.noSleep) sleep(0.2);
    return r;
  }

  // ═══ P0: AI Kernel ═══════════════════════════════════════
  group('P0-Kernel', () => {
    test('GET', '/api/v1/kernel/health', { auth: false });
    test('GET', '/api/v1/kernel/topology', { auth: false });
    test('GET', '/api/v1/kernel/capabilities', { auth: false });
    test('GET', '/api/v1/kernel/models', { auth: false });
  });

  // ═══ P0: Runtime Mesh ═════════════════════════════════════
  group('P0-Mesh', () => {
    test('GET', '/api/v1/mesh/stats');
    test('GET', '/api/v1/mesh/endpoints');
  });

  // ═══ P0: Evidence Chain ═══════════════════════════════════
  group('P0-Evidence', () => {
    test('GET', '/api/v1/evidence/stats');
    test('GET', '/api/v1/evidence/chains');
  });

  // ═══ P0: Capability Pipelines ═════════════════════════════
  group('P0-Capabilities', () => {
    test('GET', '/api/v1/capabilities/list');
  });

  // ═══ P0: Video Pipeline ═══════════════════════════════════
  group('P0-Video', () => {
    test('GET', '/api/v1/video/stats');
  });

  // ═══ P1: GraphRAG ═════════════════════════════════════════
  group('P1-GraphRAG', () => {
    test('POST', '/api/v1/graphrag/search',
      { body: { query: 'test query', mode: 'hybrid' } });
  });

  // ═══ P1: Workflow DSL ═════════════════════════════════════
  group('P1-Workflow', () => {
    test('GET', '/api/v1/workflow/templates');
    test('GET', '/api/v1/workflow/template/video_analysis');
  });

  // ═══ P1: Evaluator + Governance ═══════════════════════════
  group('P1-EvalGov', () => {
    test('POST', '/api/v1/evaluator/evaluate',
      { body: { agent_id: 'test', agent_name: 'Test', task: 'test', output: 'test result' } });
    test('GET', '/api/v1/governance/policies');
    test('GET', '/api/v1/governance/stats');
  });

  // ═══ P2: Triton + GB28181 ═════════════════════════════════
  group('P2-TritonGB', () => {
    test('GET', '/api/v1/triton/health');
    test('GET', '/api/v1/triton/models');
    test('GET', '/api/v1/cameras/gb28181/stats');
    test('GET', '/api/v1/cameras/gb28181/devices');
  });

  // ═══ P2: Video Service ════════════════════════════════════
  group('P2-VideoService', () => {
    test('GET', '/api/v1/video/stats');
    test('GET', '/api/v1/video/streams');
  });

  // ═══ Core Services ════════════════════════════════════════
  group('Core', () => {
    test('GET', '/api/v1/cameras');
    test('GET', '/api/v1/cases');
    test('GET', '/api/v1/agents');
    test('GET', '/api/v1/search/collections');
    test('GET', '/api/system/services', { auth: false });
  });

  // ═══ Health ═══════════════════════════════════════════════
  group('Health', () => {
    test('GET', '/actuator/health', { auth: false });
    test('GET', '/', { auth: false, json: false, expect: 200 });
  });

  console.log(`\n=== RESULTS: ${passed}/${passed + failed} passed ===`);
}
