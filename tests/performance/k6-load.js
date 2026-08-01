/**
 * VIAIOS k6 Load Test — 7 API scenarios
 * Run: k6 run tests/performance/k6-load.js
 * Install: npm i -g k6  or  docker run -i grafana/k6 run - <tests/performance/k6-load.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';

const BASE = __ENV.BASE_URL || 'http://ry3.9gpu.com:18006';
const CREDS = JSON.stringify({ username: 'admin', password: 'viaios-admin-2024' });

export const options = {
  stages: [
    { duration: '10s', target: 5 },   // Warmup
    { duration: '30s', target: 20 },  // Ramp up
    { duration: '60s', target: 20 },  // Steady
    { duration: '10s', target: 0 },   // Cool down
  ],
  thresholds: {
    'http_req_duration{group:search}': ['p(95)<1000'],
    'http_req_duration{group:health}': ['p(95)<500'],
    'http_req_failed': ['rate<0.05'],
  },
};

export default function () {
  let token = '';
  let headers = { 'Content-Type': 'application/json' };

  group('auth', () => {
    const r = http.post(`${BASE}/api/v1/auth/login`, CREDS, { headers, tags: { group: 'auth' } });
    check(r, { 'login 200': (r) => r.status === 200 });
    try { token = r.json().accessToken; } catch (e) {}
    if (token) headers['Authorization'] = `Bearer ${token}`;
    sleep(0.5);
  });

  group('health', () => {
    const r = http.get(`${BASE}/api/system/services`, { headers, tags: { group: 'health' } });
    check(r, { 'health 200': (r) => r.status === 200 });
    sleep(0.3);
  });

  group('search', () => {
    const body = JSON.stringify({ image_data: 'dGVzdA==', category: 'test', top_k: 3 });
    const r = http.post(`${BASE}/api/v1/search/v2/image`, body, { headers, tags: { group: 'search' } });
    check(r, { 'search 200': (r) => r.status === 200 });
    sleep(0.5);
  });

  group('planner', () => {
    const body = JSON.stringify({ goal: 'test query', strategy: 'sequential' });
    const r = http.post(`${BASE}/api/v1/agents/plan`, body, { headers, tags: { group: 'planner' } });
    check(r, { 'planner 200': (r) => r.status === 200 });
    sleep(0.3);
  });

  group('reasoner', () => {
    const body = JSON.stringify({ query: 'test reasoning', max_steps: 2 });
    const r = http.post(`${BASE}/api/v1/reasoning/reason`, body, { headers, tags: { group: 'reasoner' } });
    check(r, { 'reasoner 200': (r) => r.status === 200 });
    sleep(0.3);
  });

  group('graph', () => {
    const body = JSON.stringify({ query_name: 'entity_neighbors', params: { entity_id: 'P001' } });
    const r = http.post(`${BASE}/api/v1/graph/execute`, body, { headers, tags: { group: 'graph' } });
    check(r, { 'graph 200': (r) => r.status === 200 });
    sleep(0.3);
  });

  group('cameras', () => {
    const r = http.get(`${BASE}/api/v1/cameras`, { headers, tags: { group: 'cameras' } });
    check(r, { 'cameras 200': (r) => r.status === 200 });
    sleep(0.3);
  });
}
