/**
 * VIAIOS E2E Critical Flow Tests
 * Run: npx playwright test tests/e2e/critical-flow.spec.ts
 * Requirements: Playwright installed (npm i -D @playwright/test)
 */
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://ry3.9gpu.com:18006';
const CREDENTIALS = { username: 'admin', password: 'viaios-admin-2024' };

test.describe('VIAIOS Critical Flows', () => {

  test('Login → Dashboard → Cameras → Cases', async ({ page }) => {
    // 1. Navigate to app
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/VIAIOS/);

    // 2. Login
    await page.fill('input[placeholder="用户名"]', CREDENTIALS.username);
    await page.fill('input[placeholder="密码"]', CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/');

    // 3. Dashboard loads with stats
    await expect(page.locator('.ant-statistic-content-value').first()).toBeVisible({ timeout: 10000 });
    console.log('[PASS] Login + Dashboard');

    // 4. Navigate to Cameras
    await page.click('text=摄像头');
    await page.waitForURL('**/cameras');
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 });
    console.log('[PASS] Camera List');

    // 5. Click first camera
    const firstCamera = page.locator('.ant-table-row').first();
    if (await firstCamera.count() > 0) {
      await firstCamera.click();
      await page.waitForTimeout(2000);
      console.log('[PASS] Camera Detail');
    }

    // 6. Navigate to Cases
    await page.click('text=案件管理');
    await page.waitForURL('**/cases');
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 });
    console.log('[PASS] Case List');

    // 7. Navigate to Search
    await page.click('text=目标检索');
    await page.waitForURL('**/search');
    console.log('[PASS] Search Page');

    // 8. Navigate to Alarms
    await page.click('text=智能研判');
    await page.waitForURL('**/surveillance');
    await expect(page.locator('.ant-statistic-content-value').first()).toBeVisible({ timeout: 5000 });
    console.log('[PASS] Alarm Page');

    // 9. Navigate to Admin
    await page.click('text=系统管理');
    await page.waitForURL('**/settings');
    console.log('[PASS] Admin Page');
  });

  test('API Health Check', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/actuator/health`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.status).toBe('UP');
    console.log('[PASS] API Health: UP');
  });

  test('Auth Flow', async ({ request }) => {
    const resp = await request.post(`${BASE_URL}/api/v1/auth/login`, {
      data: CREDENTIALS,
      headers: { 'Content-Type': 'application/json' },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.accessToken).toBeTruthy();
    expect(data.role).toBe('ADMIN');
    console.log('[PASS] Auth: ' + data.role + ' token received');
  });

  test('Key APIs respond', async ({ request }) => {
    // Login first to get token
    const authResp = await request.post(`${BASE_URL}/api/v1/auth/login`, {
      data: CREDENTIALS, headers: { 'Content-Type': 'application/json' },
    });
    const token = (await authResp.json()).accessToken;
    const headers = { Authorization: `Bearer ${token}` };

    const apis = ['/api/v1/cameras', '/api/v1/cases', '/api/v1/agents', '/api/v1/knowledge/entities', '/api/v1/capabilities', '/api/v1/search/collections'];
    for (const api of apis) {
      const resp = await request.get(`${BASE_URL}${api}`, { headers });
      expect(resp.status()).toBe(200);
      console.log(`[PASS] ${api}: 200`);
    }
  });
});
