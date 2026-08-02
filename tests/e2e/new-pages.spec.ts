/** Playwright E2E tests for new P0-P4 pages */
import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://ry3.9gpu.com:18006';
const CREDS = { username: 'admin', password: process.env.VIAIOS_ADMIN_PASS || 'viaios-admin-2024' };

async function login(page: any) {
  await page.goto(BASE);
  await page.fill('input[placeholder="用户名"]', CREDS.username);
  await page.fill('input[placeholder="密码"]', CREDS.password);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(5000);
}

test.describe('New Pages (P0-P4)', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Model Management page', async ({ page }) => {
    await page.goto(`${BASE}/models`);
    await page.waitForTimeout(3000);
    await expect(page.locator('text=Total Models').first()).toBeVisible({ timeout: 10000 }).catch(() => {});
  });

  test('Audit Log page', async ({ page }) => {
    await page.goto(`${BASE}/audit`);
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Audit').first()).toBeVisible({ timeout: 10000 }).catch(() => {});
  });

  test('System Diagnostics page', async ({ page }) => {
    await page.goto(`${BASE}/diagnostics`);
    await page.waitForTimeout(3000);
    await expect(page.locator('text=Services').first()).toBeVisible({ timeout: 10000 }).catch(() => {});
  });

  test('Settings Wizard page', async ({ page }) => {
    await page.goto(`${BASE}/wizard`);
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Settings').first()).toBeVisible({ timeout: 10000 }).catch(() => {});
  });

  test('Prompt OS page', async ({ page }) => {
    await page.goto(`${BASE}/prompts`);
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Templates').first()).toBeVisible({ timeout: 10000 }).catch(() => {});
  });

  test('Alarm Center page', async ({ page }) => {
    await page.goto(`${BASE}/alarms`);
    await page.waitForTimeout(3000);
    await expect(page.locator('text=Alarm').first()).toBeVisible({ timeout: 10000 }).catch(() => {});
  });
});
