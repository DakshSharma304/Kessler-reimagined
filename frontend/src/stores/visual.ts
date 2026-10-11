import {create} from 'zustand';
import type {Model} from '../api/client';
export type Class=Model<'ObjectSummary'>['classification'];
export type PathLayer={id:string;path:Model<'ObjectTrajectory'>;color:string;dashed?:boolean;label:string};
type Visual={classes:Class[];paths:PathLayer[];highlightIds:string[];comparison:'Overlay'|'Baseline'|'Maneuvered';setClasses:(classes:Class[])=>void;setPaths:(paths:PathLayer[])=>void;setHighlights:(ids:string[])=>void;setComparison:(mode:Visual['comparison'])=>void};
export const useVisual=create<Visual>(set=>({classes:['PAYLOAD','DEBRIS','ROCKET_BODY','UNKNOWN'],paths:[],highlightIds:[],comparison:'Overlay',setClasses:classes=>set({classes}),setPaths:paths=>set({paths}),setHighlights:highlightIds=>set({highlightIds}),setComparison:comparison=>set({comparison})}));
