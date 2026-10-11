import { AlertCircle, Loader2 } from 'lucide-react';
import {Children,cloneElement,isValidElement,useId,type ReactNode,type ReactElement} from 'react';
export function Empty({title,children}:{title:string;children?:ReactNode}){return <div className="empty"><div className="empty-orbit"/><h3>{title}</h3><p>{children}</p></div>;}
export function Loading({children='Retrieving source data…'}:{children?:ReactNode}){return <div role="status" className="loading"><Loader2 size={16} className="spin"/>{children}</div>;}
export function ErrorNotice({error,onRetry}:{error:Error|null|undefined;onRetry?:()=>void}){if(!error)return null;return <div role="alert" className="error-notice"><AlertCircle size={17}/><div><strong>Request unavailable</strong><p>{error.message}</p>{onRetry && <button className="text-button" onClick={onRetry}>Try again</button>}</div></div>;}
export function Status({children,tone='neutral'}:{children:ReactNode;tone?:'neutral'|'warning'|'positive'}){return <span className={`status status-${tone}`}><i/>{children}</span>;}
export function Section({title,children}:{title:string;children:ReactNode}){return <section className="inspector-section"><h3 className="section-label">{title}</h3>{children}</section>;}
export function Metric({label,value,unit}:{label:string;value:ReactNode;unit?:string}){return <div className="metric"><span>{label}</span><div>{value}<small>{unit}</small></div></div>;}
export function Warnings({items=[]}:{items?:string[]}){return items.length?<details className="disclosure"><summary>Assumptions & limitations <span>{items.length}</span></summary>{items.map((text,i)=><p key={i}>{text}</p>)}</details>:null;}
export function Field({label,children,hint}:{label:string;children:ReactNode;hint?:string}){
  const id=useId();const controls=Children.map(children,child=>{
    if(!isValidElement(child)||!['input','select','textarea'].includes(String(child.type)))return child;
    const control=child as ReactElement<{'aria-label'?:string;'aria-describedby'?:string}>;
    return cloneElement(control,{'aria-label':control.props['aria-label']||label,'aria-describedby':hint?`${id}-hint`:undefined});
  });
  return <label className="field"><span>{label}</span>{controls}{hint&&<small id={`${id}-hint`}>{hint}</small>}</label>;
}
