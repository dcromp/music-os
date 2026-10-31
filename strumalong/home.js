"use strict";
// Preserve earlier shared links to Jukebox songs when the root becomes the mode chooser.
if (/^#\/(song|ready)\//.test(location.hash)) location.replace("jukebox.html" + location.search + location.hash);
