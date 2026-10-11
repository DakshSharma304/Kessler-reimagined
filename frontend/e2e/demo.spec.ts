import { test, expect } from '@playwright/test';

test('one real browser session exercises all six Kessler workflows', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });

  const positions = page.waitForResponse(
    (response) => response.url().endsWith('/positions') && response.ok(),
  );
  await page.goto('/');
  const batch = await (await positions).json();
  expect(
    batch.items.filter((item: { propagation_status: string }) => item.propagation_status === 'OK')
      .length,
  ).toBeGreaterThan(1000);
  await page.getByLabel('Search objects').fill('25544');
  const orbitResponse = page.waitForResponse(
    (response) => response.url().includes('/objects/25544/trajectory') && response.ok(),
  );
  await page.getByRole('button', { name: /ISS/ }).first().click();
  const orbit = await (await orbitResponse).json();
  expect(orbit.frame).toBe('ITRS');
  await expect(page.getByRole('heading', { name: /ISS/ })).toBeVisible();
  await page.screenshot({ path: 'test-results/demo-explore.png' });

  await page.getByRole('button', { name: 'Close approaches', exact: true }).click();
  await page.getByLabel('Search encounters').fill('27056');
  await expect(page.locator('.encounter-row').first()).toContainText('COSMOS', { timeout: 60000 });
  const analyzed = page.waitForResponse(
    (response) => response.url().endsWith('/analyze') && response.ok(),
  );
  const encounterPaths = page.waitForResponse(
    (response) => response.url().includes('/trajectories?') && response.ok(),
  );
  await page.locator('.encounter-row').first().click();
  const analysis = await (await analyzed).json();
  const tracks = await (await encounterPaths).json();
  expect(analysis.probability_analysis.probability_status).toBe('UNAVAILABLE_NO_COVARIANCE');
  expect(analysis.probability_analysis.calculated_pc).toBeNull();
  expect(tracks.trajectories).toHaveLength(2);
  await page.screenshot({ path: 'test-results/demo-encounter.png' });

  await page.getByRole('button', { name: 'Avoidance planner', exact: true }).click();
  await page.getByLabel('I explicitly assume').check();
  await page.getByLabel('Maximum delta-v · m/s', { exact: true }).fill('.1');
  const optimized = page.waitForResponse(
    (response) => response.url().endsWith('/optimize') && response.ok(),
  );
  await page.getByRole('button', { name: 'Find best maneuvers' }).click();
  const options = await (await optimized).json();
  expect(options.solutions.length).toBeGreaterThan(0);
  const path = page.waitForResponse(
    (response) =>
      response.url().endsWith('/trajectories') &&
      response.request().method() === 'POST' &&
      response.ok(),
  );
  const matched = await (await path).json();
  expect(matched.baseline.frame).toBe('ITRS');
  const screened = page.waitForResponse(
    (response) => response.url().endsWith('/screen') && response.ok(),
  );
  await page.getByRole('button', { name: 'Screen selected alternative' }).click();
  const screening = await (await screened).json();
  expect(screening.objects_screened).toBeGreaterThan(0);
  await page.screenshot({ path: 'test-results/demo-maneuver.png' });

  await page.getByRole('button', { name: 'Close approaches', exact: true }).click();
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
  const scenarioResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/analyze') &&
      !!response.request().postDataJSON()?.probability_inputs &&
      response.ok(),
  );
  await page.getByRole('button', { name: 'Calculate scenario Pc' }).click();
  const scenario = await (await scenarioResponse).json();
  expect(scenario.probability_analysis.probability_status).toBe('SCENARIO_WITH_ASSUMED_COVARIANCE');
  await expect(page.getByText('Scenario Pc', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/demo-probability.png' });

  await page.getByRole('button', { name: 'Explore', exact: true }).click();
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
  const persistence = page.waitForResponse(
    (response) => response.url().endsWith('/persistence') && response.ok(),
  );
  await page.getByRole('button', { name: 'Analyze persistence' }).click();
  const decay = await (await persistence).json();
  expect(decay.scenario_analysis.scenarios).toHaveLength(3);
  await expect(
    page.getByRole('img', { name: /Actual \d+-sample altitude trajectory/ }),
  ).toBeVisible();
  await page.screenshot({ path: 'test-results/demo-decay.png' });

  await page.getByRole('button', { name: 'Cleanup planner', exact: true }).click();
  await page.getByLabel('Maximum assessment targets').fill('2');
  const portfolio = page.waitForResponse(
    (response) => response.url().endsWith('/cleanup/optimize') && response.ok(),
  );
  await page.getByRole('button', { name: 'Prioritize candidate pool' }).click();
  const cleanup = await (await portfolio).json();
  expect(cleanup.selected_objects.length).toBeGreaterThan(0);
  expect(cleanup.selected_objects.length).toBeLessThanOrEqual(2);
  await expect(page.locator('canvas')).toHaveAttribute(
    'data-highlight-ids',
    cleanup.selected_objects.map((object: { id: string }) => object.id).join(','),
  );
  await page.screenshot({ path: 'test-results/demo-cleanup-selected.png' });
  expect(errors).toEqual([]);
  console.log(
    'REAL_DEMO_RESULTS',
    JSON.stringify({
      catalogOk: batch.items.filter(
        (item: { propagation_status: string }) => item.propagation_status === 'OK',
      ).length,
      orbitSamples: orbit.samples.length,
      encounterId: analysis.encounter_id,
      sourceMissM: analysis.published.miss_distance_m,
      modelMissM: analysis.calculated.miss_distance_m,
      optimizerSolutions: options.solutions.length,
      screeningStatus: screening.screening_status,
      screeningObjects: screening.objects_screened,
      livePcStatus: analysis.probability_analysis.probability_status,
      assumedPc: scenario.probability_analysis.calculated_pc,
      decayScenarios: decay.scenario_analysis.scenarios.map(
        (item: { scenario: string; boundary: { prediction_status: string } }) =>
          `${item.scenario}:${item.boundary.prediction_status}`,
      ),
      cleanupSelectedIds: cleanup.selected_objects.map((object: { id: string }) => object.id),
    }),
  );
});
