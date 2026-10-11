import {useMemo,useState,useEffect} from 'react';
import {Search,ChevronRight,Satellite} from 'lucide-react';
import {useCatalog,usePositions} from '../../hooks/data';
import {useVisual,type Class} from '../../stores/visual';
import {useUI} from '../../stores/ui';
import {Loading,ErrorNotice,Status} from '../../components/ui';
const categories:{id:Class;label:string}[]=[{id:'PAYLOAD',label:'Payloads'},{id:'DEBRIS',label:'Debris'},{id:'ROCKET_BODY',label:'Rocket bodies'},{id:'UNKNOWN',label:'Unknown'}];
export default function Explorer(){
  const catalog=useCatalog();const positions=usePositions();const visual=useVisual();const ui=useUI();const [search,setSearch]=useState('');
  const items=useMemo(()=>catalog.data?.items.filter(object=>visual.classes.includes(object.classification)&&(!search||`${object.name} ${object.id}`.toLowerCase().includes(search.toLowerCase()))) || [],[catalog.data,visual.classes,search]);
  return <><label className="search-box"><Search size={14}/><input aria-label="Search objects" placeholder="Name or NORAD ID" value={search} onChange={event=>setSearch(event.target.value)}/><kbd>⌕</kbd></label>
    <div className="category-filters">{categories.map(category=><button key={category.id} aria-pressed={visual.classes.includes(category.id)} onClick={()=>visual.setClasses(visual.classes.includes(category.id)?visual.classes.filter(id=>id!==category.id):[...visual.classes,category.id])}><i className={`class-dot ${category.id.toLowerCase()}`}/>{category.label}</button>)}</div>
    <div className="list-caption"><span>{items.length.toLocaleString()} in loaded scope</span><span>{catalog.data?.total.toLocaleString() || '—'} available</span></div>
    {catalog.isPending&&<Loading/>}<ErrorNotice error={catalog.error} onRetry={()=>catalog.refetch()}/><ErrorNotice error={positions.error} onRetry={()=>positions.refetch()}/>
    <div className="object-list">{items.slice(0,100).map(object=><button key={object.id} className={`object-row ${ui.selectedId===object.id?'selected':''}`} onClick={()=>ui.selectObject(object.id)}><span className={`class-dot ${object.classification.toLowerCase()}`}/><span><strong>{object.name}</strong><small>{object.id} · {object.classification.toLowerCase().replace('_',' ')}</small></span><ChevronRight size={13}/></button>)}</div>
    {!catalog.isPending&&!items.length&&<p className="caption">No matching objects in the loaded scope. Catalog-wide search is available in the next explorer integration.</p>}
    <div className="source-note"><Satellite size={12}/><span>CelesTrak · {catalog.data?.catalog.coverage || 'Loading'}<br/>{positions.data?.items.filter(item=>item.propagation_status==='OK').length.toLocaleString() || '—'} propagated markers</span></div><Status tone={catalog.data?.catalog.freshness_status==='STALE'?'warning':'neutral'}>{catalog.data?.catalog.freshness_status || 'Loading'} elements · bounded display scope</Status>
  </>;
}
