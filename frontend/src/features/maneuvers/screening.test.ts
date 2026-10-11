import { it, expect } from 'vitest';
import { screeningSummary } from './screening';
it('never describes positive alerts or incomplete coverage as an all-clear', () => {
  expect(screeningSummary({ screening_complete: true, additional_close_approaches: 2 })).toBe(
    'Additional close approaches detected within the selected screening coverage.',
  );
  expect(screeningSummary({ screening_complete: false, additional_close_approaches: 0 })).toContain(
    'Incomplete',
  );
  expect(screeningSummary({ screening_complete: true, additional_close_approaches: 0 })).toContain(
    'No additional',
  );
});
