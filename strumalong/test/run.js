"use strict";
// Runs every strumalong/test/*.test.js file. Each file prints its own pass count and throws
// on failure. Exits non-zero if any file throws (including an async rejection).
// Usage: node strumalong/test/run.js
const fs = require("node:fs");
const path = require("node:path");

const dir = __dirname;
const files = fs.readdirSync(dir).filter(name => name.endsWith(".test.js")).sort();
const failures = [];
const pending = [];

process.on("unhandledRejection", error => { failures.push(`unhandled rejection: ${error && error.message ? error.message : error}`); });

for (const name of files) {
  console.log(`# ${name}`);
  try {
    const exported = require(path.join(dir, name));
    // Optional async support: a file may export a promise that rejects on failure.
    if (exported && typeof exported.then === "function") {
      pending.push(exported.then(() => {}, error => { failures.push(`${name}: ${error && error.message ? error.message : error}`); }));
    }
  } catch (error) {
    failures.push(`${name}: ${error && error.message ? error.message : error}`);
    console.error(`  ${name} failed: ${error && error.stack ? error.stack.split("\n").slice(0, 4).join("\n  ") : error}`);
  }
}

Promise.all(pending).then(() => {
  if (!files.length) { console.error("No test files found."); process.exitCode = 1; return; }
  if (failures.length) {
    console.error(`\n${failures.length} of ${files.length} test file(s) failed:\n  - ${failures.join("\n  - ")}`);
    process.exitCode = 1;
  } else {
    console.log(`\nAll ${files.length} test file(s) passed.`);
  }
});
