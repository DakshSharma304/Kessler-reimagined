import {create} from 'zustand';
import type {Model} from '../api/client';
export type PlannerInputs={objectId:string;deltaV:number;minLead:number;maxLead:number;target:number;objective:'MAXIMUM_CLEARANCE'|'MINIMUM_DELTA_V';acknowledged:boolean;autoScreen:boolean;screenObjects:number;screenHours:number;screenSeconds:number};
export const initialInputs:PlannerInputs={objectId:'',deltaV:.2,minLead:5,maxLead:15,target:10,objective:'MAXIMUM_CLEARANCE',acknowledged:false,autoScreen:false,screenObjects:128,screenHours:.01,screenSeconds:10};
type Planner={inputs:PlannerInputs;result:Model<'OptimizationResult'>|null;index:number;pending:boolean;error:Error|null;patch:(patch:Partial<PlannerInputs>)=>void;setResult:(result:Model<'OptimizationResult'>|null)=>void;setIndex:(index:number)=>void;setPending:(pending:boolean)=>void;setError:(error:Error|null)=>void};
export const usePlanner=create<Planner>(set=>({inputs:initialInputs,result:null,index:0,pending:false,error:null,patch:patch=>set(state=>({inputs:{...state.inputs,...patch}})),setResult:result=>set({result,index:0}),setIndex:index=>set({index}),setPending:pending=>set({pending}),setError:error=>set({error})}));
export function validatePlanner(input:PlannerInputs){
  const errors:string[]=[];if(!input.acknowledged)errors.push('Confirm the hypothetical maneuver capability.');
  if(![input.deltaV,input.minLead,input.maxLead,input.target].every(Number.isFinite))errors.push('All numeric constraints must be finite.');
  if(input.deltaV<0)errors.push('Delta-v cannot be negative.');if(input.minLead<=0||input.maxLead<=input.minLead||input.maxLead>2880)errors.push('Lead times must be positive, increasing and within48hours.');if(input.target<=0)errors.push('Target separation must be positive.');
  if(input.autoScreen&&(!Number.isInteger(input.screenObjects)||input.screenObjects<1||input.screenObjects>2000||input.screenHours<=0||input.screenHours>24||input.screenSeconds<=0||input.screenSeconds>60))errors.push('Screening requires1–2000objects, a positive horizon≤24hours and time budget≤60seconds.');return errors;
}
export function optimizationBody(encounterId:string,input:PlannerInputs,primaryId:string):Model<'OptimizeRequest'>{
  if(validatePlanner(input).length)throw new Error(validatePlanner(input).join(' '));
  return {encounter_id:encounterId,maneuvering_object_id:input.objectId||primaryId,max_delta_v_m_s:input.deltaV,min_lead_time_minutes:input.minLead,max_lead_time_hours:input.maxLead/60,target_miss_distance_km:input.target,objective:input.objective,hypothetical_capability_assumed:true,search:{time_samples:3,magnitude_samples:3,max_evaluations:80,refinement_evaluations:6,timeout_seconds:20}};
}
