import { test,expect } from '@playwright/test';
test('real backend connection, navigation, panels and responsive shell',async({page})=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  await page.goto('/');await expect(page.getByText('Backend connected',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Close approaches',exact:true}).click();await expect(page.getByRole('heading',{name:'Close approaches',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Close explorer',exact:true}).click();await expect(page.getByRole('button',{name:'Open explorer'})).toBeVisible();
  await page.getByRole('button',{name:'Open explorer'}).click();await expect(page.getByRole('heading',{name:'Close approaches',exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});await expect(page.getByRole('navigation')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);expect(errors).toEqual([]);
  await page.screenshot({path:'test-results/checkpoint1-mobile.png'});
});
