let player, chart, ready=false, failed=false, hiddenCues=false, time=0, state=-1, seeking=false;
const $=id=>document.getElementById(id), logs=[];
function log(event,data={}){logs.push({at:new Date().toISOString(),event,...data});if(logs.length>150)logs.shift();$('debug').textContent=JSON.stringify({browser:navigator.userAgent,viewport:[innerWidth,innerHeight],videoId:chart?.videoId,chartSha256:chart?.chartSha256,state,time,logs},null,2)}
function status(text){$('status').textContent=text}
function controls(enabled){for(const id of ['play','pause','restart','back','seek','rate'])$(id).disabled=!enabled}
function display(){
 $('clock').textContent=`Player position: ${time.toFixed(1)} s`;
 if(failed||hiddenCues||document.hidden){$('cues').textContent=failed?'Playback unavailable.': 'Cues hidden until you resume.';return}
 if(!ready||!chart)return;
 const i=chart.chords.findIndex(c=>time>=c.start_seconds&&time<c.end_seconds);
 if(i<0){$('cues').textContent=state===0?'End of recording.':'No chart coverage at this position.';return}
 $('cues').replaceChildren();
 for(const [j,c] of [chart.chords[i],chart.chords[i+1]].entries()){
  const box=document.createElement('div');box.className='cue '+(j?'next':'');
  const caption=document.createElement('small');caption.textContent=j?'NEXT':'NOW';
  const chord=document.createElement('div');chord.className='chord';chord.textContent=c?(c.label==='N'?'—':c.label):'End';
  const duration=document.createElement('div');duration.textContent=c?`${(c.end_seconds-c.start_seconds).toFixed(1)} s hold${j?'':` · ${Math.max(0,c.end_seconds-time).toFixed(1)} s left`}`:'';
  box.append(caption,chord,duration);$('cues').append(box)
 }
}
function sample(){if(!ready||failed)return;const value=player.getCurrentTime();if(Number.isFinite(value))time=value;const duration=player.getDuration();if(duration>0)$('seek').max=duration;if(!seeking)$('seek').value=time;display()}
function seek(value){if(!ready||failed)return;log('seek-request',{target:value,from:time});player.seekTo(value,true);status('Seeking — waiting for player position.');sample()}
window.onYouTubeIframeAPIReady=async()=>{
 try{const response=await fetch('recordings.json');if(!response.ok)throw Error('Chart unavailable');const recordings=await response.json();const key=new URLSearchParams(location.search).get('recording')||'wild-thing';chart=recordings[key]||recordings['wild-thing'];$('recording').value=recordings[key]?key:'wild-thing';$('title').textContent=chart.title;$('external').href='https://www.youtube.com/watch?v='+chart.videoId;
 player=new YT.Player('player',{width:'100%',height:'100%',videoId:chart.videoId,playerVars:{playsinline:1,controls:1,origin:location.origin},events:{
 onReady:()=>{ready=true;controls(true);status('Ready — tap Play in the video or below.');const rates=player.getAvailablePlaybackRates();$('rate').replaceChildren(...rates.map(r=>new Option(r+'×',r)));$('rate').value=player.getPlaybackRate();log('ready',{rates});sample()},
 onStateChange:e=>{state=e.data;status(({'-1':'Ready to start',0:'Ended',1:'Playing',2:'Paused',3:'Buffering — waiting for playback',5:'Ready'})[state]||'Waiting');log('state',{state,position:player.getCurrentTime()});sample()},
 onError:e=>{failed=true;controls(false);status(`YouTube could not play this recording (error ${e.data}). Try the link below or another browser.`);log('error',{code:e.data});display()},
 onAutoplayBlocked:()=>{status('Tap Play inside the YouTube player to start.');log('autoplay-blocked')},
 onPlaybackRateChange:e=>{$('rate').value=e.data;log('rate-confirmed',{rate:e.data})}
 }});
 }catch(e){failed=true;status('Could not load the prototype chart. Reload to retry.');log('load-error',{message:String(e)})}
};
$('play').onclick=()=>{log('play-request');player.playVideo()};$('pause').onclick=()=>{log('pause-request');player.pauseVideo()};$('restart').onclick=()=>seek(0);$('back').onclick=()=>seek(Math.max(0,time-10));$('seek').oninput=()=>seeking=true;$('seek').onchange=e=>{seek(+e.target.value);seeking=false};$('rate').onchange=e=>{log('rate-request',{rate:+e.target.value});player.setPlaybackRate(+e.target.value)};
$('hold').onclick=()=>{hiddenCues=!hiddenCues;$('hold').textContent=hiddenCues?'Show cues again':'Hide cues during interruption';log('cues-hidden',{hiddenCues});display()};
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText($('debug').textContent);$('copy').textContent='Copied'}catch{$('copy').textContent='Select and copy the log below'}};
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&ready){player.pauseVideo();log('tab-hidden-pause')}sample()});
setInterval(sample,100);setTimeout(()=>{if(!ready&&!failed)status('YouTube has not loaded yet. Check the connection, then reload or try Safari.')},12000);
const api=document.createElement('script');api.src='https://www.youtube.com/iframe_api';api.onerror=()=>status('YouTube could not load. Check the connection and reload.');document.head.append(api);

$('recording').onchange=e=>{const u=new URL(location);u.searchParams.set('recording',e.target.value);location.href=u};
