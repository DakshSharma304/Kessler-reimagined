import type {Model} from '../api/client';
export function closestSample(path:Model<'ObjectTrajectory'>,time:number){
  const samples=path.samples;
  if(!samples.length||time<new Date(samples[0].epoch).getTime()||time>new Date(samples[samples.length-1].epoch).getTime())return null;
  const nearest=samples.reduce((nearest,sample)=>Math.abs(new Date(sample.epoch).getTime()-time)<Math.abs(new Date(nearest.epoch).getTime()-time)?sample:nearest);
  return nearest.propagation_status==='OK'&&nearest.position_km?nearest:null;
}
