import {test,expect} from '@playwright/test';
test('real catalog-wide search, metadata, SOCRATES selection and actual paths',async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('/');await page.getByLabel('Search objects').fill('25544');await page.getByRole('button',{name:/ISS/}).first().click();
 await expect(page.locator('.object-title')).toContainText('ISS',{timeout:30000});await expect(page.getByText('Mass',{exact:true})).toBeVisible();await expect(page.getByText('Unavailable',{exact:true}).first()).toBeVisible();
 await page.getByRole('button',{name:'Close approaches',exact:true}).click();await page.getByLabel('Search encounters').fill('27056');
 const selected=page.locator('.encounter-row').first();await expect(selected).toContainText('COSMOS',{timeout:60000});
 const analysis=page.waitForResponse(r=>r.url().endsWith('/analyze')&&r.ok());const paths=page.waitForResponse(r=>r.url().includes('/trajectories?')&&r.ok());await selected.click();
 const data=await (await analysis).json();const tracks=await (await paths).json();expect(data.calculated.miss_distance_m).toBeGreaterThan(0);expect(tracks.trajectories).toHaveLength(2);expect(tracks.trajectories.every((track:any)=>track.frame==='ITRS'&&track.position_units==='km')).toBe(true);
 await expect(page.getByText('Model separation',{exact:true})).toBeVisible();await expect(page.getByText('unavailable no covariance',{exact:false})).toBeVisible();
 await page.getByLabel('Sort approaches').selectOption('time');await expect(page.locator('.encounter-row').first()).toBeVisible();
 expect(errors).toEqual([]);await page.screenshot({path:'test-results/checkpoint3-encounter.png'});
});
test('source unavailable has a readable recoverable state',async({page})=>{
 await page.route('**/api/objects?**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({status:'UNAVAILABLE',detail:'Catalog source is temporarily unavailable.'})}));
 await page.goto('/');await expect(page.getByRole('alert').first()).toContainText('Catalog source is temporarily unavailable.');
 await expect(page.getByRole('button',{name:'Try again'}).first()).toBeVisible();await expect(page.getByRole('navigation')).toBeVisible();
});
