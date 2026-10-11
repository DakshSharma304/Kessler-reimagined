import {useEffect} from 'react';
import {ArrowUpRight,Focus} from 'lucide-react';
import {useAnalysis,useEncounter,useEncounterPaths} from '../../hooks/data';
import {useUI} from '../../stores/ui';
import {useVisual} from '../../stores/visual';
import {Empty,ErrorNotice,Loading,Metric,Section,Status,Warnings} from '../../components/ui';
import {number,timestamp,probability} from '../../utils/format';
export default function EncounterInspector(){
  const event=useEncounter();const analysis=useAnalysis();const paths=useEncounterPaths();const ui=useUI();const visual=useVisual();
  useEffect(()=>{if(paths.data&&ui.view==='Close approaches'){visual.setPaths(paths.data.trajectories.map((path,index)=>({id:`participant-${path.id}`,path,color:index===0?'#d2e5f4':'#bcb4ab',label:index===0?'Primary':'Secondary'})));visual.setHighlights(paths.data.participant_ids);visual.setComparison('Overlay');}},[paths.data,ui.view]);
  if(!ui.encounterId)return <Empty title="Choose a close approach">Select a published encounter to inspect both objects and the calculated geometry.</Empty>;
  if(event.isPending)return <Loading/>;if(!event.data)return <ErrorNotice error={event.error} onRetry={()=>event.refetch()}/>;
  const data=event.data;const calculated=analysis.data?.calculated;
  return <><Status>{data.source} · {data.data_status}</Status><h3 className="object-title">A closer approach</h3><div className="participant-pair">{[[data.object_1_id,data.object_1_name],[data.object_2_id,data.object_2_name]].map(([id,name],index)=><button key={id} onClick={()=>{ui.selectObject(id);ui.setView('Explore');}}><i style={{background:index===0?'#d2e5f4':'#bcb4ab'}}/><span>{name}<small>NORAD {id}</small></span><ArrowUpRight size={13}/></button>)}</div>
    <Section title="Published prediction"><Metric label="Miss distance" value={number(data.source_miss_distance_m/1000,3)} unit="km"/><Metric label="Relative speed" value={number(data.source_relative_speed_m_s/1000,3)} unit="km/s"/><p className="caption">{timestamp(data.time_of_closest_approach)}</p></Section>
    <Section title="Recalculated geometry">{analysis.isPending?<Loading>Analyzing actual orbital states…</Loading>:<><Status tone={calculated?.status==='COMPLETE'?'neutral':'warning'}>{calculated?.status || 'Unavailable'}</Status><Metric label="Model separation" value={number(calculated?.miss_distance_m===undefined?null:calculated.miss_distance_m/1000,3)} unit={calculated?'km':undefined}/><p className="caption">{timestamp(calculated?.tca)}</p>{analysis.data?.source_model_disagreement&&<p className="scientific-notice">Source/model disagreement. Different GP elements and force models can shift the predicted closest approach.</p>}</>}<ErrorNotice error={analysis.error}/></Section>
    <Section title="Probability availability"><Metric label="SOCRATES screening metric" value={probability(data.socrates_max_probability)}/><p className="caption">Covariance-based Pc: <strong>{analysis.data?.probability_analysis.probability_status.replaceAll('_',' ').toLowerCase() || 'Loading'}</strong></p><p className="caption">Source screening maximum is not calibrated Pc.</p></Section>
    <button className="secondary-button" onClick={()=>ui.focus('encounter')}><Focus size={13}/> Focus approach region</button><button className="primary-button" onClick={()=>ui.setView('Avoidance planner')}>Analyze maneuver <ArrowUpRight size={14}/></button>
    <p className="caption">Actual paths around published TCA. Object markers are enlarged; positions and path distances are not exaggerated.</p><ErrorNotice error={paths.error}/><Warnings items={[...data.warnings,...(analysis.data?.warnings || []),...(paths.data?.warnings || [])]}/></>;
}
