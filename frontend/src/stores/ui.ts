import { create } from 'zustand';
export const views=['Explore','Close approaches','Avoidance planner','Orbital decay','Cleanup planner','Data & methods'] as const;
export type View=typeof views[number];
type UI={view:View;selectedId:string|null;encounterId:string|null;encounterFilter:string;time:number;referenceTime:number;playing:boolean;speed:number;leftOpen:boolean;rightOpen:boolean;cameraAction:'earth'|'object'|'encounter';cameraRevision:number;follow:boolean;
  setView:(view:View)=>void;selectObject:(id:string)=>void;selectEncounter:(id:string)=>void;setEncounterFilter:(value:string)=>void;setContextTime:(time:number)=>void;setTime:(time:number)=>void;setPlaying:(playing:boolean)=>void;setSpeed:(speed:number)=>void;togglePanel:(panel:'left'|'right')=>void;openPanel:(panel:'left'|'right')=>void;focus:(action:UI['cameraAction'])=>void;setFollow:(value:boolean)=>void;};
const referenceTime=Date.now();
export const useUI=create<UI>((set)=>({view:'Explore',selectedId:null,encounterId:null,encounterFilter:'',time:referenceTime,referenceTime,playing:false,speed:1,leftOpen:true,rightOpen:true,cameraAction:'earth',cameraRevision:0,follow:false,
  setView:view=>set({view}),selectObject:id=>set(s=>({selectedId:id,rightOpen:true,cameraAction:'object',cameraRevision:s.cameraRevision+1})),
  selectEncounter:id=>set(s=>({encounterId:id,selectedId:null,rightOpen:true,cameraAction:'encounter',cameraRevision:s.cameraRevision+1})),
  setEncounterFilter:encounterFilter=>set({encounterFilter}),setContextTime:time=>set({time,referenceTime:time,playing:false}),
  setTime:time=>set({time}),setPlaying:playing=>set({playing}),setSpeed:speed=>set({speed}),
  togglePanel:panel=>set(s=>panel==='left'?{leftOpen:!s.leftOpen}:{rightOpen:!s.rightOpen}),
  openPanel:panel=>set(panel==='left'?{leftOpen:true}:{rightOpen:true}),
  focus:cameraAction=>set(s=>({cameraAction,cameraRevision:s.cameraRevision+1})),setFollow:follow=>set({follow})}));
