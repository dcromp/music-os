'use strict';
// One preview at a time. Musical plans use seconds; this module owns their lifetime.
(function(root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.createPreviewPlayback = factory;
})(typeof globalThis !== 'undefined' ? globalThis : this, function createPreviewPlayback({
  createAudio, prepare, buffer, changed = () => {}, failed = () => {},
  later = setTimeout, cancel = clearTimeout
}) {
  let audio, active;
  function stop() {
    const old = active;
    active = null; // Invalidate pending work before touching resources or notifying callers.
    if (!old) return;
    old.timers.forEach(cancel);
    old.nodes.forEach(node => { try { node.stop(); } catch {} });
    old.connections.forEach(node => { try { node.disconnect(); } catch {} });
    changed({playing:false});
  }
  async function play(plan) {
    stop();
    const run = {timers:[], nodes:[], connections:[]};
    active = run;
    const current = () => active === run;
    try {
      changed({playing:true, tag:plan.tag, bar:-1, beat:-1});
      audio ??= createAudio();
      await audio.resume();
      if (!current()) return;
      const requests = [...new Set(plan.notes.map(n => n.instrument))].map(instrument => ({
        instrument, notes:plan.notes.filter(n => n.instrument === instrument).map(n => n.midi)
      }));
      await prepare(audio, requests, current);
      if (!current()) return;
      const start = audio.currentTime + .05;
      const connect = node => { run.connections.push(node); return node; };
      const master = connect(audio.createGain());
      master.gain.value = plan.level;
      master.connect(audio.destination);
      let bus = master;
      if (plan.driven) {
        const shaper = connect(audio.createWaveShaper()), curve = new Float32Array(2048);
        for (let i=0;i<curve.length;i++) { const x=2*i/(curve.length-1)-1; curve[i]=Math.tanh(3*x)/Math.tanh(3); }
        shaper.curve=curve;
        const trim=connect(audio.createGain()); trim.gain.value=.45;
        shaper.connect(trim).connect(master); bus=shaper;
      }
      const buffers = new Map();
      for (const n of plan.notes) {
        const src=audio.createBufferSource(), gain=connect(audio.createGain());
        run.nodes.push(src);
        const key=[n.instrument,n.midi,n.duration,!!n.muted].join(':');
        if (!buffers.has(key)) buffers.set(key,buffer(audio,n.instrument,n.midi,n.duration,n.muted));
        src.buffer=buffers.get(key);
        gain.gain.setValueAtTime(n.level,start+n.time);
        gain.gain.setValueAtTime(n.level,start+n.time+Math.max(0,n.duration-plan.release));
        gain.gain.linearRampToValueAtTime(0,start+n.time+n.duration);
        src.connect(gain).connect(bus);
        src.start(start+n.time); src.stop(start+n.time+n.duration);
      }
      for (const p of plan.progress) run.timers.push(later(() => {
        if (current()) changed({playing:true,tag:plan.tag,bar:p.bar,beat:p.beat ?? -1});
      },50+p.time*1000));
      run.timers.push(later(() => { if (current()) stop(); },100+plan.duration*1000));
    } catch (error) {
      if (!current()) return;
      stop(); failed(error);
    }
  }
  return {play,stop};
});
