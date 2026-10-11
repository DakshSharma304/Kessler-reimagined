import { expect, it } from 'vitest';
import { diagonalCovariance } from './Probability';
it('forms SI covariance from explicit one-sigma assumptions, rejecting absence and nonfinite values', () => {
  expect(diagonalCovariance(['2', '3', '4'], 'RTN', '2026-10-11T00:00:00Z').matrix_m2).toEqual([
    [4, 0, 0],
    [0, 9, 0],
    [0, 0, 16],
  ]);
  expect(() => diagonalCovariance(['', '3', '4'], 'RTN', '2026-10-11T00:00:00Z')).toThrow();
  expect(() => diagonalCovariance(['Infinity', '3', '4'], 'RTN', '2026-10-11T00:00:00Z')).toThrow();
});
