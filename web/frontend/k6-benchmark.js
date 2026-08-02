/**
 * VIAIOS Performance Benchmark — k6 load test
 * Run: k6 run k6-benchmark.js -e VIAIOS_ADMIN_PASS=viaios-admin-2024
 */
import http from 'k6/http';
import { check, sleep, group } from 'k6';

const BASE = __ENV.VIAIOS_BASE_URL || 'http://ry3.9gpu.com:18006';
const ADMIN_USER = __ENV.VIAIOS_ADMIN_USER || 'admin';
const ADMIN_PASS = __ENV.VIAIOS_ADMIN_PASS || 'changeme';

export const options = {
  stages: [
    { duration: '10s', target: 2 },
    { duration: '30s', target: 5 },
    { duration: '30s', target: 5 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000', 'p(99)<5000'],
    'http_req_failed': ['rate<0.05'],
    'http_req_duration{group:health}': ['p(95)<500'],
    'http_req_duration{group:kernel}': ['p(95)<1000'],
  },
};

export default function () {
  let token = '';
  const json = { 'Content-Type': 'application/json' };

  group('health', () => {
    const r = http.get(`${BASE}/actuator/health`, { tags: { group: 'health' } });
    check(r, { 'health 200': (r) => r.status === 200 });
    sleep(0.5);
  });

  group('auth', () => {
    const body = JSON.stringify({ username: ADMIN_USER, password: ADMIN_PASS });
    const r = http.post(`${BASE}/api/v1/auth/login`, body, { headers: json, tags: { group: 'auth' } });
    check(r, { 'auth 200': (r) => r.status === 200 });
    try { token = r.json().accessToken; } catch (e) {}
    sleep(0.3);
  });

  const auth = token ? { Authorization: `Bearer ${token}`, ...json } : json;

  group('kernel', () => {
    const r = http.get(`${BASE}/api/v1/kernel/health`, { headers: auth, tags: { group: 'kernel' } });
    check(r, { 'kernel 200': (r) => r.status === 200 });
    sleep(0.3);
  });

  group('governance', () => {
    const r = http.get(`${BASE}/api/v1/governance/stats`, { headers: auth, tags: { group: 'governance' } });
    check(r, { 'gov 200': (r) => r.status === 200 });
    sleep(0.3);
  });

  group('mesh', () => {
    const r = http.get(`${BASE}/api/v1/mesh/stats`, { headers: auth, tags: { group: 'mesh' } });
    check(r, { 'mesh 200': (r) => r.status === 200 });
    sleep(0.3);
  });

  group('cameras', () => {
    const r = http.get(`${BASE}/api/v1/cameras`, { headers: auth, tags: { group: 'cameras' } });
    check(r, { 'cameras 200': (r) => r.status === 200 });
    sleep(0.3);
  });
}
