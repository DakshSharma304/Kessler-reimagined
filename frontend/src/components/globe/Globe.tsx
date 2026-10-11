import {Canvas,useFrame,useThree} from '@react-three/fiber';
import {OrbitControls,Line,Html} from '@react-three/drei';
import {Component,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {useReducedMotion} from 'framer-motion';
import * as THREE from 'three';
import type {OrbitControls as Controls} from 'three-stdlib';
import {usePositions,useObjectOrbit} from '../../hooks/data';
import {useUI} from '../../stores/ui';
import {useVisual,type Class} from '../../stores/visual';
import {toWorld} from '../../utils/coordinates';
import {usePlanner} from '../../stores/planner';
import {closestSample} from '../../utils/samples';
import {ErrorNotice} from '../ui';

const colors:Record<Class,string>={PAYLOAD:'#b4d4ea',DEBRIS:'#bdb3a8',ROCKET_BODY:'#ddd2b8',UNKNOWN:'#747d88'};
const vertex=`attribute vec3 color; varying vec3 vColor; void main(){vColor=color;vec4 p=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*p;gl_PointSize=clamp(7.0/-p.z,2.0,5.0);}`;
const fragment=`varying vec3 vColor;void main(){float d=distance(gl_PointCoord,vec2(.5));if(d>.5)discard;gl_FragColor=vec4(vColor,1.-smoothstep(.1,.5,d));}`;

function Earth(){
  const [texture,setTexture]=useState<THREE.Texture|null>(null);
  useEffect(()=>{
    let cancelled=false;const resources:THREE.Texture[]=[];
    async function fallback(){
      const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=512;const ctx=canvas.getContext('2d');if(!ctx)return;
      ctx.fillStyle='#142b3e';ctx.fillRect(0,0,1024,512);
      try{const geo=await fetch('/maps/land.geojson').then(r=>r.json());ctx.fillStyle='#627067';
        for(const feature of geo.features){const polygons=feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates;
          for(const polygon of polygons){ctx.beginPath();for(const ring of polygon){ring.forEach(([lon,lat]:number[],i:number)=>{const x=(lon+180)/360*1024,y=(90-lat)/180*512;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.closePath();}ctx.fill('evenodd');}}
      }catch{/* A failed local fallback map still leaves a navigable globe. */}
      const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;resources.push(map);if(!cancelled)setTexture(map);
    }
    const loaded=new THREE.TextureLoader().load('/textures/earth.png',map=>{map.colorSpace=THREE.SRGBColorSpace;map.anisotropy=4;if(!cancelled)setTexture(map);},undefined,()=>{void fallback();});resources.push(loaded);
    return()=>{cancelled=true;resources.forEach(resource=>resource.dispose());};
  },[]);
  return <><mesh><sphereGeometry args={[1,96,64]}/><meshPhongMaterial key={texture?.uuid || 'loading-earth'} map={texture} color={texture?'#d8e4ee':'#1a3040'} shininess={8} specular="#293943"/></mesh>
    <mesh><sphereGeometry args={[1.018,64,48]}/><shaderMaterial transparent side={THREE.BackSide} depthWrite={false} uniforms={{glow:{value:new THREE.Color('#789ebe')}}} vertexShader={`varying vec3 n;varying vec3 view;void main(){vec4 p=modelViewMatrix*vec4(position,1.);n=normalize(normalMatrix*normal);view=normalize(-p.xyz);gl_Position=projectionMatrix*p;}`} fragmentShader={`varying vec3 n;varying vec3 view;uniform vec3 glow;void main(){float rim=pow(1.-abs(dot(n,view)),3.);gl_FragColor=vec4(glow,rim*.19);}`}/></mesh></>;
}
function Scene(){
  const positions=usePositions();const orbit=useObjectOrbit();const selected=useUI(s=>s.selectedId);const ui=useUI();const visual=useVisual();const reduced=useReducedMotion();
  const controls=useRef<Controls>(null);const {camera,gl,invalidate}=useThree();const goal=useRef<THREE.Vector3|null>(null);const target=useRef(new THREE.Vector3());const follow=useRef(ui.follow);const lastFocus=useRef(-1);
  const display=useMemo(()=>positions.data?.items.filter(item=>item.propagation_status==='OK' && item.position_km && visual.classes.includes(item.classification)) || [],[positions.data,visual.classes]);
  const visibleLayers=visual.paths.filter(layer=>visual.comparison==='Overlay'||(visual.comparison==='Baseline'?layer.label!=='Maneuvered':layer.label!=='Baseline'));
  const geometry=useMemo(()=>{const shape=new THREE.BufferGeometry();const points:number[]=[],tints:number[]=[];
    for(const item of display){points.push(...toWorld(item.position_km!));const color=new THREE.Color(colors[item.classification]);if(visual.highlightIds.length && !visual.highlightIds.includes(item.id))color.multiplyScalar(.22);tints.push(color.r,color.g,color.b);}
    shape.setAttribute('position',new THREE.Float32BufferAttribute(points,3));shape.setAttribute('color',new THREE.Float32BufferAttribute(tints,3));shape.computeBoundingSphere();return shape;
  },[display,visual.highlightIds]);
  useEffect(()=>()=>geometry.dispose(),[geometry]);
  const marker=display.find(item=>item.id===selected);
  const selectedPosition=marker?.position_km || orbit.data?.samples.find(sample=>sample.position_km)?.position_km;
  const focusPosition=visual.paths[0]?.path.samples[Math.floor((visual.paths[0]?.path.samples.length || 1)/2)]?.position_km;
  const planner=usePlanner();const option=planner.result?.encounter_id===ui.encounterId?planner.result?.solutions[planner.index]:undefined;
  const burn=option&&visual.paths.find(layer=>layer.label==='Baseline')?.path.samples.reduce((nearest,sample)=>Math.abs(new Date(sample.epoch).getTime()-new Date(option.maneuver_time).getTime())<Math.abs(new Date(nearest.epoch).getTime()-new Date(option.maneuver_time).getTime())?sample:nearest);
  useEffect(()=>{
    if(lastFocus.current===ui.cameraRevision)return;
    if(ui.cameraAction==='earth'){target.current.set(0,0,0);goal.current=new THREE.Vector3(2.9,1.65,3.6);lastFocus.current=ui.cameraRevision;}
    else{const position=ui.cameraAction==='encounter'?focusPosition:selectedPosition;if(position){const p=new THREE.Vector3(...toWorld(position));target.current.copy(p.clone().multiplyScalar(ui.cameraAction==='encounter'?1:.5));goal.current=ui.cameraAction==='encounter'?p.clone().add(p.clone().normalize().multiplyScalar(.28)):p.clone().normalize().multiplyScalar(2.8);lastFocus.current=ui.cameraRevision;}}
    invalidate();
  },[ui.cameraRevision,ui.cameraAction,selectedPosition?.join(','),focusPosition?.join(',')]);
  useEffect(()=>{follow.current=ui.follow;},[ui.follow]);
  const stats=useRef({frames:0,since:performance.now(),fps:0});
  useFrame((_,delta)=>{
    if(goal.current&&controls.current){const ease=reduced?1:1-Math.exp(-Math.min(delta,.1)*4);camera.position.lerp(goal.current,ease);controls.current.target.lerp(target.current,ease);if(camera.position.distanceTo(goal.current)<.002)goal.current=null;else invalidate();controls.current.update();}
    if(follow.current&&selectedPosition&&controls.current){const p=new THREE.Vector3(...toWorld(selectedPosition)).multiplyScalar(.5);controls.current.target.lerp(p,reduced?1:.04);if(controls.current.target.distanceTo(p)>.001)invalidate();}
    const count=stats.current;count.frames++;const now=performance.now();if(now-count.since>1000){count.fps=count.frames*1000/(now-count.since);count.frames=0;count.since=now;gl.domElement.dataset.fps=count.fps.toFixed(1);gl.domElement.dataset.drawCalls=String(gl.info.render.calls);}
    gl.domElement.dataset.objects=String(display.length);
    gl.domElement.dataset.trackEpochs=JSON.stringify(visibleLayers.map(layer=>closestSample(layer.path,ui.time)?.epoch || null));
  });
  const time=useUI(s=>s.time);const utcAngle=(time%86400000)/86400000*Math.PI*2;
  return <><ambientLight intensity={.32}/><directionalLight position={[-Math.cos(utcAngle)*5,1.3,Math.sin(utcAngle)*5]} intensity={2.2}/><Earth/>
    <points geometry={geometry} onPointerOver={event=>{event.stopPropagation();gl.domElement.style.cursor='pointer';}} onPointerOut={()=>gl.domElement.style.cursor='grab'} onClick={event=>{event.stopPropagation();if(event.index!==undefined && display[event.index])ui.selectObject(display[event.index].id);}}><shaderMaterial vertexShader={vertex} fragmentShader={fragment} transparent depthWrite={false}/></points>
    {orbit.data&&selected && ui.view!=='Close approaches'&&ui.view!=='Avoidance planner'&&<Path path={orbit.data} color="#d5e1ed"/>}
    {visibleLayers.map(layer=><Path key={layer.id} path={layer.path} color={layer.color} dashed={layer.dashed}/>)}
    {selectedPosition&&<group position={toWorld(selectedPosition)}><mesh><sphereGeometry args={[.012,16,16]}/><meshBasicMaterial color="#f4f7ff"/></mesh><Html distanceFactor={4} className="object-label" occlude><span>{marker?.name || orbit.data?.name || selected}</span><small>NORAD {selected}</small></Html></group>}
    {visibleLayers.map(layer=>{const sample=closestSample(layer.path,ui.time);return sample?.position_km?<mesh key={`marker-${layer.id}`} position={toWorld(sample.position_km)} onClick={event=>{event.stopPropagation();ui.selectObject(layer.path.id);}}><sphereGeometry args={[.0035,12,12]}/><meshBasicMaterial color={layer.color}/></mesh>:null;})}
    {ui.view==='Avoidance planner'&&burn?.position_km&&<group position={toWorld(burn.position_km)}><mesh><sphereGeometry args={[.002,12,12]}/><meshBasicMaterial color="#e9f3fe"/></mesh><Html className="burn-label" occlude>Hypothetical burn · nearest returned sample</Html></group>}
    <OrbitControls ref={controls} enableDamping dampingFactor={reduced?1:.07} minDistance={ui.cameraAction==='encounter'?.025:1.08} maxDistance={9} enablePan={false} rotateSpeed={.55} zoomSpeed={.8} onStart={()=>{goal.current=null;if(follow.current)ui.setFollow(false);}}/>
  </>;
}
export function Path({path,color,dashed=false}:{path:NonNullable<ReturnType<typeof useObjectOrbit>['data']>;color:string;dashed?:boolean}){
  // Split on unavailable samples: never connect across missing orbital data.
  const segments=useMemo(()=>{const result:[number,number,number][][]=[];let current:[number,number,number][]=[];for(const sample of path.samples){if(sample.propagation_status==='OK'&&sample.position_km)current.push(toWorld(sample.position_km));else{if(current.length>1)result.push(current);current=[];}}if(current.length>1)result.push(current);return result;},[path]);
  return <>{segments.map((points,index)=><Line key={index} points={points} color={color} lineWidth={1.2} transparent opacity={.7} dashed={dashed} dashSize={.018} gapSize={.01}/>)}</>;
}
class GlobeBoundary extends Component<{children:ReactNode},{error:Error|null}>{state={error:null as Error|null};static getDerivedStateFromError(error:Error){return {error};}render(){return this.state.error?<div className="globe-error"><ErrorNotice error={new Error('3D graphics unavailable. Try a WebGL-capable browser; catalog and analysis tools remain available.')}/></div>:this.props.children;}}
export default function Globe(){return <GlobeBoundary><Canvas aria-label="Interactive Earth" frameloop="demand" camera={{position:[2.9,1.65,3.6],fov:36,near:.01,far:100}} dpr={[1,1.5]} gl={{antialias:true,powerPreference:'high-performance'}} onCreated={({raycaster})=>{raycaster.params.Points!.threshold=.017;}}><Scene/></Canvas></GlobeBoundary>;}
