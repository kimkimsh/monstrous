/* Layout gate. A slide whose content collides with the header, the footer,
   or its own box is a slide that will print clipped, so the build stops. */
const {chromium}=require('playwright');
const path=require('path');
(async()=>{
  const file=path.resolve(process.argv[2]);
  const b=await chromium.launch();
  const pg=await b.newPage({viewport:{width:1340,height:760}});
  const errs=[];
  pg.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
  await pg.goto('file://'+file);
  await pg.emulateMedia({media:'print'});
  await pg.waitForTimeout(500);
  const bad=await pg.evaluate(()=>{
    const out=[];
    document.querySelectorAll('section.s').forEach((s,i)=>{
      const n=i+1, r=s.getBoundingClientRect();
      if(Math.round(r.width)!==1280||Math.round(r.height)!==720)
        out.push(`slide ${n}: page box is ${Math.round(r.width)}x${Math.round(r.height)}, not 1280x720`);
      if(s.scrollHeight>s.clientHeight+1) out.push(`slide ${n}: content taller than the page`);
      const bd=s.querySelector('.body'), hd=s.querySelector('.hd'), ft=s.querySelector('.foot');
      if(!bd) return;
      if(bd.scrollHeight>bd.clientHeight+1)
        out.push(`slide ${n}: body overflows by ${bd.scrollHeight-bd.clientHeight}px`);
      const kids=[...bd.children].map(k=>k.getBoundingClientRect());
      if(!kids.length) return;
      const top=Math.min(...kids.map(k=>k.top)), bot=Math.max(...kids.map(k=>k.bottom));
      if(hd&&top<hd.getBoundingClientRect().bottom-1)
        out.push(`slide ${n}: body runs under the title`);
      if(ft&&bot>ft.getBoundingClientRect().top-1)
        out.push(`slide ${n}: body runs into the footer`);
    });
    return out;
  });
  await b.close();
  if(errs.length) bad.push('console errors: '+errs.slice(0,3).join(' | '));
  if(bad.length){ console.error(bad.join('\n')); process.exit(1); }
  console.log('layout ok');
})();
