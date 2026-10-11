import { expect, it } from 'vitest';
import { validateDecay } from './Decay';
it('requires explicit physical and hypothetical weather inputs with bounded work', () => {
  expect(validateDecay('400', '4', '2.2', '.05', 'SOURCE_ONLY', '', '')).toEqual([
    400, 4, 2.2, 0.05,
  ]);
  expect(() => validateDecay('', '4', '2.2', '.05', 'SOURCE_ONLY', '', '')).toThrow();
  expect(() => validateDecay('400', '4', '2.2', '90', 'SOURCE_ONLY', '', '')).toThrow();
  expect(() => validateDecay('400', '4', '2.2', '.05', 'HYPOTHETICAL_CONSTANT', '', '')).toThrow();
});
