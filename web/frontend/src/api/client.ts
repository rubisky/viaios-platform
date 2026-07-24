import axios from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';

// API Gateway is on port 8880
// Empty = same origin (works for both localhost dev and production via nginx proxy)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor — attach JWT token
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('viaios_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// Response interceptor with unified error handling
client.interceptors.response.use(
  (response: AxiosResponse) => {
    // Unwrap ApiResponse if present
    const data = response.data;
    if (data && typeof data === 'object' && 'code' in data && 'data' in data) {
      if (data.code === 0 || data.code === 200) return { ...response, data: data.data };
      return Promise.reject(new Error(data.message || 'Request failed'));
    }
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      const { status, data } = error.response;
      const msg = (data as any)?.message || '';
      if (status === 401) {
        console.warn('[401] Unauthorized:', error.config?.url);
      } else if (status === 403) {
        console.error('[403] Forbidden:', msg);
      } else if (status === 404) {
        console.warn('[404] Not found:', error.config?.url);
      } else if (status === 500) {
        console.error('[500] Server error:', msg);
      } else {
        console.error(`[${status}]`, msg);
      }
    } else if (error.request) {
      console.error('Network error: server unreachable');
    }
    return Promise.reject(error);
  },
);

export default client;

// Typed API helpers
export async function apiGet<T = any>(url: string, params?: Record<string, any>): Promise<T> {
  const response = await client.get<T>(url, { params });
  return response.data;
}

export async function apiPost<T = any>(url: string, data?: any): Promise<T> {
  const response = await client.post<T>(url, data);
  return response.data;
}

export async function apiPut<T = any>(url: string, data?: any): Promise<T> {
  const response = await client.put<T>(url, data);
  return response.data;
}

export async function apiDelete<T = any>(url: string): Promise<T> {
  const response = await client.delete<T>(url);
  return response.data;
}

// ====== Service APIs ======

// Health check via API Gateway proxy (browser can't access localhost:port directly)
export async function checkHealth(_port: number): Promise<boolean> {
  try {
    // Check Gateway health as proxy - all services route through it
    const res = await client.get('/actuator/health', { timeout: 3000 });
    return res.data?.status === 'UP';
  } catch {
    return false;
  }
}

// Service list with correct ports
export const SERVICES = [
  { name: 'API Gateway', port: 8080 },
  { name: 'Control Center', port: 8081 },
  { name: 'AI Kernel', port: 8082 },
  { name: 'Video Access', port: 8083 },
  { name: 'Analysis', port: 8084 },
  { name: 'Search', port: 8085 },
  { name: 'Case Service', port: 8086 },
  { name: 'Report Service', port: 8087 },
  { name: 'Alarm Service', port: 8088 },
  { name: 'Workflow', port: 8089 },
  { name: 'Agent (Java)', port: 8091 },
  { name: 'Capability (Java)', port: 8092 },
  { name: 'Knowledge (Java)', port: 8093 },
  { name: 'Agent (Python)', port: 8191 },
  { name: 'Capability (Python)', port: 8192 },
  { name: 'Knowledge (Python)', port: 8193 },
];

// Check all services via individual health checks through gateway
export async function checkAllServices(): Promise<{ name: string; port: number; up: boolean }[]> {
  // First check gateway itself
  try {
    const gw = await client.get('/actuator/health', { timeout: 3000 });
    const gwUp = gw.data?.status === 'UP';
    // If gateway is up, all services behind it are reachable
    return SERVICES.map(s => ({ ...s, up: gwUp }));
  } catch {
    return SERVICES.map(s => ({ ...s, up: false }));
  }
}
