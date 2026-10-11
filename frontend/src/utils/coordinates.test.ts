import {it,expect} from 'vitest';
import {toWorld,EARTH_RADIUS_KM} from './coordinates';
it('maps ITRS kilometers to a right-handed Y-up Earth-radius scale',()=>{expect(toWorld([EARTH_RADIUS_KM,0,0])).toEqual([1,0,-0]);expect(toWorld([0,EARTH_RADIUS_KM,0])).toEqual([0,0,-1]);expect(toWorld([0,0,EARTH_RADIUS_KM])).toEqual([0,1,-0]);});
it('preserves vector length and rejects unavailable/invalid values',()=>{const position=[7000,1234,-1000];expect(Math.hypot(...toWorld(position))*EARTH_RADIUS_KM).toBeCloseTo(Math.hypot(...position),9);expect(()=>toWorld([NaN,0,0])).toThrow();expect(()=>toWorld([1,2])).toThrow();});
