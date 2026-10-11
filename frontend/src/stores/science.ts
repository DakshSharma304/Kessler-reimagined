import { create } from 'zustand';
import type { Model } from '../api/client';

type LiveScenario = {
  encounterId: string;
  inputs: Model<'ProbabilityInputs'>;
  result: Model<'ProbabilityBaselineAnalysis'>;
};
type DecayResult = { objectId: string; result: Model<'PersistenceAnalysis'> };
type Science = {
  liveScenario: LiveScenario | null;
  decay: DecayResult | null;
  cleanup: Model<'CleanupPortfolio'> | null;
  setLiveScenario: (value: LiveScenario | null) => void;
  setDecay: (value: DecayResult | null) => void;
  setCleanup: (value: Model<'CleanupPortfolio'> | null) => void;
};
export const useScience = create<Science>((set) => ({
  liveScenario: null,
  decay: null,
  cleanup: null,
  setLiveScenario: (liveScenario) => set({ liveScenario }),
  setDecay: (decay) => set({ decay }),
  setCleanup: (cleanup) => set({ cleanup }),
}));
