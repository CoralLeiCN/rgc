/* Deterministic SVG geometry preview. This does not capture a browser. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const M = require('./layered-price-model.js');
const layers = M.layers(4), clouds = M.cloud(layers, 1, 3), selected = M.products[175];
const proposal = Math.round(M.unitPrice(selected) * 1.08 * 100) / 100;
const money = n => '£' + n.toFixed(2);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const num = n => Number(n.toFixed(2));
const svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="980" viewBox="0 0 1440 980"><title>RGC price point cloud: 500 fictional products</title><desc>Static projection of the same product records and trait-layer samples as the interactive prototype. This is not a browser screenshot.</desc>',
  '<defs><radialGradient id="cloudGlow"><stop stop-color="#13303b"/><stop offset="1" stop-color="#08131d"/></radialGradient><linearGradient id="pageGlow" x2="1" y2="1"><stop stop-color="#11212c"/><stop offset="1" stop-color="#080f17"/></linearGradient><clipPath id="plotClip"><rect x="41" y="242" width="1014" height="480"/></clipPath></defs>',
  '<rect width="1440" height="980" fill="url(#pageGlow)"/>'];
const rect = (x,y,w,h,fill,stroke='none',radius=0) => svg.push(`<rect x="${num(x)}" y="${num(y)}" width="${num(w)}" height="${num(h)}" rx="${radius}" fill="${fill}" stroke="${stroke}"/>`);
const text = (x,y,label,size=12,color='#a7bcc8',weight=400,anchor='start') => svg.push(`<text x="${num(x)}" y="${num(y)}" fill="${color}" font-family="Arial, sans-serif" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}">${esc(label)}</text>`);
const line = (x1,y1,x2,y2,color='#213744',extra='') => svg.push(`<line x1="${num(x1)}" y1="${num(y1)}" x2="${num(x2)}" y2="${num(y2)}" stroke="${color}" ${extra}/>`);
const circle = (x,y,r,fill,opacity=1,extra='') => svg.push(`<circle cx="${num(x)}" cy="${num(y)}" r="${r}" fill="${fill}" opacity="${opacity}" ${extra}/>`);
const project = (x,y,z) => [535+(x-y)*444, 513+(x+y)*104-z*70];
const plotline = (a,b,color,extra) => line(...project(...a),...project(...b),color,extra);

text(40,48,'RGC',28,'#eff8f5',800); circle(108,39,4,'#62ebc6');
text(137,43,'CATEGORY INTELLIGENCE / DESIGN STUDY 04',10,'#93aeba',500);
rect(1163,23,237,30,'#142b2b','#2d524d',15); text(1282,43,'LiDAR-STYLE / FICTIONAL DATA',10,'#b5e9db',500,'middle');
line(40,65,1400,65);
text(40,100,'EXPLORE THE SHAPE OF A PRICING DECISION',10,'#94afb9',600);
text(38,151,'Price',49,'#f0f6f4',600); text(167,151,'point cloud.',49,'#d8baff',600);
text(42,176,'500 products. Six traits. Every price has a structure.',13);
text(1081,116,'500 fictional products · illustrative model',12,'#dbe9e4',600);
text(1081,138,'Colored points reveal the layers behind each price.',10);
text(1081,155,'Synthetic product data. LiDAR-inspired appearance.',10);

rect(40,202,1016,714,'#0c1822','#283d49',12);
rect(41,243,1014,479,'url(#cloudGlow)');
text(60,228,'01 / EXPLORE THE POINT CLOUD',10,'#bed2d6',600);
rect(480,211,138,23,'#162730','#334b57',4); text(491,227,'Top traits: 4 + other',10,'#c9dcdd');
rect(628,211,139,23,'#162730','#334b57',4); text(639,227,'Samples / layer: 3',10,'#c9dcdd');
rect(777,211,128,23,'#162730','#334b57',4); text(789,227,'Scan slice: 100%',10,'#c9dcdd');
rect(916,211,40,23,'#294d46','#477d6d',4); text(936,227,'3D',10,'#c7f6e5',500,'middle');
text(979,227,'Side',10); text(1022,227,'Top',10);
circle(67,265,3,'#62ebc6'); text(78,269,`500 / 500 PRODUCTS  ·  ${clouds.reduce((s,c)=>s+c.x.length,0).toLocaleString('en-GB')} LAYER SAMPLES`,10,'#b0cfcf');
text(1035,269,'£ / 100 g',10,'#a9c4ca',500,'end');

svg.push('<g clip-path="url(#plotClip)">');
for (let i=0;i<=10;i++) {
  const k=i/10;
  plotline([k,0,0],[k,1,0],i%5===0?'#2b4653':'#19313e');
  plotline([0,k,0],[1,k,0],i%5===0?'#2b4653':'#19313e');
}
plotline([0,1,0],[0,1,5.2],'#395463');
for(let z=0;z<=4;z+=2){ const [x,y]=project(0,1,z); text(x-12,y+4,'£'+z,10,'#8fabb8',400,'end'); plotline([0,1,z],[1,1,z],'#1b3340','stroke-dasharray="3 6"'); }
const dots=[];
clouds.forEach((c,index)=>c.x.forEach((x,i)=>dots.push({x,y:c.y[i],z:c.z[i],color:c.color,r:index===0?1:1.18,opacity:index===0?.5:.86})));
M.products.forEach(p=>dots.push({x:p.x,y:p.y,z:p.fit,color:'#dffff4',r:1.5,opacity:.9}));
dots.sort((a,b)=>a.x+a.y-b.x-b.y).forEach(d=>circle(...project(d.x,d.y,d.z),d.r,d.color,d.opacity));
const [sx,sy]=project(selected.x,selected.y,selected.fit), [,py]=project(selected.x,selected.y,proposal);
let low=0;
layers.forEach(layer=>{ const high=low+layer.value(selected); plotline([selected.x,selected.y,low],[selected.x,selected.y,high],layer.color,'stroke-width="4" opacity="0.95"');low=high; });
plotline([selected.x,selected.y,selected.fit],[selected.x,selected.y,proposal],'#e2c6ff','stroke-width="2" stroke-dasharray="4 4"');
circle(sx,sy,6,'#0e212b',1,'stroke="#effff9" stroke-width="2"');
circle(...project(selected.x,selected.y,M.unitPrice(selected)),3,'#ffffff');
circle(sx,py,17,'#d8baff',.1); circle(sx,py,10,'#d8baff',.12);
svg.push(`<path d="M${num(sx)},${num(py-6)}l6,6 -6,6 -6,-6Z" fill="#d8baff"/>`);
line(sx+8,py,sx+41,py-4,'#ba9cd9');
rect(sx+41,py-20,143,35,'#251f36','#6e5789',5); text(sx+53,py+2,`${selected.id} / PROPOSED ${money(proposal)}`,10,'#ead9ff',600);
svg.push('</g>');
text(245,694,'TRAIT-CONTRIBUTION SIMILARITY',9,'#7799a9',500);
text(1033,704,'DRAG TO ORBIT · CLICK A POINT TO INSPECT',9,'#829eaa',500,'end');
line(60,723,1035,723);
let lx=66;
layers.forEach(layer=>{circle(lx,744,3.5,layer.color);text(lx+10,748,layer.name,10,'#b9cbd2');lx+=layer.name.length*5.4+37;});
text(65,770,'White anchors = full benchmark. Colored returns = samples within each product’s stacked contributions.',10,'#93acb8');
line(60,787,1035,787);
text(64,810,'02 / SAME VALUES, EXACT STACKED BARS',10,'#b0c7d0',600);
const sorted=[...M.products].sort((a,b)=>a.x-b.x||a.y-b.y);
const sample=Array.from({length:8},(_,i)=>sorted[Math.round(i*(sorted.length-1)/7)]);sample[4]=selected;
sample.forEach((p,i)=>{
  const x=91+i*119;let cumulative=0;
  layers.forEach(layer=>{const h=layer.value(p)*10.7;rect(x,884-cumulative-h,36,h,layer.color);cumulative+=h;});
  text(x+18,884-cumulative-6,money(p.fit),10,'#d2e3df',400,'middle');
  text(x+18,902,p.id,9,p.id===selected.id?'#d8baff':'#8faab6',400,'middle');
  if(p.id===selected.id)line(x-3,908,x+39,908,'#d8baff','stroke-width="2"');
});

rect(1076,202,324,714,'#101c26','#2b3f4c',12);
text(1098,229,'PRODUCT CROSS-SECTION',10,'#9bb3bf',600);
rect(1098,244,279,32,'#101f29','#36505e',5);text(1110,265,`${selected.id} · ${selected.name}`,11,'#cee0df');line(1362,257,1366,262,'#afc3ce');line(1366,262,1370,257,'#afc3ce');
text(1098,307,selected.name,22,'#eff6f2',600);
text(1098,328,`${selected.sugar} g sugar /100 g · fictional product`,10);
let stackBottom=483;
layers.forEach(layer=>{const h=layer.value(selected)/selected.fit*135;rect(1128,stackBottom-h,220,h,layer.color);if(h>19)text(1238,stackBottom-h/2+4,layer.name,10,'#0a1823',600,'middle');stackBottom-=h;});
layers.forEach((layer,i)=>{circle(1103,508+i*22,3.5,layer.color);text(1116,512+i*22,layer.name,11,'#beced7');text(1376,512+i*22,money(layer.value(selected)),11,'#e3edeb',400,'end');});
line(1098,643,1377,643);
text(1098,669,'Full benchmark /100 g',11);text(1376,671,money(selected.fit),25,'#e6f3ed',600,'end');
text(1098,704,'Actual price /100 g',11);text(1376,706,money(M.unitPrice(selected)),25,'#e6f3ed',600,'end');
text(1098,741,'Proposed price /100 g',11);text(1376,741,'GBP',10,'#d8baff',400,'end');
rect(1098,752,279,45,'#241f34','#675182',5);text(1110,782,'£',21,'#d8baff');text(1363,782,proposal.toFixed(2),25,'#d8baff',600,'end');
line(1098,813,1376,813,'#415363','stroke-width="3"');line(1098,813,1250,813,'#bea0e8','stroke-width="3"');circle(1250,813,5,'#d8baff');
text(1098,842,'Proposal vs benchmark',11);text(1376,842,`+${((proposal/selected.fit-1)*100).toFixed(1)}%`,15,'#e0c1ff',600,'end');
text(1098,875,'Every layer sums to the benchmark.',10,'#a9c6c4');
text(1098,893,'Changing the proposal preserves the cloud.',10,'#8faab6');
text(40,944,'500 FICTIONAL RECORDS · SIX TRAITS · SYNTHETIC PRICE FUNCTION',10,'#97b0bc');
text(1400,944,'STATIC GEOMETRY PREVIEW · NOT A BROWSER SCREENSHOT',9,'#7999a8',500,'end');
svg.push('</svg>');
fs.writeFileSync(path.join(__dirname,'layered-price-preview.svg'),svg.join('\n'));
console.log(`Rendered ${M.products.length} products and ${clouds.reduce((s,c)=>s+c.x.length,0)} layer samples to layered-price-preview.svg`);
