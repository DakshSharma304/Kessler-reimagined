import { describe,it,expect } from 'vitest';
import { resolveBase,formatError,ApiError,retryRead } from './client';
describe('API contract',()=>{
  it('has explicit configurable dev/prod origins',()=>{expect(resolveBase(undefined)).toBe('http://127.0.0.1:8000/api');expect(resolveBase('https://x.modal.run/api',true)).toBe('https://x.modal.run/api');expect(()=>resolveBase(undefined,true)).toThrow('VITE_API_BASE_URL');});
  it('rejects invalid URLs',()=>{for(const value of ['ftp://example.com/api','https://user:secret@example.com/api','https://example.com','https://example.com/api?x=1'])expect(()=>resolveBase(value)).toThrow();});
  it('keeps backend scientific and validation explanations',()=>{expect(formatError({status:'UNSUPPORTED',detail:'Covariance missing'})).toBe('Covariance missing');expect(formatError({detail:[{loc:['body','radius'],msg:'Field required'}]})).toContain('radius: Field required');});
  it('does not automatically retry expensive or rejected inputs',()=>{expect(retryRead(0,new ApiError('busy',429))).toBe(false);expect(retryRead(1,new Error('source'))).toBe(false);});
});
