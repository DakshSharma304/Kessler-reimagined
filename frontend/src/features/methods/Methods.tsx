import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { request, type Model } from '../../api/client';
import {
  ErrorNotice,
  Field,
  Loading,
  Metric,
  Section,
  Status,
  Warnings,
} from '../../components/ui';
import { number, probability, timestamp } from '../../utils/format';

const cases = [
  '000020580_conj_000022015_20210315_212955_20210313_065123',
  '000025994_conj_000037558_20210324_151047_20210323_154356',
  '000028485_conj_000044777_20220407_231108_20220406_140506',
  '000025994_conj_000026980_20220928_223445_20220924_220647',
];
export default function Methods() {
  const [selected, setSelected] = useState(cases[1]);
  const catalog = useQuery({
    queryKey: ['catalog-status'],
    queryFn: ({ signal }) => request<Model<'CatalogStatusResponse'>>('/catalog/status', { signal }),
  });
  const service = useQuery({
    queryKey: ['service-status'],
    queryFn: ({ signal }) => request<Model<'StatusResponse'>>('/status', { signal }),
  });
  const weather = useQuery({
    queryKey: ['weather-status'],
    queryFn: ({ signal }) =>
      request<Model<'SpaceWeatherStatus'>>('/space-weather/status', { signal }),
  });
  const benchmark = useMutation({
    mutationFn: (reference_case: string) =>
      request<Model<'ReferenceComparison'>>('/probability/calculate', {
        body: { reference_case, independent_benchmark: true },
      }),
  });
  return (
    <>
      <span className="eyebrow">MODEL & SOURCE PROVENANCE</span>
      <h3 className="feature-title">Understand the calculation</h3>
      <p className="caption">
        Source dates, partial coverage, numerical assumptions and validation cases remain separate
        from live encounter risk.
      </p>
      <Section title="Catalog & screening">
        <Status tone={catalog.data?.catalog?.freshness_status === 'STALE' ? 'warning' : 'neutral'}>
          {catalog.data?.catalog?.freshness_status || catalog.data?.status || 'Loading'}
        </Status>
        <Metric
          label="Catalog objects available"
          value={catalog.data?.catalog?.objects_available ?? 'Unavailable'}
        />
        <Metric
          label="SOCRATES encounters loaded"
          value={service.data?.encounters_loaded ?? 'Unavailable'}
        />
        <p className="caption">
          Assembled {timestamp(catalog.data?.catalog?.assembled_at)} · newest GP epoch{' '}
          {timestamp(catalog.data?.catalog?.newest_element_epoch ?? undefined)}. Public catalog and
          SOCRATES cover different populations/windows. GP positions are predictions, not
          instantaneous observations.
        </p>
        <Warnings
          items={[
            ...(catalog.data?.catalog?.coverage_limitations || []),
            ...(service.data?.warnings || []),
          ]}
        />
      </Section>
      <Section title="Coordinate and numerical contract">
        <p className="caption">
          3D positions and paths arrive from backend SGP4/Astropy in Earth-fixed ITRS, kilometers,
          UTC ISO timestamps. Display maps (x,y,z) to Three.js (x,z,−y), scaled by 6378.137 km Earth
          radius. Maneuver paths come from the existing GCRS gravity/J2 simulator before backend
          conversion to ITRS.
        </p>
        <p className="caption">
          Object markers are visually enlarged. Time scrubbing uses nearest returned trajectory
          samples; no orbital propagation runs in the browser.
        </p>
      </Section>
      <Section title="Collision probability">
        <p className="caption">
          SOCRATES MAX_PROB screens conjunctions; it is not covariance-aware Pc. Actual Pc requires
          supplied position covariance and combined hard-body radius at the analyzed TCA. An assumed
          scenario remains hypothetical; independent uncertainties and a fixed-covariance maneuver
          comparison require explicit selection.
        </p>
        <Field label="Historical NASA CARA benchmark">
          <select value={selected} onChange={(event) => setSelected(event.target.value)}>
            {cases.map((name) => (
              <option key={name} value={name}>
                {name.slice(0, 9)} / {name.slice(19, 28)} · {name.slice(-24, -16)}
              </option>
            ))}
          </select>
        </Field>
        <button
          className="secondary-button"
          disabled={benchmark.isPending}
          onClick={() => benchmark.mutate(selected)}
        >
          {benchmark.isPending
            ? 'Calculating historical benchmark…'
            : 'Compare with NASA reference'}
        </button>
        {benchmark.data && (
          <>
            <Status>HISTORICAL REFERENCE ONLY</Status>
            <Metric
              label="Published Pc2D"
              value={probability(benchmark.data.published_reference_pc)}
            />
            <Metric
              label="Kessler calculated Pc"
              value={probability(benchmark.data.calculated_pc)}
            />
            <Metric
              label="Absolute difference"
              value={
                benchmark.data.numerical_difference === null
                  ? 'Unavailable'
                  : Math.abs(benchmark.data.numerical_difference).toExponential(3)
              }
            />
            <Metric
              label="Relative difference"
              value={
                benchmark.data.relative_difference === null
                  ? 'Unavailable'
                  : benchmark.data.relative_difference.toExponential(3)
              }
            />
            <p className="caption">
              Reference CDM TCA {timestamp(benchmark.data.original_tca)} ·{' '}
              {benchmark.data.reference_model}. Independent-model benchmark explicitly omits known
              common-density correlations; not an operational Pc for this historical conjunction.
            </p>
            <a
              className="source-link"
              href={benchmark.data.reference_url}
              target="_blank"
              rel="noreferrer"
            >
              NASA CARA source ↗
            </a>
            <Warnings items={[...benchmark.data.assumptions, ...benchmark.data.warnings]} />
          </>
        )}
        <ErrorNotice error={benchmark.error} />
      </Section>
      <Section title="Atmosphere & debris policy">
        <Status tone={weather.data?.status === 'NOT_LOADED' ? 'warning' : 'neutral'}>
          Space weather: {weather.data?.status || 'Loading'}
        </Status>
        <p className="caption">
          Persistence uses actual NRLMSIS 2.1 drag integrations for a finite horizon.
          Low/nominal/high settings are scenarios, not uncertainty probabilities. Modeled boundary
          crossing is a cutoff, not impact time.
        </p>
        <p className="caption">
          Cleanup scores use chosen exposure, persistence and radar cross-section weights. Missing
          evidence stays unavailable. Effort units are abstract; neither removal feasibility nor
          dollars are estimated.
        </p>
        <Warnings items={weather.data?.warnings} />
      </Section>
      <Section title="Visual assets">
        <p className="caption">
          Earth: NASA Earth Observatory Blue Marble 2048×1024 (public domain). Fallback continents:
          Natural Earth 1:110m (public domain). Source details ship in
          frontend/public/ATTRIBUTION.md.
        </p>
      </Section>
      {(catalog.isPending || weather.isPending || service.isPending) && <Loading />}
      <ErrorNotice error={catalog.error} onRetry={() => catalog.refetch()} />
      <ErrorNotice error={service.error} onRetry={() => service.refetch()} />
      <ErrorNotice error={weather.error} onRetry={() => weather.refetch()} />
    </>
  );
}
