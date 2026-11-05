"use strict";
// Preserve earlier shared links to Jukebox songs when the root becomes the mode chooser.
if (/^#\/(song|ready)\//.test(location.hash)) location.replace("jukebox.html" + location.search + location.hash);

// Pick up where you left off: the card keeps its plain link to the Jukebox if nothing was played or anything here fails.
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const store = window.StrumSession.createStore({
      getItem: key => window.localStorage.getItem(key),
      setItem: (key, value) => window.localStorage.setItem(key, value),
    });
    const response = await fetch("songs/index.json", { cache: "no-cache" });
    const point = store.resumePoint((await response.json()).songs);
    if (!point) return;
    document.getElementById("resume").href = `jukebox.html#/resume/${encodeURIComponent(point.song.id)}`;
    document.getElementById("resume-label").textContent = point.t ? "Pick up where you left off" : "Play it again";
    document.getElementById("resume-song").textContent = `${point.song.title} · ${point.song.artist}`;
  } catch (_) { /* no saved progress to show */ }
});
