import {it,expect} from 'vitest';
import {useUI} from '../../stores/ui';
import {useVisual} from '../../stores/visual';
it('selection, camera, filters and time remain independent',()=>{const time=useUI.getState().time;useUI.getState().selectObject('25544');expect(useUI.getState().selectedId).toBe('25544');expect(useUI.getState().cameraAction).toBe('object');expect(useUI.getState().time).toBe(time);useVisual.getState().setClasses(['DEBRIS']);expect(useVisual.getState().classes).toEqual(['DEBRIS']);useUI.getState().setTime(time+5000);expect(useUI.getState().time).toBe(time+5000);useUI.getState().focus('earth');expect(useUI.getState().cameraAction).toBe('earth');});
