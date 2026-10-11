import { useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, Layers3, PanelLeftClose, PanelRightClose, Radio, Search } from 'lucide-react';
import {lazy,Suspense,useEffect} from 'react';
import Explorer from './features/explorer/Explorer';
import Timeline from './components/globe/Timeline';
import {usePositions,useObjectOrbit} from './hooks/data';
import ObjectInspector from './features/explorer/ObjectInspector';
import Encounters from './features/encounters/Encounters';
import EncounterInspector from './features/encounters/EncounterInspector';
import Planner from './features/maneuvers/Planner';
import Results from './features/maneuvers/Results';
import Decay from './features/decay/Decay';
import DecayResult from './features/decay/DecayResult';
import Cleanup from './features/cleanup/Cleanup';
import CleanupResult from './features/cleanup/CleanupResult';
import Methods from './features/methods/Methods';
const Globe=lazy(()=>import('./components/globe/Globe'));
import { request, type Model } from './api/client';
import { useUI, views } from './stores/ui';
import {useVisual} from './stores/visual';
import { Empty, ErrorNotice, Loading, Status } from './components/ui';

export default function App(){
  const ui=useUI();const reduced=useReducedMotion();const positions=usePositions();const orbit=useObjectOrbit();
  useEffect(()=>{if(!['Close approaches','Avoidance planner'].includes(ui.view))useVisual.getState().setPaths([]);if(['Cleanup planner','Data & methods'].includes(ui.view))useUI.getState().focus('earth');},[ui.view]);
  const health=useQuery({queryKey:['health'],queryFn:({signal})=>request<Model<'HealthResponse'>>('/health',{signal}),refetchInterval:60000});
  return <main className="app-shell">
    <header className="topbar"><a className="brand" href="#" aria-label="Kessler home" onClick={()=>ui.setView('Explore')}><span className="brand-symbol">k</span><span>KESSLER<small>ORBITAL INTELLIGENCE</small></span></a>
      <nav aria-label="Primary navigation">{views.map(view=><button key={view} className={ui.view===view?'nav-item active':'nav-item'} onClick={()=>ui.setView(view)}>{view}</button>)}</nav>
      <div className="connection"><Radio size={13}/><span>{health.isSuccess?'Backend connected':health.isPending?'Connecting':'Backend offline'}</span></div></header>
    <div className="workspace">
      <div className="visual-stage"><div className="stage-top"><span>EARTH / ORBITAL ENVIRONMENT</span><Status>Predicted positions · UTC</Status></div><Suspense fallback={<div className="stage-placeholder"><Loading>Initializing 3D workspace…</Loading></div>}><Globe/></Suspense><div className="globe-caption"><span>WGS84 / EARTH-FIXED</span><small>Markers enlarged for visibility · partial catalog</small></div></div>
      <AnimatePresence>{ui.leftOpen&&<motion.aside className="left-panel panel" aria-label="Explorer" initial={{opacity:0,x:reduced?0:-12}} animate={{opacity:1,x:0}} exit={{opacity:0,x:reduced?0:-12}}><div className="panel-heading"><div><span className="eyebrow">WORKSPACE</span><h2>{ui.view}</h2></div><button className="icon-button" aria-label="Close explorer" onClick={()=>ui.togglePanel('left')}><PanelLeftClose size={17}/></button></div><div className="panel-content">{ui.view==='Explore'?<Explorer/>:ui.view==='Close approaches'?<Encounters/>:ui.view==='Avoidance planner'?<Planner/>:ui.view==='Orbital decay'?<Decay/>:ui.view==='Cleanup planner'?<Cleanup/>:<Methods/>}<ErrorNotice error={health.error} onRetry={()=>health.refetch()}/>{health.isPending&&<Loading/>}</div><footer className="panel-footer"><Layers3 size={14}/>Backend is the scientific source of truth</footer></motion.aside>}</AnimatePresence>
      <AnimatePresence>{ui.rightOpen&&ui.view!=='Data & methods'&&<motion.aside className={`right-panel panel ${!ui.selectedId&&!ui.encounterId?'inspector-empty':''}`} aria-label="Inspector" initial={{opacity:0,x:reduced?0:12}} animate={{opacity:1,x:0}} exit={{opacity:0,x:reduced?0:12}}><div className="panel-heading"><div><span className="eyebrow">CONTEXT</span><h2>Inspector</h2></div><button className="icon-button" aria-label="Close inspector" onClick={()=>ui.togglePanel('right')}><PanelRightClose size={17}/></button></div><div className="panel-content">{ui.view==='Close approaches'?<EncounterInspector/>:ui.view==='Avoidance planner'?<Results/>:ui.view==='Orbital decay'?<DecayResult/>:ui.view==='Cleanup planner'?<CleanupResult/>:ui.selectedId?<ObjectInspector/>:<Empty title="A closer perspective">Select an orbital object or encounter to inspect its source data and available analyses.</Empty>}<div className="quiet-note"><ArrowUpRight size={16}/><span>Source data. Explicit assumptions.<br/>No implied operational safety.</span></div></div></motion.aside>}</AnimatePresence>
      {!ui.leftOpen&&<button className="restore-panel restore-left icon-button" aria-label="Open explorer" onClick={()=>ui.togglePanel('left')}><Search size={18}/></button>}
      {!ui.rightOpen&&ui.view!=='Data & methods'&&<button className="restore-panel restore-right icon-button" aria-label="Open inspector" onClick={()=>ui.togglePanel('right')}><PanelRightClose size={18}/></button>}
    </div><Timeline/>
  </main>;
}
