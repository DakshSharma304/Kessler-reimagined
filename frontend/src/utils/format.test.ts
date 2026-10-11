import {it,expect} from 'vitest';
import {number,probability,timestamp} from './format';
it('never represents missing scientific data as zero',()=>{expect(number(null)).toBe('Unavailable');expect(number(undefined)).toBe('Unavailable');expect(number(0)).toBe('0.00');expect(probability(null)).toBe('Unavailable');expect(probability(0)).toContain('numerical result');expect(timestamp(undefined)).toBe('Unavailable');});
