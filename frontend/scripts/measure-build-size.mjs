import { readFile, stat } from "node:fs/promises";
import { gzipSync } from "node:zlib";
import path from "node:path";

const dist = path.resolve("dist");
const html = await readFile(path.join(dist, "index.html"), "utf8");
const scripts = [...html.matchAll(/<script[^>]+src=["']([^"']+)["']/g)].map(
  (match) => match[1],
);

if (scripts.length === 0) {
  throw new Error("No initial JavaScript entry was found in dist/index.html");
}

let rawBytes = 0;
let gzipBytes = 0;
const entries = [];
for (const source of scripts) {
  const file = path.join(dist, source.replace(/^\//, ""));
  const content = await readFile(file);
  const raw = (await stat(file)).size;
  const gzip = gzipSync(content).byteLength;
  rawBytes += raw;
  gzipBytes += gzip;
  entries.push({ file: source, rawBytes: raw, gzipBytes: gzip });
}

console.log(
  JSON.stringify(
    {
      measuredAt: new Date().toISOString(),
      mode: "report-only",
      initialJavaScript: { rawBytes, gzipBytes },
      entries,
    },
    null,
    2,
  ),
);
