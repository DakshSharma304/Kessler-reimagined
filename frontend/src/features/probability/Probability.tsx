import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { request, type Model } from '../../api/client';
import { useAnalysis, useEncounter } from '../../hooks/data';
import { useScience } from '../../stores/science';
import { useUI } from '../../stores/ui';
import {
  Empty,
  ErrorNotice,
  Field,
  Loading,
  Metric,
  Section,
  Status,
  Warnings,
} from '../../components/ui';
import { number, probability, timestamp } from '../../utils/format';

type Covariance = Model<'PositionCovariance'>;
export function diagonalCovariance(
  values: string[],
  frame: Covariance['frame'],
  epoch: string,
): Covariance {
  const sigma = values.map(Number);
  if (
    values.length !== 3 ||
    values.some((value) => !value.trim()) ||
    sigma.some((value) => !Number.isFinite(value) || value <= 0 || value > 1e7)
  )
    throw Error(
      'Supply three positive, finite one-sigma position uncertainties at the analyzed TCA.',
    );
  return {
    matrix_m2: [
      [sigma[0] ** 2, 0, 0],
      [0, sigma[1] ** 2, 0],
      [0, 0, sigma[2] ** 2],
    ],
    frame,
    epoch,
    units: 'm2',
  };
}

export default function Probability() {
  const ui = useUI();
  const encounter = useEncounter();
  const analysis = useAnalysis();
  const science = useScience();
  const [primary, setPrimary] = useState(['', '', '']);
  const [secondary, setSecondary] = useState(['', '', '']);
  const [frame1, setFrame1] = useState<Covariance['frame']>('RTN');
  const [frame2, setFrame2] = useState<Covariance['frame']>('RTN');
  const [radius, setRadius] = useState('');
  const [ack, setAck] = useState(false);
  const [message, setMessage] = useState('');
  const saved = science.liveScenario?.encounterId === ui.encounterId ? science.liveScenario : null;
  const mutation = useMutation({
    mutationFn: (inputs: Model<'ProbabilityInputs'>) =>
      request<Model<'ProbabilityBaselineAnalysis'>>(`/encounters/${ui.encounterId}/analyze`, {
        body: { probability_analysis: true, probability_inputs: inputs },
      }),
    onSuccess: (result, inputs) =>
      science.setLiveScenario({ encounterId: ui.encounterId!, inputs, result }),
  });
  function calculate() {
    setMessage('');
    try {
      if (!ack)
        throw Error('Confirm these are illustrative user-supplied uncertainty assumptions.');
      const epoch = analysis.data?.calculated.tca;
      if (!epoch || !encounter.data) throw Error('First load the analyzed encounter geometry.');
      const hardBody = Number(radius);
      if (!radius.trim() || !Number.isFinite(hardBody) || hardBody <= 0)
        throw Error('Supply a positive combined hard-body radius in meters.');
      const inputs: Model<'ProbabilityInputs'> = {
        kind: 'ASSUMED',
        primary: diagonalCovariance(primary, frame1, epoch),
        secondary: diagonalCovariance(secondary, frame2, epoch),
        combined_hard_body_radius_m: hardBody,
        primary_object_id: encounter.data.object_1_id,
        secondary_object_id: encounter.data.object_2_id,
        correlation: 'INDEPENDENT',
        model_applicable: true,
      };
      mutation.mutate(inputs);
    } catch (error) {
      setMessage((error as Error).message);
    }
  }
  if (!ui.encounterId)
    return (
      <Empty title="Select a close approach">
        Choose a SOCRATES encounter to inspect probability availability.
      </Empty>
    );
  return (
    <>
      <span className="eyebrow">COVARIANCE-AWARE PROBABILITY</span>
      <h3 className="object-title">What can be calculated?</h3>
      <Section title="Live encounter">
        <Metric
          label="SOCRATES MAX_PROB"
          value={probability(encounter.data?.socrates_max_probability)}
        />
        <Metric
          label="Covariance-based Pc"
          value={probability(analysis.data?.probability_analysis.calculated_pc)}
        />
        <Status tone="warning">
          {analysis.data?.probability_analysis.probability_status || 'LOADING'}
        </Status>
        <p className="caption">
          SOCRATES MAX_PROB is a screening metric. It is not calibrated collision probability. Live
          object covariances and radii are unavailable unless supplied separately.
        </p>
      </Section>
      <Section title="Illustrative uncertainty scenario">
        <p className="caption">
          Enter one-sigma position uncertainties for each object at the recalculated TCA (
          {timestamp(analysis.data?.calculated.tca)}). Each object's RTN frame is rotated separately
          by the backend. Diagonal covariance is formed in m²; cross-covariance is omitted under
          your independence assumption.
        </p>
        <Field label="Primary covariance frame">
          <select
            value={frame1}
            onChange={(event) => setFrame1(event.target.value as Covariance['frame'])}
          >
            {['RTN', 'RIC', 'TEME', 'GCRS', 'EME2000', 'GCRF'].map((frame) => (
              <option key={frame}>{frame}</option>
            ))}
          </select>
        </Field>
        <div className="row">
          {primary.map((value, index) => (
            <Field key={index} label={`Primary σ ${['R / X', 'T / Y', 'N / Z'][index]} · m`}>
              <input
                type="number"
                min="0.001"
                step="any"
                value={value}
                onChange={(event) =>
                  setPrimary((old) =>
                    old.map((item, i) => (i === index ? event.target.value : item)),
                  )
                }
              />
            </Field>
          ))}
        </div>
        <Field label="Secondary covariance frame">
          <select
            value={frame2}
            onChange={(event) => setFrame2(event.target.value as Covariance['frame'])}
          >
            {['RTN', 'RIC', 'TEME', 'GCRS', 'EME2000', 'GCRF'].map((frame) => (
              <option key={frame}>{frame}</option>
            ))}
          </select>
        </Field>
        <div className="row">
          {secondary.map((value, index) => (
            <Field key={index} label={`Secondary σ ${['R / X', 'T / Y', 'N / Z'][index]} · m`}>
              <input
                type="number"
                min="0.001"
                step="any"
                value={value}
                onChange={(event) =>
                  setSecondary((old) =>
                    old.map((item, i) => (i === index ? event.target.value : item)),
                  )
                }
              />
            </Field>
          ))}
        </div>
        <Field label="Combined hard-body radius · m">
          <input
            type="number"
            min="0.001"
            step="any"
            value={radius}
            onChange={(event) => setRadius(event.target.value)}
          />
        </Field>
        <label className="checkbox">
          <input type="checkbox" checked={ack} onChange={(event) => setAck(event.target.checked)} />
          <span>
            I assume independent, user-supplied uncertainties and an illustrative combined radius.
          </span>
        </label>
        <button className="primary-button" disabled={mutation.isPending} onClick={calculate}>
          {mutation.isPending ? 'Calculating…' : 'Calculate scenario Pc'}
        </button>
        {message && (
          <p role="alert" className="validation-message">
            {message}
          </p>
        )}
        <ErrorNotice error={mutation.error} />
      </Section>
      {saved && (
        <Section title="ILLUSTRATIVE — USER-SUPPLIED UNCERTAINTY ASSUMPTIONS">
          <Status
            tone={saved.result.probability_analysis.calculated_pc === null ? 'warning' : 'neutral'}
          >
            {saved.result.probability_analysis.probability_status}
          </Status>
          <Metric
            label="Scenario Pc"
            value={probability(saved.result.probability_analysis.calculated_pc)}
          />
          <Metric
            label="Combined radius"
            value={number(saved.inputs.combined_hard_body_radius_m, 2)}
            unit="m"
          />
          <p className="caption">
            Covariance at original analyzed TCA only; no uncertainty propagation. This value is not
            observed operational risk.
          </p>
          <Warnings
            items={[
              ...(saved.result.probability_analysis.assumptions || []),
              ...(saved.result.probability_analysis.warnings || []),
            ]}
          />
        </Section>
      )}
      {analysis.isPending && <Loading>Checking covariance availability…</Loading>}
      <ErrorNotice error={analysis.error} />
    </>
  );
}
