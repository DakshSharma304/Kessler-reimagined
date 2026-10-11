import { test, expect } from '@playwright/test';

test('camera keeps Earth context; keyboard and responsive panels stay usable', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Close approaches', exact: true }).click();
  await page.getByLabel('Search encounters').fill('27056');
  await expect(page.locator('.encounter-row').first()).toContainText('COSMOS', { timeout: 60000 });
  await page.locator('.encounter-row').first().click();
  await expect
    .poll(async () => Number(await page.locator('canvas').getAttribute('data-camera-radius')), {
      timeout: 30000,
    })
    .toBeLessThan(4.2);
  await page.screenshot({ path: 'test-results/checkpoint6-encounter-desktop.png' });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Open inspector' })).toBeVisible();
  await page.evaluate(() => (document.activeElement as HTMLElement)?.blur());
  await page.keyboard.press('r');
  await expect
    .poll(async () => Number(await page.locator('canvas').getAttribute('data-camera-radius')), {
      timeout: 30000,
    })
    .toBeGreaterThan(4.3);
  await page.keyboard.press('/');
  await expect(page.getByLabel('Search encounters')).toBeFocused();

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.getByRole('button', { name: 'Explore', exact: true }).click();
  await page.screenshot({ path: 'test-results/checkpoint6-explore-wide.png' });
  await page.setViewportSize({ width: 1366, height: 768 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/checkpoint6-explore-laptop.png' });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByLabel('Search objects').fill('25544');
  await page.getByRole('button', { name: /ISS/ }).first().click();
  await expect(page.getByRole('button', { name: 'Close inspector' })).toBeVisible();
  await page.getByRole('button', { name: 'Orbital decay', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Orbital decay', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open inspector' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/checkpoint6-decay-mobile.png' });
  expect(errors).toEqual([]);
});

test('reduced motion disables interface animations without blocking navigation', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(
    true,
  );
  expect(
    await page
      .getByRole('button', { name: 'Explore', exact: true })
      .evaluate((node) => getComputedStyle(node).transitionDuration),
  ).toBe('0s');
  await page.getByRole('button', { name: 'Data & methods', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Data & methods', exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect
    .poll(async () => {
      const active = await page.locator('.nav-item.active').boundingBox();
      const nav = await page.getByRole('navigation').boundingBox();
      // Chromium can place the final tab 0.2 CSS px beyond the scroll box.
      return (
        !!active &&
        !!nav &&
        active.x >= nav.x - 1 &&
        active.x + active.width <= nav.x + nav.width + 1
      );
    })
    .toBe(true);
  await page.screenshot({ path: 'test-results/checkpoint6-reduced-motion-mobile.png' });
});
