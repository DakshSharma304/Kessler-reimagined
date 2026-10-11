import { useScience } from '../../stores/science';
import { useUI } from '../../stores/ui';
import { Empty, Metric, Section, Status, Warnings } from '../../components/ui';
import { number, timestamp } from '../../utils/format';
export default function CleanupResult() {
  const data = useScience((s) => s.cleanup);
  const select = useUI((s) => s.selectObject);
  const setView = useUI((s) => s.setView);
  if (!data)
    return (
      <Empty title="No portfolio yet">
        Set an assessment budget and run the transparent priority policy.
      </Empty>
    );
  const scores = new Map(data.priority_ranking.map((score) => [score.id, score]));
  return (
    <>
      <span className="eyebrow">MODELED PRIORITY · NOT A MISSION PLAN</span>
      <h3 className="object-title">Candidates for assessment</h3>
      <Status tone={data.status === 'OPTIMAL_WITHIN_CANDIDATE_POOL' ? 'neutral' : 'warning'}>
        {data.status}
      </Status>
      <Section title="Resource outcome">
        <Metric label="Selected" value={data.selected_objects.length} />
        <Metric label="Total priority proxy" value={number(data.total_priority_proxy, 4)} />
        <Metric
          label="Abstract effort spent"
          value={number(data.total_abstract_resource_expenditure, 2)}
        />
        <Metric label="Budget remaining" value={number(data.budget_remaining, 2)} />
        <Metric label="Targets remaining" value={data.targets_remaining} />
        <p className="caption">
          Only evidence inside the chosen candidate pool and source coverage informed this ranking.
        </p>
      </Section>
      <Section title="Selected objects">
        {data.selected_objects.length ? (
          data.selected_objects.map((object, index) => {
            const score = scores.get(object.id);
            return (
              <button
                className="ranked-object"
                key={object.id}
                onClick={() => {
                  setView('Explore');
                  select(object.id);
                }}
              >
                <span className="rank-number">{String(index + 1).padStart(2, '0')}</span>
                <span>
                  <strong>{object.name}</strong>
                  <small>
                    NORAD {object.id} · {object.classification.replace('_', ' ')}
                  </small>
                  <small>
                    Score {number(score?.score, 4)} · {score?.status}
                  </small>
                  <small>GP epoch {timestamp(object.element_epoch)}</small>
                </span>
              </button>
            );
          })
        ) : (
          <p className="caption">
            No target selected under the stated budget, eligibility and evidence requirements.
          </p>
        )}
      </Section>
      <Section title="Score breakdown">
        {data.priority_ranking.slice(0, 12).map((score) => (
          <details key={score.id} className="disclosure">
            <summary>
              {score.id} · {score.status} · {number(score.score, 4)}
            </summary>
            {Object.entries(score.components).map(([key, value]) => {
              const row = value as {
                value: number | null;
                weight: number;
                contribution: number | null;
                status: string;
              };
              return (
                <p key={key}>
                  {key.replaceAll('_', ' ')}: {number(row.value, 3)} · weight{' '}
                  {number(row.weight, 2)} · contribution {number(row.contribution, 3)} ·{' '}
                  {row.status}
                </p>
              );
            })}
            {score.reasons.map((reason) => (
              <p key={reason}>{reason}</p>
            ))}
          </details>
        ))}
      </Section>
      <Section title="Evidence & exclusions">
        <Metric
          label="Distinct screening encounters represented"
          value={data.unique_screening_encounters_represented}
        />
        <Metric label="Excluded objects" value={Object.keys(data.excluded_objects).length} />
        <p className="caption">
          Unknown physical mass and removal cost remain unknown. More metadata does not
          automatically increase priority.
        </p>
        <Warnings
          items={[
            ...data.model_assumptions,
            ...data.warnings,
            ...Object.entries(data.excluded_objects)
              .slice(0, 8)
              .map(([id, reasons]) => `${id}: ${reasons.join('; ')}`),
          ]}
        />
      </Section>
    </>
  );
}
