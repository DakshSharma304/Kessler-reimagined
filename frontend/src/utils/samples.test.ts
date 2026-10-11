import { it, expect } from 'vitest';
import { closestSample } from './samples';
import type { Model } from '../api/client';
it('selects actual samples without extrapolating unsupported times or filling gaps', () => {
  const path = {
    samples: [
      { epoch: '2026-10-11T00:00:00Z', position_km: [1, 2, 3], propagation_status: 'OK' },
      { epoch: '2026-10-11T00:00:10Z', position_km: [4, 5, 6], propagation_status: 'OK' },
    ],
  } as Model<'ObjectTrajectory'>;
  expect(closestSample(path, Date.parse('2026-10-11T00:00:08Z'))?.position_km).toEqual([4, 5, 6]);
  expect(closestSample(path, Date.parse('2026-10-11T00:00:11Z'))).toBeNull();
  expect(closestSample({ ...path, samples: [] }, Date.now())).toBeNull();
});
