import { useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, Globe2, Layers3, PanelLeftClose, PanelRightClose, Radio, Search } from 'lucide-react';
import { request, type Model } from './api/client';
import { useUI, views } from './stores/ui';
import { Empty, ErrorNotice, Loading, Status } from './components/ui';

export default function App(){
  const ui=useUI();const reduced=useReducedMotion();
  const health=useQuery({queryKey:['health'],queryFn:({signal})=>request<Model<'HealthResponse'>>('/health',{signal}),refetchInterval:60000});
  return <main className="app-shell">
    <header className="topbar"><a className="brand" href="#" aria-label="Kessler home" onClick={()=>ui.setView('Explore')}><span className="brand-symbol">k</span><span>KESSLER<small>ORBITAL INTELLIGENCE</small></span></a>
      <nav aria-label="Primary navigation">{views.map(view=><button key={view} className={ui.view===view?'nav-item active':'nav-item'} onClick={()=>ui.setView(view)}>{view}</button>)}</nav>
      <div className="connection"><Radio size={13}/><span>{health.isSuccess?'Backend connected':health.isPending?'Connecting':'Backend offline'}</span></div></header>
    <div className="workspace">
      <div className="visual-stage"><div className="stage-top"><span>EARTH / ORBITAL ENVIRONMENT</span><Status>Predicted positions · UTC</Status></div><div className="stage-placeholder"><Globe2 size={108} strokeWidth={.5}/><p>Orbital workspace</p><span>Visualization initializes after the verified API connection.</span></div></div>
      <AnimatePresence>{ui.leftOpen&&<motion.aside className="left-panel panel" aria-label="Explorer" initial={{opacity:0,x:reduced?0:-12}} animate={{opacity:1,x:0}} exit={{opacity:0,x:reduced?0:-12}}><div className="panel-heading"><div><span className="eyebrow">WORKSPACE</span><h2>{ui.view}</h2></div><button className="icon-button" aria-label="Close explorer" onClick={()=>ui.togglePanel('left')}><PanelLeftClose size={17}/></button></div><div className="panel-content"><Empty title={ui.view==='Explore'?'Explore the orbital environment':'Your analysis workspace'}>Live data and scientific tools are provided by the connected backend.</Empty><ErrorNotice error={health.error} onRetry={()=>health.refetch()}/>{health.isPending&&<Loading/>}</div><footer className="panel-footer"><Layers3 size={14}/>Backend is the scientific source of truth</footer></motion.aside>}</AnimatePresence>
      <AnimatePresence>{ui.rightOpen&&<motion.aside className="right-panel panel" aria-label="Inspector" initial={{opacity:0,x:reduced?0:12}} animate={{opacity:1,x:0}} exit={{opacity:0,x:reduced?0:12}}><div className="panel-heading"><div><span className="eyebrow">CONTEXT</span><h2>Inspector</h2></div><button className="icon-button" aria-label="Close inspector" onClick={()=>ui.togglePanel('right')}><PanelRightClose size={17}/></button></div><div className="panel-content"><Empty title="A closer perspective">Select an orbital object or encounter to inspect its source data and available analyses.</Empty><div className="quiet-note"><ArrowUpRight size={16}/><span>Real observations. Explicit assumptions.<br/>No implied operational safety.</span></div></div></motion.aside>}</AnimatePresence>
      {!ui.leftOpen&&<button className="restore-panel restore-left icon-button" aria-label="Open explorer" onClick={()=>ui.togglePanel('left')}><Search size={18}/></button>}
      {!ui.rightOpen&&<button className="restore-panel restore-right icon-button" aria-label="Open inspector" onClick={()=>ui.togglePanel('right')}><PanelRightClose size={18}/></button>}
    </div><footer className="timeline"><Globe2 size={18}/><div><span className="eyebrow">PREDICTION EPOCH</span><time>{new Date(ui.time).toISOString().replace('T',' ').slice(0,19)} UTC</time></div><span className="timeline-note">Earth-fixed ITRS · kilometers · partial catalog coverage</span></footer>
  </main>;
}
