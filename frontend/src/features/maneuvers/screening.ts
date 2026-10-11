import type {Model} from '../../api/client';
export function screeningSummary(result:Pick<Model<'ScreeningResult'>,'screening_complete'|'additional_close_approaches'>){
  if(!result.screening_complete)return 'Incomplete screening. Empty detections do not establish absent close approaches.';
  if(result.additional_close_approaches>0)return 'Additional close approaches detected within the selected screening coverage.';
  return 'No additional close approaches detected within the selected screening coverage.';
}
