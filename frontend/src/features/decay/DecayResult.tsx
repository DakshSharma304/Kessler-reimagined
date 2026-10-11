import { useState } from 'react';
import { useScience } from '../../stores/science';
import { useUI } from '../../stores/ui';
import type { Model } from '../../api/client';
import { Empty, Metric, Section, Status, Warnings } from '../../components/ui';
import { number, timestamp } from '../../utils/format';

type Sample = Model<'DecaySample'>;
type Scenario = Model<'ScenarioResult'>;
export function chartPoints(
  samples: Sample[],
  field: 'geodetic' | 'perigee_altitude_m' | 'apogee_altitude_m',
  low: number,
  range: number,
) {
  const values = samples
    .map((sample) => (field === 'geodetic' ? sample.geodetic.altitude_m : sample[field]))
    .filter(Number.isFinite);
  if (values.length < 2) return '';
  return values
    .map(
      (value, i) => `${12 + (i * 276) / (values.length - 1)},${114 - ((value - low) * 96) / range}`,
    )
    .join(' ');
}
function Curve({ samples }: { samples: Sample[] }) {
  if (samples.length < 2)
    return <p className="caption">No valid numerical trajectory samples to chart.</p>;
  const series = [
    ['geodetic', 'Geodetic altitude', '#b9d5e5'],
    ['perigee_altitude_m', 'Osculating perigee', '#b8b3ad'],
    ['apogee_altitude_m', 'Osculating apogee', '#d5d0c9'],
  ] as const;
  const heights = samples
    .flatMap((sample) => [
      sample.geodetic.altitude_m,
      sample.perigee_altitude_m,
      sample.apogee_altitude_m,
    ])
    .filter(Number.isFinite);
  const low = Math.min(...heights),
    range = Math.max(...heights) - low || 1;
  return (
    <div className="decay-chart">
      <svg
        role="img"
        aria-label={`Actual ${samples.length}-sample altitude trajectory with geodetic altitude and osculating perigee and apogee`}
        viewBox="0 0 300 130"
        preserveAspectRatio="none"
      >
        <line x1="12" y1="114" x2="288" y2="114" stroke="#5b6269" />
        {series.map(([field, label, color]) => (
          <polyline
            key={field}
            points={chartPoints(samples, field, low, range)}
            fill="none"
            stroke={color}
            strokeWidth="1.6"
          >
            <title>{label}</title>
          </polyline>
        ))}
      </svg>
      <div className="chart-legend">
        {series.map(([, label, color]) => (
          <span key={label}>
            <i style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
      <p className="caption">
        {timestamp(samples[0].state.timestamp)} → {timestamp(samples.at(-1)!.state.timestamp)}.
        Shared altitude scale in meters. Perigee/apogee are osculating element radii minus
        equatorial radius, not geodetic height.
      </p>
    </div>
  );
}
export default function DecayResult() {
  const id = useUI((s) => s.selectedId);
  const record = useScience((s) => s.decay);
  const [choice, setChoice] = useState('NOMINAL');
  if (!record || record.objectId !== id)
    return (
      <Empty title="Model an orbit">
        Enter physical assumptions and calculate a bounded atmospheric scenario.
      </Empty>
    );
  const data = record.result;
  const scenarios = data.scenario_analysis?.scenarios || [];
  const selected: Scenario | undefined =
    scenarios.find((s) => s.scenario === choice) ||
    scenarios.find((s) => s.scenario === 'NOMINAL') ||
    scenarios[0];
  const boundary = selected?.boundary;
  const samples = boundary?.propagation?.samples || [];
  return (
    <>
      <span className="eyebrow">NUMERICAL PERSISTENCE · NORAD {id}</span>
      <h3 className="object-title">A bounded trajectory</h3>
      <Status tone={boundary?.prediction_status === 'BOUNDARY_REACHED' ? 'warning' : 'neutral'}>
        {boundary?.prediction_status || data.prediction_status}
      </Status>
      {scenarios.length > 1 && (
        <div className="solution-tabs">
          {scenarios.map((s) => (
            <button
              key={s.scenario}
              aria-pressed={selected?.scenario === s.scenario}
              onClick={() => setChoice(s.scenario)}
            >
              {s.scenario.replace('_', ' ')}
            </button>
          ))}
        </div>
      )}
      <Section title="Modeled horizon">
        <Metric
          label="Prediction horizon"
          value={number(data.prediction_horizon_days, 4)}
          unit="days"
        />
        <Metric
          label="Boundary"
          value={number(
            boundary?.boundary_altitude_m === undefined
              ? null
              : boundary.boundary_altitude_m / 1000,
            0,
          )}
          unit="km geodetic"
        />
        <Metric label="Reached within horizon" value={boundary?.crossing_occurred ? 'Yes' : 'No'} />
        <p className="caption">
          {boundary?.crossing_occurred
            ? `Modeled boundary time ${timestamp(boundary.crossing_time ?? undefined)}; this is not actual reentry.`
            : 'The modeled boundary was not reached within the selected horizon, or valid inputs/source data were unavailable. This is not an indefinite lifetime estimate.'}
        </p>
      </Section>
      <Section title="Altitude & orbit shape">
        {samples.length >= 2 ? (
          <>
            <Curve key={selected?.scenario} samples={samples} />
            <Metric
              label="Final geodetic altitude"
              value={number(samples.at(-1)!.geodetic.altitude_m / 1000, 2)}
              unit="km"
            />
            <Metric
              label="Final osculating perigee"
              value={number(samples.at(-1)!.perigee_altitude_m / 1000, 2)}
              unit="km"
            />
            <Metric
              label="Final osculating apogee"
              value={number(samples.at(-1)!.apogee_altitude_m / 1000, 2)}
              unit="km"
            />
          </>
        ) : (
          <p className="caption">
            No numerical curve is available for this scenario. The status and warnings below explain
            why.
          </p>
        )}
      </Section>
      <Section title="Source & assumptions">
        <p className="caption">
          GP epoch {timestamp(data.gp_epoch)}. Scenario {selected?.scenario || 'Unavailable'}.
          Actual numerical propagation with specified drag and weather treatment.
        </p>
        <Warnings
          items={[
            ...data.assumptions,
            ...data.warnings,
            ...(data.scenario_analysis?.assumptions || []),
            ...(selected?.warnings || []),
            ...(boundary?.warnings || []),
          ]}
        />
      </Section>
    </>
  );
}
