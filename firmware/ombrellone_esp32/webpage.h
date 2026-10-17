#pragma once
// Pagina web servita dall'ESP32: pianta dall'alto, tocca per spostare la zona d'ombra.
static const char WEBPAGE[] PROGMEM = R"HTML(<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ombrellone</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f4f1ea;color:#222}
header{padding:12px 16px;background:#1b4965;color:#fff}
main{padding:16px;max-width:520px;margin:auto}
canvas{width:100%;aspect-ratio:1;background:#fff;border-radius:12px;touch-action:none;display:block}
.row{display:flex;gap:8px;align-items:center;margin:10px 0;flex-wrap:wrap}
button{padding:8px 14px;border:0;border-radius:8px;background:#1b4965;color:#fff;font-size:15px}
.ok{color:#1b7f3b}.ko{color:#b3261e}
small{color:#666}
</style></head><body>
<header><b>Ombrellone intelligente</b> <span id="clock"></span></header>
<main>
<p>Tocca la pianta per spostare la zona d'ombra (cerchio). Il palo e' al centro, il Nord in alto.</p>
<canvas id="c" width="500" height="500"></canvas>
<div class="row"><label>Raggio zona <input id="r" type="range" min="0.03" max="0.3" step="0.01"></label><span id="rv"></span></div>
<div class="row"><button onclick="send()">Applica</button><button onclick="fetch('/park')">Parcheggia</button><button onclick="fetch('/calib').then(r=>r.json()).then(j=>alert('Nord calibrato: offset '+j.north_offset))">Calibra Nord</button></div>
<p id="st"></p><p id="win"></p>
<small>Giunti: <span id="joints"></span></small>
</main>
<script>
const c=document.getElementById('c'),ctx=c.getContext('2d');let S=null,tx=0,ty=0,tr=0.1,scale=1;
function px(x,y){return[c.width/2+x*scale,c.height/2-y*scale]}
function draw(){if(!S)return;const reach=S.geom.L+S.geom.R+0.05;scale=c.width/2/reach;ctx.clearRect(0,0,c.width,c.height);
ctx.strokeStyle='#ddd';for(let g=-Math.ceil(reach*10);g<=Math.ceil(reach*10);g++){const[x0]=px(g/10,0),[,y0]=px(0,g/10);ctx.beginPath();ctx.moveTo(x0,0);ctx.lineTo(x0,c.height);ctx.moveTo(0,y0);ctx.lineTo(c.width,y0);ctx.stroke();}
// ombra attuale: ellisse campionata lato server? semplificato: cerchio bersaglio + centro palo + direzione sole
const[cx,cy]=px(0,0);ctx.fillStyle='#1b4965';ctx.beginPath();ctx.arc(cx,cy,6,0,7);ctx.fill();
const az=S.sun.az*Math.PI/180,len=c.width*0.45;ctx.strokeStyle='#e9a23b';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+len*Math.sin(az),cy-len*Math.cos(az));ctx.stroke();ctx.lineWidth=1;
ctx.fillStyle='#e9a23b';ctx.font='14px sans-serif';ctx.fillText('sole '+S.sun.elev.toFixed(0)+'°',cx+len*Math.sin(az)*0.8,cy-len*Math.cos(az)*0.8);
// braccio tenuto
const th=S.held.theta*Math.PI/180,al=S.held.alpha*Math.PI/180,ex=S.geom.L*Math.sin(th)*Math.sin(al),ey=S.geom.L*Math.sin(th)*Math.cos(al);const[ax,ay]=px(ex,ey);
ctx.strokeStyle='#555';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(ax,ay);ctx.stroke();ctx.lineWidth=1;
ctx.strokeStyle='#999';ctx.beginPath();ctx.arc(ax,ay,S.geom.R*scale,0,7);ctx.stroke();
const[txp,typ]=px(tx,ty);ctx.fillStyle=S.full?'rgba(27,127,59,.35)':'rgba(179,38,30,.35)';ctx.beginPath();ctx.arc(txp,typ,tr*scale,0,7);ctx.fill();}
function pick(e){const r=c.getBoundingClientRect();const x=(e.clientX-r.left)*c.width/r.width,y=(e.clientY-r.top)*c.height/r.height;tx=(x-c.width/2)/scale;ty=-(y-c.height/2)/scale;draw();}
c.addEventListener('pointerdown',pick);c.addEventListener('pointermove',e=>{if(e.buttons)pick(e)});
document.getElementById('r').oninput=e=>{tr=+e.target.value;document.getElementById('rv').textContent=(tr*100).toFixed(0)+' cm';draw();};
function send(){fetch(`/set?x=${tx.toFixed(3)}&y=${ty.toFixed(3)}&r=${tr.toFixed(3)}`).then(r=>r.json()).then(j=>{document.getElementById('win').textContent='Copertura totale possibile oggi: '+j.window;refresh();});}
function refresh(){fetch('/status').then(r=>r.json()).then(j=>{S=j;if(document.activeElement.id!=='r'){tr=j.target.r;document.getElementById('r').value=tr;document.getElementById('rv').textContent=(tr*100).toFixed(0)+' cm';}
document.getElementById('clock').textContent=new Date(j.time*1000).toLocaleTimeString('it-IT');
document.getElementById('st').innerHTML=(j.parked?'Parcheggiato. ':'')+'Copertura zona: <b class="'+(j.coverage>=0.999?'ok':'ko')+'">'+(j.coverage*100).toFixed(0)+'%</b>, margine '+(j.margin*100).toFixed(0)+'%'+(j.full?'':' &mdash; <span class=ko>il sole e’ troppo basso per coprire tutta la zona</span>');
document.getElementById('joints').textContent=`alpha ${j.held.alpha}°, theta ${j.held.theta}°, beta ${j.held.beta}°, gamma ${j.held.gamma}°`;draw();});}
refresh();setInterval(refresh,5000);fetch('/window').then(r=>r.json()).then(j=>document.getElementById('win').textContent='Copertura totale possibile oggi: '+j.window);
</script></body></html>)HTML";
