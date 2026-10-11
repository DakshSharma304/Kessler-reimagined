import {test,expect} from '@playwright/test';
test('actual Earth, thousand-object batch, filters, selection, time and camera',async({page})=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  const initialResponse=page.waitForResponse(response=>response.url().endsWith('/positions')&&response.ok());
  await page.goto('/');const positions:any[]=[await (await initialResponse).json()];const canvas=page.getByLabel('Interactive Earth');await expect(canvas).toBeVisible({timeout:30000});
  await expect.poll(async()=>Number(await page.locator('canvas').getAttribute('data-objects')),{timeout:60000}).toBeGreaterThan(1000);
  expect(positions[0].frame).toBe('ITRS');expect(positions[0].position_units).toBe('km');expect(positions[0].items.every((item:any)=>item.position_km===null||item.position_km.every(Number.isFinite))).toBe(true);
  const original=await canvas.screenshot();await page.mouse.move(800,410);await page.mouse.down();await page.mouse.move(880,455,{steps:12});await page.mouse.up();await page.waitForTimeout(300);expect(await canvas.screenshot()).not.toEqual(original);
  await page.getByRole('button',{name:'Reset camera'}).click();
  await page.getByLabel('Search objects').fill('25544');await page.getByRole('button',{name:/ISS/}).first().click();await expect(page.locator('.object-label')).toContainText('25544',{timeout:60000});
  await page.getByRole('button',{name:'Payloads',exact:true}).click();await expect(page.getByRole('button',{name:'Payloads',exact:true})).toHaveAttribute('aria-pressed','false');
  const epoch=positions[positions.length-1].epoch;
  const updatedResponse=page.waitForResponse(response=>response.url().endsWith('/positions')&&response.ok());
  await page.getByLabel('Prediction time').fill('60');positions.push(await (await updatedResponse).json());expect(positions[positions.length-1].epoch).not.toBe(epoch);
  await page.getByRole('button',{name:'Reset time'}).click();await page.getByRole('button',{name:'Reset camera'}).click();
  const fps=await page.locator('canvas').getAttribute('data-fps');const calls=await page.locator('canvas').getAttribute('data-draw-calls');console.log('MEASURED_HEADLESS_GPU',JSON.stringify({fps,drawCalls:calls,objects:positions[0].items.length}));
  expect(errors).toEqual([]);await page.screenshot({path:'test-results/checkpoint2-desktop.png'});
});
