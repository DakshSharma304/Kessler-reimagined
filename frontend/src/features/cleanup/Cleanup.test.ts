import { expect, it } from 'vitest';
import { validateCleanup } from './Cleanup';
it('rejects unsupported budgets, absent effort costs, and empty or negative policies', () => {
  expect(validateCleanup(0, [1, 0, 0], '0', '101: 2', ['101'])).toEqual({
    effort_budget: 0,
    effort_costs: { '101': 2 },
  });
  expect(() => validateCleanup(1, [0, 0, 0], '', '', [])).toThrow();
  expect(() => validateCleanup(1, [1, 0, 0], '2', '', ['101'])).toThrow();
  expect(() => validateCleanup(100, [1, 0, 0], '', '', [])).toThrow();
});
