/**
 * VIAIOS k6 Smoke Test — Quick sanity check (~10s)
 * Run: k6 run tests/performance/smoke-test.js
 */
import http from 'k6/http';
import { check, sleep, group } from 'k6';

const BASE = __ENV.VIAIOS_BASE_URL || __ENV.BASE_URL || 'http://ry3.9gpu.com:18006';
const ADMIN_USER = __ENV.VIAIOS_ADMIN_USER || 'admin';
const ADMIN_PASS = __ENV.VIAIOS_ADMIN_PASS || 'changeme';
const CREDS = JSON.stringify({ username: ADMIN_USER, password: ADMIN_PASS });

export const options = {
  vus: 2,
  duration: '10s',
  thresholds: {
    'http_req_failed': ['rate<0.1'],
    'http_req_duration': ['p(95)<3000'],
  },
};

export default function () {
  let token = '';
  let headers = { 'Content-Type': 'application/json' };

  group('health', () => {
    const r = http.get(`${BASE}/actuator/health`, { tags: { group: 'health' } });
    check(r, { 'gateway up': (r) => r.status === 200 });
    sleep(0.5);
  });

  group('login', () => {
    const r = http.post(`${BASE}/api/v1/auth/login`, CREDS, { headers, tags: { group: 'login' } });
    check(r, { 'login ok': (r) => r.status === 200 });
    try { token = r.json().accessToken; } catch (e) { }
    if (token) headers['Authorization'] = `Bearer ${token}`;
    sleep(0.5);
  });

  group('services', () => {
    const r = http.get(`${BASE}/api/system/services`, { headers, tags: { group: 'services' } });
    check(r, { 'services ok': (r) => r.status === 200 });
  });
}
