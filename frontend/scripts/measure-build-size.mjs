import { readFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";
import path from "node:path";

const INITIAL_LIMIT = 250 * 1024;
const WORKFLOW_LIMIT = 150 * 1024;
const dist = path.resolve("dist");
const manifest = JSON.parse(
  await readFile(path.join(dist, ".vite", "manifest.json"), "utf8"),
);

function entry(source) {
  const match = Object.values(manifest).find((item) => item.src === source);
  if (!match) throw new Error(`Build manifest is missing ${source}`);
  return match;
}

function staticFiles(root) {
  const files = new Set();
  const visit = (item) => {
    if (files.has(item.file)) return;
    files.add(item.file);
    for (const key of item.imports ?? []) visit(manifest[key]);
  };
  visit(root);
  return files;
}

async function measurement(files) {
  let rawBytes = 0;
  let gzipBytes = 0;
  const entries = [];
  for (const file of [...files].sort()) {
    const content = await readFile(path.join(dist, file));
    const raw = content.byteLength;
    const gzip = gzipSync(content).byteLength;
    rawBytes += raw;
    gzipBytes += gzip;
    entries.push({ file, rawBytes: raw, gzipBytes: gzip });
  }
  return { rawBytes, gzipBytes, entries };
}

const shellFiles = staticFiles(entry("index.html"));
for (const file of staticFiles(entry("src/pages/ProjectCockpitPage.tsx"))) {
  shellFiles.add(file);
}
const tenderEntry = entry("src/pages/TenderCockpitPage.tsx");
const tenderFiles = new Set([tenderEntry.file]);
const styleFiles = staticFiles(entry("src/pages/StyleGenomeDemoPage.tsx"));
const styleRootFile = entry("src/pages/StyleGenomeDemoPage.tsx").file;
const threeFiles = [styleRootFile];
const leakedThree = [...shellFiles, ...tenderFiles].filter(
  (file) => file === styleRootFile || file.toLowerCase().includes("three"),
);

const report = {
  measuredAt: new Date().toISOString(),
  mode: process.argv.includes("--enforce") ? "enforced" : "report-only",
  budgets: {
    initialCockpitGzipBytes: INITIAL_LIMIT,
    workflowEntryGzipBytes: WORKFLOW_LIMIT,
  },
  initialCockpit: await measurement(shellFiles),
  tenderWorkflow: await measurement(tenderFiles),
  styleDemoThreeFiles: threeFiles,
  threeFilesOutsideStyleDemo: [...new Set(leakedThree)],
};

console.log(JSON.stringify(report, null, 2));

if (process.argv.includes("--enforce")) {
  const failures = [];
  if (report.initialCockpit.gzipBytes > INITIAL_LIMIT) {
    failures.push(`initial cockpit is ${report.initialCockpit.gzipBytes} gzip bytes`);
  }
  if (report.tenderWorkflow.gzipBytes > WORKFLOW_LIMIT) {
    failures.push(`tender workflow is ${report.tenderWorkflow.gzipBytes} gzip bytes`);
  }
  if (report.threeFilesOutsideStyleDemo.length) {
    failures.push("Three.js is reachable from a non-style-demo route");
  }
  if (failures.length) throw new Error(`Bundle budget failed: ${failures.join("; ")}`);
}
