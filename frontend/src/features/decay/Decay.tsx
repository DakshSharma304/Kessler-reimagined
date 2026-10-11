import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { request, type Model } from '../../api/client';
import { useUI } from '../../stores/ui';
import { useScience } from '../../stores/science';
import { Empty, ErrorNotice, Field, Status } from '../../components/ui';

export function validateDecay(
  mass: string,
  area: string,
  cd: string,
  horizon: string,
  weather: string,
  f107: string,
  ap: string,
) {
  const values = [mass, area, cd, horizon].map(Number);
  if (
    [mass, area, cd, horizon].some((v) => !v.trim()) ||
    values.some((v) => !Number.isFinite(v)) ||
    values[0] <= 0 ||
    values[1] < 0 ||
    values[2] <= 0 ||
    values[2] > 5 ||
    values[3] <= 0 ||
    values[3] > 1
  )
    throw Error(
      'Enter positive finite mass, area, drag coefficient ≤5, and a horizon above zero and at most 1 day.',
    );
  if (
    weather !== 'SOURCE_ONLY' &&
    (!f107.trim() ||
      !ap.trim() ||
      !Number.isFinite(Number(f107)) ||
      !Number.isFinite(Number(ap)) ||
      Number(f107) <= 0 ||
      Number(f107) > 500 ||
      Number(ap) < 0 ||
      Number(ap) > 400)
  )
    throw Error('Explicit hypothetical weather requires F10.7 in (0,500] sfu and Ap in [0,400].');
  return values;
}

export default function Decay() {
  const id = useUI((s) => s.selectedId);
  const ui = useUI();
  const science = useScience();
  const [mass, setMass] = useState('');
  const [area, setArea] = useState('');
  const [cd, setCd] = useState('2.2');
  const [horizon, setHorizon] = useState('0.05');
  const [weather, setWeather] = useState<'SOURCE_ONLY' | 'HYPOTHETICAL_CONSTANT'>('SOURCE_ONLY');
  const [f107, setF107] = useState('');
  const [ap, setAp] = useState('');
  const [mode, setMode] = useState<'NOMINAL' | 'COMPARE'>('NOMINAL');
  const [ack, setAck] = useState(false);
  const [message, setMessage] = useState('');
  const mutation = useMutation({
    mutationFn: (body: Model<'PersistenceRequest'>) =>
      request<Model<'PersistenceAnalysis'>>(`/objects/${id}/persistence`, { body }),
    onSuccess: (result) => {
      science.setDecay({ objectId: id!, result });
      ui.openPanel('right');
    },
  });
  function run() {
    setMessage('');
    try {
      if (!id) throw Error('Select a cataloged object first.');
      if (!ack) throw Error('Confirm the physical parameters are user-supplied assumptions.');
      const [m, a, c, h] = validateDecay(mass, area, cd, horizon, weather, f107, ap);
      const body: Model<'PersistenceRequest'> = {
        aerodynamic_properties: {
          input_category: 'HYPOTHETICAL_ASSUMPTION',
          mass_kg: m,
          area_m2: a,
          drag_coefficient: c,
        },
        horizon_days: h,
        boundary_altitude_m: 120000,
        scenario_mode: mode,
        weather_mode: weather,
        visualization: false,
        solver: {
          sample_step_seconds: Math.max(10, Math.min(300, Math.round((h * 86400) / 96))),
          timeout_seconds: 45,
          rtol: 1e-9,
          position_atol_m: 1e-4,
          velocity_atol_m_s: 1e-7,
          max_step_seconds: 120,
        },
        ...(weather === 'SOURCE_ONLY'
          ? {}
          : { nominal_f107_sfu: Number(f107), nominal_ap: Number(ap) }),
      };
      mutation.mutate(body);
    } catch (error) {
      setMessage((error as Error).message);
    }
  }
  return (
    <>
      <span className="eyebrow">ATMOSPHERIC MODEL</span>
      <h3 className="feature-title">Orbital persistence</h3>
      <p className="caption">
        Explore a finite numerical horizon with explicit physical and weather inputs. A modeled
        boundary crossing is not ground impact or a certain reentry date.
      </p>
      {!id ? (
        <Empty title="Choose an object">
          Select a tracked object in Explore, then return here. No mass or area is assumed from
          catalog metadata.
        </Empty>
      ) : (
        <>
          <Status>Selected NORAD {id}</Status>
          <button className="text-button" onClick={() => ui.setView('Explore')}>
            Change object
          </button>
        </>
      )}
      <Field label="Assumed mass · kg">
        <input
          type="number"
          min="0.001"
          step="any"
          value={mass}
          onChange={(event) => setMass(event.target.value)}
        />
      </Field>
      <Field label="Assumed drag area · m²">
        <input
          type="number"
          min="0"
          step="any"
          value={area}
          onChange={(event) => setArea(event.target.value)}
        />
      </Field>
      <Field label="Assumed drag coefficient">
        <input
          type="number"
          min="0.001"
          max="5"
          step="any"
          value={cd}
          onChange={(event) => setCd(event.target.value)}
        />
      </Field>
      <Field
        label="Prediction horizon · days"
        hint="Interface bound: 1 day. Longer science requests are available directly through the backend."
      >
        <input
          type="number"
          min="0.0001"
          max="1"
          step="any"
          value={horizon}
          onChange={(event) => setHorizon(event.target.value)}
        />
      </Field>
      <Field label="Atmospheric scenarios">
        <select value={mode} onChange={(event) => setMode(event.target.value as typeof mode)}>
          <option value="NOMINAL">Nominal only</option>
          <option value="COMPARE">Low / nominal / high drag</option>
        </select>
      </Field>
      <Field label="Nominal weather source">
        <select
          value={weather}
          onChange={(event) => setWeather(event.target.value as typeof weather)}
        >
          <option value="SOURCE_ONLY">Available measured / forecast source</option>
          <option value="HYPOTHETICAL_CONSTANT">Hypothetical constant solar history</option>
        </select>
      </Field>
      {weather === 'HYPOTHETICAL_CONSTANT' && (
        <div className="row">
          <Field label="F10.7 · sfu">
            <input
              type="number"
              min="0.001"
              max="500"
              value={f107}
              onChange={(event) => setF107(event.target.value)}
            />
          </Field>
          <Field label="Ap index">
            <input
              type="number"
              min="0"
              max="400"
              value={ap}
              onChange={(event) => setAp(event.target.value)}
            />
          </Field>
        </div>
      )}
      <label className="checkbox">
        <input type="checkbox" checked={ack} onChange={(event) => setAck(event.target.checked)} />
        <span>I understand these physical inputs are hypothetical and the horizon is bounded.</span>
      </label>
      <button className="primary-button" onClick={run} disabled={!id || mutation.isPending}>
        {mutation.isPending ? 'Calculating atmospheric trajectory…' : 'Analyze persistence'}
      </button>
      {message && (
        <p role="alert" className="validation-message">
          {message}
        </p>
      )}
      <ErrorNotice error={mutation.error} />
      <p className="caption">
        NRLMSIS 2.1, WGS84/J2 + drag. Source weather may be unavailable for the selected epoch; the
        backend reports that explicitly.
      </p>
    </>
  );
}
