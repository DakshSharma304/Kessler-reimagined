import { it, expect } from 'vitest';
import { initialInputs, validatePlanner, optimizationBody } from '../../stores/planner';
it('requires explicit capability, finite/increasing lead constraints', () => {
  expect(validatePlanner(initialInputs)).not.toHaveLength(0);
  expect(validatePlanner({ ...initialInputs, acknowledged: true })).toEqual([]);
  for (const patch of [
    { maxLead: 3 },
    { minLead: 0 },
    { deltaV: -1 },
    { target: 0 },
    { deltaV: NaN },
  ])
    expect(
      validatePlanner({ ...initialInputs, acknowledged: true, ...patch }).length,
    ).toBeGreaterThan(0);
});
it('encodes actual editable constraints and converts minutes to hours exactly', () => {
  const a = optimizationBody('real', { ...initialInputs, acknowledged: true }, '25544');
  const b = optimizationBody(
    'real',
    { ...initialInputs, acknowledged: true, deltaV: 0.5, maxLead: 30 },
    '25544',
  );
  expect(a.max_lead_time_hours).toBe(0.25);
  expect(b.max_lead_time_hours).toBe(0.5);
  expect(b.max_delta_v_m_s).toBe(0.5);
  expect(b.hypothetical_capability_assumed).toBe(true);
  expect(a.encounter_id).toBe('real');
});
