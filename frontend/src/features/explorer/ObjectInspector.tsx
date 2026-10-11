import {ArrowUpRight,Orbit,Activity} from 'lucide-react';
import {useObjectInfo,useObjectOrbit} from '../../hooks/data';
import {useUI} from '../../stores/ui';
import {ErrorNotice,Loading,Metric,Section,Status,Warnings} from '../../components/ui';
import {number,timestamp} from '../../utils/format';
export default function ObjectInspector(){
  const info=useObjectInfo();const orbit=useObjectOrbit();const ui=useUI();if(info.isPending)return <Loading>Retrieving object metadata…</Loading>;
  if(!info.data)return <ErrorNotice error={info.error} onRetry={()=>info.refetch()}/>;
  const data=info.data;const object=data.object;
  return <><span className="eyebrow">NORAD {object.id}</span><h3 className="object-title">{object.name}</h3><Status>{object.classification.replace('_',' ')} · {data.orbit.data_status}</Status>
    <Section title="Orbit"><Metric label="Perigee" value={number(object.perigee_km,1)} unit={object.perigee_km!==null?'km':undefined}/><Metric label="Apogee" value={number(object.apogee_km,1)} unit={object.apogee_km!==null?'km':undefined}/><Metric label="Inclination" value={number(object.inclination_deg,2)} unit="°"/><Metric label="Mean motion" value={number(data.orbit.elements.mean_motion_rev_day,4)} unit="rev/day"/></Section>
    <Section title="Source & epoch"><p className="caption">{data.orbit.source}<br/>Element epoch {timestamp(object.element_epoch)}<br/>Retrieved {timestamp(data.orbit.fetched_at)}</p><a className="source-link" href={data.orbit.source_url} target="_blank" rel="noreferrer">View source <ArrowUpRight size={12}/></a></Section>
    <Section title="Physical properties"><Metric label="Mass" value={number(data.metadata?.mass_kg)} unit={data.metadata?.mass_kg!=null?'kg':undefined}/><Metric label="Aerodynamic area" value={number(data.metadata?.aerodynamic_area_m2)} unit={data.metadata?.aerodynamic_area_m2!=null?'m²':undefined}/><p className="caption">Unknown properties stay unavailable; radar cross section is not aerodynamic area.</p></Section>
    <button className="secondary-button" onClick={()=>ui.focus('object')}><Orbit size={13}/> Focus orbit</button><button className="primary-button" onClick={()=>{ui.setEncounterFilter(object.id);ui.setView('Close approaches');}}>Related close approaches <ArrowUpRight size={14}/></button><button className="text-button" onClick={()=>ui.setView('Orbital decay')}><Activity size={12}/> Analyze orbital persistence</button>
    {orbit.isPending?<Loading>Retrieving path…</Loading>:<p className="caption">{orbit.data?.samples.length || 0} actual path samples · ITRS / km</p>}<ErrorNotice error={orbit.error}/><Warnings items={[...data.warnings,...(orbit.data?.warnings || [])]}/></>;
}
