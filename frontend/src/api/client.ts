import type { components } from './schema';
export type Model<K extends keyof components['schemas']> = components['schemas'][K];
export class ApiError extends Error {
  constructor(message:string,public status:number,public code:string='ERROR'){super(message);this.name='ApiError';}
}
export function resolveBase(value:string|undefined,production=false){
  if(!value && production) throw new ApiError('Set VITE_API_BASE_URL to your Modal backend URL, including /api, then rebuild.',0,'CONFIGURATION');
  const url=new URL(value || 'http://127.0.0.1:8000/api');
  if(!['http:','https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || !url.pathname.endsWith('/api'))
    throw new ApiError('Backend URL must be an HTTP(S) URL ending in /api, without credentials or query parameters.',0,'CONFIGURATION');
  return url.toString().replace(/\/$/,'');
}
export function formatError(data:unknown):string{
  if(data && typeof data==='object' && 'detail' in data){
    const detail=(data as {detail:unknown}).detail;
    if(typeof detail==='string') return detail;
    if(Array.isArray(detail)) return detail.map(item=>`${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg}`).join('; ');
  }
  return 'The backend could not complete this request.';
}
export async function request<T>(path:string,options:{body?:unknown;signal?:AbortSignal;timeout?:number}={}):Promise<T>{
  const base=resolveBase(import.meta.env.VITE_API_BASE_URL,import.meta.env.PROD);
  const timeout=AbortSignal.timeout(options.timeout || 240000);
  const signal=options.signal ? AbortSignal.any([options.signal,timeout]) : timeout;
  let response:Response;
  try{ response=await fetch(base+path,{method:options.body===undefined?'GET':'POST',headers:options.body===undefined?{}:{'Content-Type':'application/json'},body:options.body===undefined?undefined:JSON.stringify(options.body),signal}); }
  catch(error){if(options.signal?.aborted) throw error;throw new ApiError(timeout.aborted?'Request timed out. The server may still be calculating; do not assume it stopped.':'Cannot reach the backend. Check the URL, connection and allowed frontend origin.',0,'NETWORK');}
  const data=await response.json();
  if(!response.ok) throw new ApiError(formatError(data),response.status,data.status || (response.status===429?'BUSY':'ERROR'));
  return data as T;
}
export const retryRead=(count:number,error:Error)=>!(error instanceof ApiError && [0,404,422,429].includes(error.status)) && count<1;
