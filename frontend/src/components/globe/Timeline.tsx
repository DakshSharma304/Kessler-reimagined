import {useEffect} from 'react';
import {Play,Pause,RotateCcw,Focus,LocateFixed} from 'lucide-react';
import {useUI} from '../../stores/ui';
import {usePositions} from '../../hooks/data';
export default function Timeline(){
  const ui=useUI();const positions=usePositions();
  useEffect(()=>{if(!ui.playing)return;const interval=setInterval(()=>{if(document.hidden||positions.isFetching)return;const state=useUI.getState();const next=state.time+5000*state.speed;if(next>state.referenceTime+3600000){state.setPlaying(false);return;}state.setTime(next);},5000);return()=>clearInterval(interval);},[ui.playing,ui.speed,positions.isFetching]);
  return <footer className="timeline"><button className="icon-button" aria-label={ui.playing?'Pause playback':'Play playback'} onClick={()=>ui.setPlaying(!ui.playing)}>{ui.playing?<Pause size={17}/>:<Play size={17}/>}</button>
    <div className="time-readout"><span className="eyebrow">PREDICTED POSITION</span><time>{new Date(positions.data?.epoch || ui.time).toISOString().replace('T',' ').slice(0,19)} UTC</time></div>
    <input className="time-slider" type="range" aria-label="Prediction time" min={-3600} max={3600} step={5} value={Math.round((ui.time-ui.referenceTime)/1000)} onChange={event=>{ui.setPlaying(false);ui.setTime(ui.referenceTime+Number(event.target.value)*1000);}}/>
    <select aria-label="Playback speed" value={ui.speed} onChange={event=>ui.setSpeed(Number(event.target.value))}>{[1,5,20].map(speed=><option key={speed} value={speed}>{speed}×</option>)}</select>
    <button className="icon-button" aria-label="Reset time" onClick={()=>{ui.setPlaying(false);ui.setTime(ui.referenceTime);}}><RotateCcw size={16}/></button>
    <button className="icon-button" aria-label="Reset camera" onClick={()=>{ui.setFollow(false);ui.focus('earth');}}><Focus size={17}/></button>
    <button className={`icon-button ${ui.follow?'active':''}`} aria-label={ui.follow?'Exit follow mode':'Follow selected object'} disabled={!ui.selectedId} onClick={()=>{ui.setFollow(!ui.follow);ui.focus('object');}}><LocateFixed size={17}/></button>
    <span className="timeline-note">Backend samples · 5 s refresh · ITRS / km</span></footer>;
}
