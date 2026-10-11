import { useMutation } from '@tanstack/react-query';
import { useEffect } from 'react';
import { ArrowUpRight, Loader2, SlidersHorizontal } from 'lucide-react';
import { request, type Model } from '../../api/client';
import { useEncounter } from '../../hooks/data';
import { useUI } from '../../stores/ui';
import {
  usePlanner,
  validatePlanner,
  optimizationBody,
  type PlannerInputs,
} from '../../stores/planner';
import { Empty, ErrorNotice, Field, Status } from '../../components/ui';
export default function Planner() {
  const event = useEncounter();
  const ui = useUI();
  const state = usePlanner();
  const inputs = state.inputs;
  const errors = validatePlanner(inputs);
  useEffect(() => {
    if (
      event.data &&
      inputs.objectId &&
      ![event.data.object_1_id, event.data.object_2_id].includes(inputs.objectId)
    )
      state.patch({ objectId: '' });
  }, [event.data, inputs.objectId]);
  const mutation = useMutation({
    mutationFn: () =>
      request<Model<'OptimizationResult'>>(`/encounters/${ui.encounterId}/optimize`, {
        body: optimizationBody(ui.encounterId!, inputs, event.data!.object_1_id),
      }),
    onMutate: () => {
      state.setResult(null);
      state.setError(null);
      state.setPending(true);
    },
    onSuccess: (result) => {
      state.setResult(result);
      ui.openPanel('right');
    },
    onError: (error) => state.setError(error),
    onSettled: () => state.setPending(false),
  });
  if (!ui.encounterId || !event.data)
    return (
      <Empty title="Start with a close approach">
        Choose a real encounter first.
        <button className="primary-button" onClick={() => ui.setView('Close approaches')}>
          Browse close approaches <ArrowUpRight size={13} />
        </button>
      </Empty>
    );
  function value(key: keyof PlannerInputs, event: React.ChangeEvent<HTMLInputElement>) {
    state.patch({ [key]: event.target.value === '' ? NaN : Number(event.target.value) });
  }
  return (
    <>
      <p className="caption">
        Find the best evaluated maneuver under your constraints. Results are hypothetical, not
        flight commands.
      </p>
      <Field label="Maneuvering object">
        <select
          value={inputs.objectId || event.data.object_1_id}
          onChange={(event) => state.patch({ objectId: event.target.value })}
        >
          <option value={event.data.object_1_id}>{event.data.object_1_name}</option>
          <option value={event.data.object_2_id}>{event.data.object_2_name}</option>
        </select>
      </Field>
      <Field label="Maximum delta-v · m/s">
        <input
          type="number"
          step="0.01"
          min="0"
          value={Number.isFinite(inputs.deltaV) ? inputs.deltaV : ''}
          onChange={(event) => value('deltaV', event)}
        />
        <input
          aria-label="Delta-v slider"
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={Math.min(inputs.deltaV, 1)}
          onChange={(event) => value('deltaV', event)}
        />
      </Field>
      <div className="row">
        <Field label="Min lead · minutes">
          <input
            type="number"
            min=".1"
            value={Number.isFinite(inputs.minLead) ? inputs.minLead : ''}
            onChange={(event) => value('minLead', event)}
          />
        </Field>
        <Field label="Max lead · minutes">
          <input
            type="number"
            min=".1"
            max="2880"
            value={Number.isFinite(inputs.maxLead) ? inputs.maxLead : ''}
            onChange={(event) => value('maxLead', event)}
          />
        </Field>
      </div>
      <Field
        label="Target separation · km"
        hint="A modeled target, not an operational safety threshold."
      >
        <input
          type="number"
          min=".001"
          step=".1"
          value={Number.isFinite(inputs.target) ? inputs.target : ''}
          onChange={(event) => value('target', event)}
        />
      </Field>
      <Field label="Objective">
        <select
          value={inputs.objective}
          onChange={(event) =>
            state.patch({ objective: event.target.value as PlannerInputs['objective'] })
          }
        >
          <option value="MAXIMUM_CLEARANCE">Maximum modeled clearance</option>
          <option value="MINIMUM_DELTA_V">Minimum delta-v meeting target</option>
        </select>
      </Field>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={inputs.acknowledged}
          onChange={(event) => state.patch({ acknowledged: event.target.checked })}
        />
        <span>I explicitly assume this object can perform the hypothetical maneuver.</span>
      </label>
      <details className="disclosure">
        <summary>
          <SlidersHorizontal size={12} /> Secondary screening settings
        </summary>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={inputs.autoScreen}
            onChange={(event) => state.patch({ autoScreen: event.target.checked })}
          />
          <span>Screen selected alternatives automatically</span>
        </label>
        <Field label="Screening object limit">
          <input
            type="number"
            min="1"
            max="2000"
            value={inputs.screenObjects}
            onChange={(event) => value('screenObjects', event)}
          />
        </Field>
        <Field label="Post-TCA horizon · hours">
          <input
            type="number"
            min=".001"
            max="24"
            step=".01"
            value={inputs.screenHours}
            onChange={(event) => value('screenHours', event)}
          />
        </Field>
        <Field label="Screening time budget · seconds">
          <input
            type="number"
            min="1"
            max="60"
            value={inputs.screenSeconds}
            onChange={(event) => value('screenSeconds', event)}
          />
        </Field>
        <p className="caption">
          Public coverage is partial. A bounded search can remain INCOMPLETE.
        </p>
      </details>
      <button
        className="primary-button"
        disabled={errors.length > 0 || state.pending}
        onClick={() => mutation.mutate()}
      >
        {state.pending ? (
          <>
            <Loader2 className="spin" size={15} /> Evaluating maneuvers…
          </>
        ) : (
          <>
            Find best maneuvers <ArrowUpRight size={14} />
          </>
        )}
      </button>
      {!!errors.length && (
        <p className="validation-message" role="status">
          {errors.join(' ')}
        </p>
      )}
      <ErrorNotice error={state.error} />
      <p className="caption">
        Bounded deterministic search · up to80evaluations · no global optimum guarantee.
      </p>
      <button className="text-button" onClick={() => ui.setView('Close approaches')}>
        Change encounter
      </button>
    </>
  );
}
