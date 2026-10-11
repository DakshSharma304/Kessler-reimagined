export const EARTH_RADIUS_KM=6378.137;
export function toWorld(position:readonly number[]):[number,number,number]{
  if(position.length!==3 || !position.every(Number.isFinite)) throw new Error('A finite ITRS kilometer vector is required');
  return [position[0]/EARTH_RADIUS_KM,position[2]/EARTH_RADIUS_KM,-position[1]/EARTH_RADIUS_KM];
}
export function altitudeKm(position:readonly number[]){return Math.hypot(...position)-EARTH_RADIUS_KM;}
