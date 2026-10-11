import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {ChevronRight,Search} from 'lucide-react';
import {request,type Model} from '../../api/client';
import {useUI} from '../../stores/ui';
import {useDebounced} from '../../hooks/data';
import {Empty,Loading,ErrorNotice,Field,Status} from '../../components/ui';
import {number,timestamp} from '../../utils/format';
export default function Encounters(){
  const ui=useUI();const [sort,setSort]=useState('minimum_separation');const [offset,setOffset]=useState(0);const term=useDebounced(ui.encounterFilter);
  const filter=term?`&${/^\d+$/.test(term)?'object_id':'name'}=${encodeURIComponent(term)}`:'';
  const query=useQuery({queryKey:['encounters',sort,term,offset],queryFn:({signal})=>request<Model<'EncounterListResponse'>>(`/encounters?sort=${sort}&limit=30&offset=${offset}${filter}`,{signal})});
  return <><label className="search-box"><Search size={14}/><input aria-label="Search encounters" placeholder="Object name or NORAD ID" value={ui.encounterFilter} onChange={event=>{ui.setEncounterFilter(event.target.value);setOffset(0);}}/></label>
    <Field label="Sort approaches"><select value={sort} onChange={event=>{setSort(event.target.value);setOffset(0);}}><option value="minimum_separation">Published separation</option><option value="time">Closest approach time</option><option value="max_probability">SOCRATES screening metric</option><option value="screening">Source screening order</option></select></Field>
    <div className="list-caption"><span>SOCRATES / upcoming</span><Status tone={query.data?.data_status==='STALE_CACHE'?'warning':'neutral'}>{query.data?.data_status || 'Loading'}</Status></div>
    {query.isPending&&<Loading>Retrieving published encounters…</Loading>}<ErrorNotice error={query.error} onRetry={()=>query.refetch()}/>
    <div className="encounter-list">{query.data?.items.map(event=><button className={`encounter-row ${ui.encounterId===event.id?'selected':''}`} key={event.id} onClick={()=>{ui.selectEncounter(event.id);ui.setContextTime(new Date(event.time_of_closest_approach).getTime());}}><div><strong>{event.object_1_name}</strong><small>with {event.object_2_name}</small></div><ChevronRight size={13}/><span className="encounter-distance">{number(event.source_miss_distance_m/1000,3)}<small>km published miss</small></span><time>{timestamp(event.time_of_closest_approach)}</time></button>)}</div>
    {query.data&&!query.data.items.length&&<Empty title="No upcoming approaches">No encounters match the selected source filters.</Empty>}
    <div className="pagination"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-30))}>Previous</button><span>Page {offset/30+1}</span><button disabled={!query.data||query.data.items.length<30} onClick={()=>setOffset(offset+30)}>Next</button></div>
    <p className="caption">Published screening predictions, not confirmed collisions. MAX_PROB is not measured covariance-based Pc.</p><p className="caption">Dataset {timestamp(query.data?.dataset_timestamp)}</p></>;
}
