import { test, expect } from '@playwright/test';

test('live covariance availability, assumed Pc, fixed-covariance comparison, and historical NASA benchmark', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Close approaches', exact: true }).click();
  await page.getByLabel('Search encounters').fill('27056');
  await expect(page.locator('.encounter-row').first()).toContainText('COSMOS', { timeout: 60000 });
  const baseline = page.waitForResponse((r) => r.url().endsWith('/analyze') && r.ok());
  await page.locator('.encounter-row').first().click();
  const initial = await (await baseline).json();
  expect(initial.probability_analysis.probability_status).toBe('UNAVAILABLE_NO_COVARIANCE');
  expect(initial.probability_analysis.calculated_pc).toBeNull();
  await page.getByText('Analyze assumed covariance scenario').click();
  for (const label of [
    'Primary σ R / X · m',
    'Primary σ T / Y · m',
    'Primary σ N / Z · m',
    'Secondary σ R / X · m',
    'Secondary σ T / Y · m',
    'Secondary σ N / Z · m',
  ])
    await page.getByLabel(label, { exact: true }).fill('500');
  await page.getByLabel('Combined hard-body radius · m').fill('10');
  await page.getByLabel('I assume independent, user-supplied uncertainties').check();
  const scenario = page.waitForResponse(
    (r) => r.url().endsWith('/analyze') && r.request().postDataJSON()?.probability_inputs && r.ok(),
  );
  await page.getByRole('button', { name: 'Calculate scenario Pc' }).click();
  const actual = await (await scenario).json();
  expect(actual.probability_analysis.probability_status).toBe('SCENARIO_WITH_ASSUMED_COVARIANCE');
  expect(actual.probability_analysis.calculated_pc).toBeGreaterThanOrEqual(0);
  expect(actual.probability_analysis.calculated_pc).toBeLessThanOrEqual(1);
  await expect(page.getByText('Scenario Pc', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Avoidance planner', exact: true }).click();
  await page.getByLabel('I explicitly assume').check();
  const optimized = page.waitForResponse((r) => r.url().endsWith('/optimize') && r.ok());
  await page.getByRole('button', { name: 'Find best maneuvers' }).click();
  expect((await (await optimized).json()).solutions.length).toBeGreaterThan(0);
  const comparison = page.waitForResponse((r) => r.url().endsWith('/simulate') && r.ok());
  await page.getByRole('button', { name: 'Compare fixed-covariance Pc' }).click();
  const compared = await (await comparison).json();
  expect(compared.probability_comparison.covariance_treatment).toBe(
    'FIXED_INERTIAL_GCRS_AT_ORIGINAL_TCA',
  );
  expect(compared.probability_comparison.baseline_pc).toBeGreaterThanOrEqual(0);
  expect(compared.probability_comparison.modified_scenario_pc).toBeGreaterThanOrEqual(0);
  await expect(page.getByText('Modified scenario Pc', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Data & methods', exact: true }).click();
  const nasa = page.waitForResponse((r) => r.url().endsWith('/probability/calculate') && r.ok());
  await page.getByRole('button', { name: 'Compare with NASA reference' }).click();
  const reference = await (await nasa).json();
  expect(reference.reference_only).toBe(true);
  expect(reference.published_reference_pc).toBeGreaterThan(0);
  expect(Math.abs(reference.relative_difference)).toBeLessThan(1e-3);
  await expect(page.getByText('HISTORICAL REFERENCE ONLY')).toBeVisible();
  expect(errors).toEqual([]);
  await page.screenshot({ path: 'test-results/checkpoint5-probability.png' });
});

test('actual atmospheric propagation returns charts for three separate scenarios', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  await page.goto('/');
  await page.getByLabel('Search objects').fill('25544');
  await page.getByRole('button', { name: /ISS/ }).first().click();
  await page.getByRole('button', { name: 'Orbital decay', exact: true }).click();
  await page.getByLabel('Assumed mass · kg').fill('400');
  await page.getByLabel('Assumed drag area · m²').fill('4');
  await page.getByLabel('Prediction horizon · days').fill('0.001');
  await page.getByLabel('Atmospheric scenarios').selectOption('COMPARE');
  await page.getByLabel('Nominal weather source').selectOption('HYPOTHETICAL_CONSTANT');
  await page.getByLabel('F10.7 · sfu').fill('100');
  await page.getByLabel('Ap index').fill('10');
  await page.getByLabel('I understand these physical inputs').check();
  const decay = page.waitForResponse((r) => r.url().endsWith('/persistence') && r.ok());
  await page.getByRole('button', { name: 'Analyze persistence' }).click();
  const response = await decay;
  const result = await response.json();
  expect(response.request().postDataJSON().horizon_days).toBe(0.001);
  expect(result.scenario_analysis.scenarios).toHaveLength(3);
  expect(
    result.scenario_analysis.scenarios.every(
      (s: any) => s.boundary.propagation?.samples?.length >= 2,
    ),
  ).toBe(true);
  await expect(
    page.getByRole('img', { name: /Actual \d+-sample altitude trajectory/ }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'LOW DRAG' }).click();
  await expect(page.getByRole('button', { name: 'LOW DRAG' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  expect(errors).toEqual([]);
  await page.screenshot({ path: 'test-results/checkpoint5-decay.png' });
});

test('real debris portfolio obeys target and effort budgets and highlights propagated selections', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  const positions: any[] = [];
  page.on('response', async (r) => {
    if (r.url().endsWith('/positions') && r.ok())
      try {
        positions.push(await r.json());
      } catch {
        /* navigation cancellation */
      }
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Cleanup planner', exact: true }).click();
  await expect(page.getByText('Current pool')).toBeVisible({ timeout: 60000 });
  await page.getByLabel('Maximum assessment targets').fill('2');
  const run = page.getByRole('button', { name: 'Prioritize candidate pool' });
  await expect(run).toBeEnabled({ timeout: 60000 });
  const first = page.waitForResponse((r) => r.url().endsWith('/cleanup/optimize') && r.ok());
  await run.click();
  const firstResponse = await first;
  const data = await firstResponse.json();
  expect(firstResponse.request().postDataJSON().constraints.max_targets).toBe(2);
  expect(data.selected_objects.length).toBeLessThanOrEqual(2);
  expect(data.selected_objects.length).toBeGreaterThan(0);
  const selected = data.selected_objects.map((v: any) => v.id);
  await expect(page.locator('canvas')).toHaveAttribute('data-highlight-ids', selected.join(','));
  await expect
    .poll(
      () =>
        positions.some((batch) =>
          selected.every((id: string) =>
            batch.items.some((item: any) => item.id === id && item.propagation_status === 'OK'),
          ),
        ),
      { timeout: 30000 },
    )
    .toBe(true);
  await page.getByText('Optional abstract effort budget').click();
  const ids = firstResponse.request().postDataJSON().candidate_ids as string[];
  await page.getByLabel('Effort-unit budget').fill('1');
  await page.getByLabel('Per-object effort costs').fill(ids.map((id) => `${id}: 1`).join('\n'));
  const second = page.waitForResponse((r) => r.url().endsWith('/cleanup/optimize') && r.ok());
  await run.click();
  const constrained = await (await second).json();
  expect(constrained.total_abstract_resource_expenditure).toBeLessThanOrEqual(1);
  expect(constrained.selected_objects.length).toBeLessThanOrEqual(1);
  await page.getByLabel('Maximum assessment targets').fill('0');
  const third = page.waitForResponse((r) => r.url().endsWith('/cleanup/optimize') && r.ok());
  await run.click();
  expect((await (await third).json()).selected_objects).toHaveLength(0);
  expect(errors).toEqual([]);
  await page.screenshot({ path: 'test-results/checkpoint5-cleanup.png' });
});
