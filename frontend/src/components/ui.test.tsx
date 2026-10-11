import {it,expect} from 'vitest';
import {render,screen,cleanup} from '@testing-library/react';
import {Field} from './ui';
it('keeps a precise input label and separately associates helper text',()=>{
  render(<Field label="Target separation · km" hint="Not an operational safety threshold."><input type="number" defaultValue={10}/></Field>);
  const input=screen.getByRole('spinbutton',{name:'Target separation · km'});
  expect(input.getAttribute('aria-describedby')).toBe(screen.getByText('Not an operational safety threshold.').id);
  cleanup();
});
