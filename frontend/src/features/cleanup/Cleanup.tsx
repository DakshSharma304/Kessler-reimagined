import {useEffect,useMemo,useState} from 'react';
import {useMutation,useQuery} from '@tanstack/react-query';
import {request,type Model} from '../../api/client';
import {useScience} from '../../stores/science';
import {useVisual} from '../../stores/visual';
import {Empty,ErrorNotice,Field,Loading,Metric,Section,Status,Warnings} from '../../components/ui';
import {number} from '../../utils/format';

type Summary=Model<'ObjectSummary'>;
export function validateCleanup(targets:number,weights:number[],budget:string,costs:string,ids:string[]){
  if(!Number.isInteger(targets)||targets<0||targets>20)throw Error('Target count must be an integer from 0 to 20.');
  if(weights.some(weight=>!Number.isFinite(weight)||weight<0||weight>100)||weights.reduce((a,b)=>a+b,0)<=0)throw Error('Choose finite, nonnegative weights with at least one positive component.');
  if(!budget.trim())return {effort_budget:null,effort_costs:null};
  const value=Number(budget);if(!Number.isFinite(value)||value<0||value>1e9)throw Error('Abstract effort budget must be finite and nonnegative.');
  const entries=costs.split(/[\n,]/).map(v=>v.trim()).filter(Boolean);const parsed:Record<string,number>={};
  for(const entry of entries){const match=/^(\d+):\s*(\d+(?:\.\d+)?)$/.exec(entry);if(!match)throw Error('Enter abstract costs as NORAD_ID: COST, one per line.');const cost=Number(match[2]);if(!Number.isFinite(cost)||cost<0||cost>1e9)throw Error('Each effort cost must be finite and nonnegative.');parsed[match[1]]=cost;}
  if(ids.some(id=>parsed[id]===undefined))throw Error('Supply an abstract effort cost for each selected candidate.');
  return {effort_budget:value,effort_costs:parsed};
}

export default function Cleanup(){
  const science=useScience();const visual=useVisual();const [debris,setDebris]=useState(true);const [rockets,setRockets]=useState(true);
  const [targets,setTargets]=useState(3);const [weights,setWeights]=useState([1,0,0]);const [budget,setBudget]=useState('');const [costs,setCosts]=useState('');
  const [excluded,setExcluded]=useState<string[]>([]);const [message,setMessage]=useState('');
  const catalog=useQuery({queryKey:['cleanup-candidates'],staleTime:300000,queryFn:async({signal})=>{
    const [a,b]=await Promise.all([request<Model<'CatalogPage'>>('/objects?classification=DEBRIS&limit=30',{signal}),request<Model<'CatalogPage'>>('/objects?classification=ROCKET_BODY&limit=20',{signal})]);return {debris:a.items,rockets:b.items,coverage:a.catalog};}});
  const pool=useMemo(()=>[...(debris?catalog.data?.debris || []:[]),...(rockets?catalog.data?.rockets || []:[])], [catalog.data,debris,rockets]);
  const ids=pool.map(v=>v.id);const mutation=useMutation({mutationFn:(body:Model<'CleanupRequest'>)=>request<Model<'CleanupPortfolio'>>('/cleanup/optimize',{body}),
    onSuccess:result=>{science.setCleanup(result);visual.setHighlights(result.selected_objects.map(object=>object.id));}});
  useEffect(()=>()=>visual.setHighlights([]),[]);
  function run(){setMessage('');try{
    if(!ids.length)throw Error('Select at least one available debris classification.');
    const effort=validateCleanup(targets,weights,budget,costs,ids);
    const body:Model<'CleanupRequest'>={candidate_ids:ids,policy:{exposure_weight:weights[0],persistence_weight:weights[1],radar_cross_section_weight:weights[2],
      exposure_saturation_count:10,persistence_saturation_days:30,radar_cross_section_saturation_m2:10},
      constraints:{max_targets:targets,max_candidates:ids.length,excluded_ids:excluded.filter(id=>ids.includes(id)),effort_budget:effort.effort_budget,effort_costs:effort.effort_costs,solver_timeout_seconds:10}};
    mutation.mutate(body);
  }catch(error){setMessage((error as Error).message);}}
  return <><span className="eyebrow">DECISION SUPPORT · ILLUSTRATIVE POLICY</span><h3 className="feature-title">Which debris deserves a closer look?</h3><p className="caption">This ranks a bounded candidate pool for further removal assessment. Scores are an additive proxy, not collisions prevented or a mission plan.</p>
    <Section title="Candidate pool"><div className="row"><label className="checkbox"><input type="checkbox" checked={debris} onChange={event=>setDebris(event.target.checked)}/> Debris</label><label className="checkbox"><input type="checkbox" checked={rockets} onChange={event=>setRockets(event.target.checked)}/> Rocket bodies</label></div><Metric label="Current pool" value={pool.length}/><p className="caption">First 30 debris + 20 rocket bodies from the partial public catalog. Eligibility and unknown properties remain visible.</p>{catalog.isPending&&<Loading/>}<ErrorNotice error={catalog.error} onRetry={()=>catalog.refetch()}/></Section>
    <Field label="Maximum assessment targets"><input type="number" min="0" max="20" step="1" value={targets} onChange={event=>setTargets(Number(event.target.value))}/></Field>
    <Section title="Priority policy weights"><p className="caption">Defaults are illustrative. Unknown positively weighted evidence excludes an object rather than fabricating a value.</p>
      {(['Observed SOCRATES exposure','Modeled persistence','Radar cross section'] as const).map((label,index)=><Field key={label} label={label}><input type="number" min="0" max="100" step=".1" value={weights[index]} onChange={event=>setWeights(old=>old.map((v,i)=>i===index?Number(event.target.value):v))}/></Field>)}</Section>
    <details className="disclosure"><summary>Optional abstract effort budget</summary><Field label="Effort-unit budget" hint="Abstract units supplied by you, not dollars or mission cost."><input type="number" min="0" step="any" value={budget} onChange={event=>setBudget(event.target.value)}/></Field><Field label="Per-object effort costs" hint="Required for all included candidates if budget is set. One NORAD_ID: COST per line."><textarea rows={4} value={costs} onChange={event=>setCosts(event.target.value)}/></Field></details>
    <details className="disclosure"><summary>Exclude candidate objects · {excluded.length}</summary><div className="candidate-list">{pool.map((object:Summary)=><label key={object.id} className="candidate-item"><input type="checkbox" checked={excluded.includes(object.id)} onChange={event=>setExcluded(old=>event.target.checked?[...old,object.id]:old.filter(v=>v!==object.id))}/><span>{object.name}<small>{object.id} · {object.classification.replace('_',' ')}</small></span></label>)}</div></details>
    <button className="primary-button" disabled={!pool.length||mutation.isPending} onClick={run}>{mutation.isPending?'Calculating portfolio…':'Prioritize candidate pool'}</button>
    {message&&<p role="alert" className="validation-message">{message}</p>}<ErrorNotice error={mutation.error}/><p className="caption">SOCRATES exposure covers a limited screening window; shared conjunctions are counted distinctly by the backend, not as independently prevented events.</p>
  </>;
}
