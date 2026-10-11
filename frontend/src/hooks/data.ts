import { useQuery } from '@tanstack/react-query';
import { request,type Model } from '../api/client';
import { useUI } from '../stores/ui';
import {useEffect,useState} from 'react';

export function useCatalog(){return useQuery({queryKey:['globe-catalog'],staleTime:300000,queryFn:async({signal})=>{
  const first=await request<Model<'CatalogPage'>>('/objects?limit=500',{signal});
  const pages=await Promise.all([500,1000,1500].filter(offset=>offset<first.total).map(offset=>request<Model<'CatalogPage'>>(`/objects?limit=500&offset=${offset}`,{signal})));
  return {...first,items:[...first.items,...pages.flatMap(page=>page.items)]};
}});}
export function usePositions(){
  const catalog=useCatalog();const time=useUI(s=>s.time);const [requestedTime,setRequestedTime]=useState(time);
  useEffect(()=>{const timer=setTimeout(()=>setRequestedTime(time),220);return()=>clearTimeout(timer);},[time]);
  const epoch=Math.floor(requestedTime/5000)*5000;
  return useQuery({queryKey:['positions',epoch,catalog.data?.catalog.snapshot_sha256],enabled:!!catalog.data?.items.length,staleTime:300000,
    queryFn:({signal})=>request<Model<'PositionBatch'>>('/positions',{body:{object_ids:catalog.data!.items.map(object=>object.id),epoch:new Date(epoch).toISOString()},signal})});
}
export function useObjectOrbit(){const id=useUI(s=>s.selectedId);const reference=useUI(s=>s.referenceTime);return useQuery({queryKey:['orbit',id,reference],enabled:!!id,staleTime:300000,queryFn:({signal})=>request<Model<'ObjectTrajectory'>>(`/objects/${id}/trajectory?sample_count=181&start_time=${encodeURIComponent(new Date(reference).toISOString())}`,{signal})});}
export function useDebounced<T>(value:T,delay=250){const [debounced,set]=useState(value);useEffect(()=>{const timer=setTimeout(()=>set(value),delay);return()=>clearTimeout(timer);},[value,delay]);return debounced;}
export function useObjectInfo(){const id=useUI(s=>s.selectedId);return useQuery({queryKey:['object',id],enabled:!!id,queryFn:({signal})=>request<Model<'ObjectInfo'>>(`/objects/${id}/metadata`,{signal})});}
export function useEncounter(){const id=useUI(s=>s.encounterId);return useQuery({queryKey:['encounter',id],enabled:!!id,queryFn:({signal})=>request<Model<'ScreenedEncounter'>>(`/encounters/${id}`,{signal})});}
export function useAnalysis(){const id=useUI(s=>s.encounterId);return useQuery({queryKey:['analysis',id],enabled:!!id,retry:false,queryFn:({signal})=>request<Model<'ProbabilityBaselineAnalysis'>>(`/encounters/${id}/analyze`,{body:{probability_analysis:true},signal})});}
export function useEncounterPaths(){const id=useUI(s=>s.encounterId);return useQuery({queryKey:['encounter-paths',id],enabled:!!id,staleTime:300000,queryFn:({signal})=>request<Model<'EncounterTrajectories'>>(`/encounters/${id}/trajectories?sample_count=121`,{signal})});}
