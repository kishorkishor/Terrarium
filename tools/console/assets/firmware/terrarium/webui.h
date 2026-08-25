/* Mobile dashboard, served from flash. Open the ESP32's IP in Chrome on
 * Android, then menu -> "Add to Home screen" to install it like an app.   */
#pragma once
#include <pgmspace.h>

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#10251b">
<title>Terrarium</title>
<style>
:root{--bg:#0e1512;--card:#16211b;--line:#24352c;--ink:#dfe9e2;--dim:#8fa89a;
--acc:#4cc98a;--warn:#e0b25e;--bad:#e57f7f;font-size:16px}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;
padding:14px;max-width:520px;margin:0 auto}
h1{font-size:20px;display:flex;align-items:center;gap:10px;margin-bottom:4px}
h1 .dot{width:10px;height:10px;border-radius:50%;background:var(--bad)}
h1 .dot.on{background:var(--acc)}
#sub{color:var(--dim);font-size:12px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.card .k{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.08em}
.card .v{font-size:26px;font-weight:600;margin-top:2px}
.card .v small{font-size:13px;color:var(--dim);font-weight:400}
.row{display:flex;align-items:center;justify-content:space-between;
padding:10px 12px;background:var(--card);border:1px solid var(--line);
border-radius:12px;margin-bottom:8px}
.row .st{width:9px;height:9px;border-radius:50%;background:#3a4a41;margin-right:10px}
.row .st.on{background:var(--acc);box-shadow:0 0 8px var(--acc)}
.row .nm{flex:1;font-size:14px}
button{font:inherit;border:0;border-radius:9px;padding:8px 14px;cursor:pointer;
background:#22352b;color:var(--ink);font-size:13px}
button:disabled{opacity:.35}
button.pri{background:var(--acc);color:#08130d;font-weight:600}
#mode{width:100%;padding:12px;font-size:15px;margin-bottom:14px}
.warnbox{display:none;background:#33231a;border:1px solid var(--warn);color:var(--warn);
border-radius:10px;padding:10px 12px;font-size:13px;margin-bottom:12px}
fieldset{border:1px solid var(--line);border-radius:12px;padding:12px;margin-top:6px}
legend{font-size:12px;color:var(--dim);padding:0 6px}
label{display:flex;justify-content:space-between;align-items:center;
font-size:13px;color:var(--dim);margin:8px 0}
input{width:84px;background:#0c120f;color:var(--ink);border:1px solid var(--line);
border-radius:7px;padding:6px 8px;font:inherit;font-size:14px;text-align:right}
#save{width:100%;margin-top:10px}
#toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);
background:var(--acc);color:#08130d;padding:8px 16px;border-radius:9px;
font-size:13px;font-weight:600;opacity:0;transition:opacity .3s;pointer-events:none}
</style></head><body>
<h1><span class="dot" id="net"></span>Terrarium</h1>
<div id="sub">connecting&hellip;</div>
<div class="warnbox" id="tank">RESERVOIR EMPTY — mist disabled until refilled</div>

<div class="grid">
 <div class="card"><div class="k">Air temp</div><div class="v" id="t">--<small> &deg;C</small></div></div>
 <div class="card"><div class="k">Humidity</div><div class="v" id="h">--<small> %</small></div></div>
 <div class="card"><div class="k">Soil avg</div><div class="v" id="s">--<small> %</small></div>
   <div class="k" id="s2" style="margin-top:4px">1: -- &middot; 2: --</div></div>
 <div class="card"><div class="k">Light</div><div class="v" id="l">--<small> lx</small></div></div>
 <div class="card"><div class="k">Leak sensor</div><div class="v" id="lk">--</div>
   <div class="k" id="lk2" style="margin-top:4px">dry</div></div>
</div>

<button id="mode" class="pri">Mode: AUTO</button>

<div id="outs">
 <div class="row" data-o="water"><span class="st"></span><span class="nm">Watering mist</span><button>ON</button></div>
 <div class="row" data-o="hum"><span class="st"></span><span class="nm">Humidity mist</span><button>ON</button></div>
 <div class="row" data-o="light"><span class="st"></span><span class="nm">Grow light</span><button>ON</button></div>
 <div class="row" data-o="buzz"><span class="st"></span><span class="nm">Buzzer</span><button>ON</button></div>
 <div class="row" data-o="fan"><span class="st"></span><span class="nm">Fan / 4th channel</span><button>ON</button></div>
</div>

<fieldset><legend>Thresholds (saved on the device)</legend>
 <label>Water below soil % <input id="f_soilDry" type="number" min="5" max="80"></label>
 <label>Mist below RH % <input id="f_humLo" type="number" min="30" max="95"></label>
 <label>Stop mist at RH % <input id="f_humHi" type="number" min="40" max="99"></label>
 <label>Light ON below lux <input id="f_luxOn" type="number" min="0" max="20000"></label>
 <label>Light OFF above lux <input id="f_luxOff" type="number" min="0" max="30000"></label>
 <label>Photoperiod start hour <input id="f_lightStart" type="number" min="0" max="23"></label>
 <label>Photoperiod end hour <input id="f_lightEnd" type="number" min="1" max="24"></label>
 <label>Brightness 0-255 <input id="f_bright" type="number" min="0" max="255"></label>
 <button id="save" class="pri">Save settings</button>
</fieldset>

<fieldset><legend>Wi-Fi (saved on the device)</legend>
 <div id="wifinow" style="font-size:12px;color:var(--dim);margin:2px 0 6px">&hellip;</div>
 <label>Network name <input id="f_wssid" type="text" style="width:170px;text-align:left"></label>
 <label>Password <input id="f_wpass" type="text" style="width:170px;text-align:left"></label>
 <button id="wsave" class="pri">Save Wi-Fi &amp; restart board</button>
 <div style="font-size:11px;color:var(--dim);margin-top:8px">
  2.4&nbsp;GHz networks only (a phone hotspot works). If the board cannot join,
  it makes its own hotspot <b>Terrarium</b> / terrarium123 at 192.168.4.1 —
  open this page there and try again.</div>
</fieldset>

<div id="toast">saved</div>
<script>
var S={mode:"auto"};
function g(i){return document.getElementById(i)}
function toast(m){var t=g("toast");t.textContent=m;t.style.opacity=1;
 setTimeout(function(){t.style.opacity=0},1400)}
function api(u){return fetch(u).then(function(r){return r.json()})}

function paint(d){
 S=d; g("net").className="dot on";
 g("sub").textContent=d.mode.toUpperCase()+" · "+d.ip+" · up "+d.up;
 g("t").innerHTML=(d.temp==null?"--":d.temp.toFixed(1))+"<small> &deg;C</small>";
 g("h").innerHTML=(d.hum==null?"--":d.hum.toFixed(0))+"<small> %</small>";
 g("s").innerHTML=d.soil+"<small> %</small>";
 g("s2").innerHTML="1: "+d.soil1+"% &middot; 2: "+(d.soil2==null?"--":d.soil2+"%");
 g("l").innerHTML=(d.lux==null?"--":Math.round(d.lux))+"<small> lx</small>";
 g("lk").innerHTML=(d.leak==null?"--":d.leak);
 g("lk2").innerHTML=d.leakWet?"<b>WATER DETECTED</b>":"dry";
 g("lk2").style.color=d.leakWet?"#ff6b6b":"";
 g("tank").style.display=d.tankOk?"none":"block";
 g("mode").textContent="Mode: "+d.mode.toUpperCase()+
   (d.mode=="auto"?"  (tap for manual)":"  (tap to resume auto)");
 document.querySelectorAll("#outs .row").forEach(function(r){
  var o=r.dataset.o,on=d.out[o];
  r.querySelector(".st").className="st"+(on?" on":"");
  var b=r.querySelector("button");
  b.textContent=on?"OFF":"ON"; b.disabled=false;
 });
 if(d.ssid!==undefined){g("wifinow").innerHTML=d.ap
   ?"<b>hotspot mode</b> — could not join &quot;"+d.ssid+"&quot;; set a network below"
   :"joined: <b>"+d.ssid+"</b>"}
 if(!paint.seeded){paint.seeded=1;
  ["soilDry","humLo","humHi","luxOn","luxOff","lightStart","lightEnd","bright"]
  .forEach(function(k){g("f_"+k).value=d.cfg[k]});
  if(d.ssid!==undefined)g("f_wssid").value=d.ssid}
}
var hold=0;                       /* pause polling right after a press */
function poll(){ if(Date.now()<hold) return;
 api("/api/status").then(function(d){ if(Date.now()<hold) return; paint(d) })
 .catch(function(){ g("net").className="dot";g("sub").textContent="reconnecting…"})}
setInterval(poll,2000); poll();

g("mode").onclick=function(){
 api("/api/mode?m="+(S.mode=="auto"?"manual":"auto")).then(paint)};
document.querySelectorAll("#outs .row button").forEach(function(b){
 b.onclick=function(){
  var r=b.closest(".row"), o=r.dataset.o, want=S.out[o]?0:1;
  hold=Date.now()+2500;            /* ignore polls while this settles */
  b.disabled=true;
  r.querySelector(".st").className="st"+(want?" on":"");
  b.textContent=want?"OFF":"ON";   /* show it immediately, don't wait */
  api("/api/out?name="+o+"&state="+want)
   .then(function(d){ hold=0; if(d.err){toast(d.err)} else {paint(d)} })
   .catch(function(){ hold=0; toast("no reply from board") })
   .then(function(){ b.disabled=false })}});
g("save").onclick=function(){
 var q=["soilDry","humLo","humHi","luxOn","luxOff","lightStart","lightEnd","bright"]
 .map(function(k){return k+"="+encodeURIComponent(g("f_"+k).value)}).join("&");
 api("/api/set?"+q).then(function(d){paint(d);toast("saved")})};
g("wsave").onclick=function(){
 var s=g("f_wssid").value.trim();
 if(!s){toast("enter a network name");return}
 if(!confirm("Save Wi-Fi \""+s+"\" and restart the board?\n\nIf it cannot join, "+
   "it will make its own hotspot Terrarium / terrarium123 at 192.168.4.1."))return;
 api("/api/wifi?ssid="+encodeURIComponent(s)+"&pass="+encodeURIComponent(g("f_wpass").value))
  .then(function(d){toast(d.err?d.err:"saved — board restarting on \""+s+"\"")})
  .catch(function(){toast("saved — board restarting")})};
</script></body></html>
)rawliteral";
