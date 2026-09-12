// Offline MCP startup probe: no model calls, credentials, or project mutations.
// Usage: node scripts/diagnose-pi-mcp-startup.mjs <adapter/index.ts> <jiti/lib/jiti.mjs> [wait]
import { createServer } from 'node:http';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { EventEmitter } from 'node:events';

const [adapterPath, jitiPath, mode] = process.argv.slice(2);
if (!adapterPath || !jitiPath) throw new Error('Provide adapter/index.ts and jiti/lib/jiti.mjs paths.');
const agentDir = mkdtempSync(join(tmpdir(), 'clerk-mcp-probe-'));
process.env.PI_CODING_AGENT_DIR = agentDir;
if (mode === 'wait') process.env.MCP_DIRECT_TOOLS = 'clerk/get_project_profile,clerk/search_documents,clerk/update_project_profile';
else delete process.env.MCP_DIRECT_TOOLS;
const required = ['get_project_profile', 'search_documents', 'update_project_profile'];
const server = createServer(async (req, res) => {
  if (req.method !== 'POST') { res.writeHead(405).end(); return; }
  let body = '';
  for await (const chunk of req) body += chunk;
  const message = JSON.parse(body);
  if (message.id === undefined) { res.writeHead(202).end(); return; }
  await new Promise(resolve => setTimeout(resolve, 100));
  const result = message.method === 'initialize'
    ? { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'probe', version: '1' } }
    : { tools: required.map(name => ({ name, description: name, inputSchema: { type: 'object', properties: {} } })) };
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ jsonrpc: '2.0', id: message.id, result }));
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const hooks = new Map();
const registered = new Map();
let active = [];
try {
  const { createJiti } = await import(pathToFileURL(jitiPath).href);
  const piRequire = createRequire(resolve(dirname(jitiPath), '../../../package.json'));
  const alias = Object.fromEntries(['typebox', '@earendil-works/pi-tui'].map(name => [name, piRequire.resolve(name)]));
  alias['@earendil-works/pi-coding-agent'] = resolve(dirname(jitiPath), '../../../dist/index.js');
  alias['@earendil-works/pi-ai'] = resolve(dirname(jitiPath), '../../@earendil-works/pi-ai/dist/compat.js');
  const jiti = createJiti(import.meta.url, { interopDefault: true, tryNative: false, alias });
  const { createMcpAdapter } = await jiti.import(adapterPath);
  createMcpAdapter({ config: { mcpServers: { clerk: {
    url: `http://127.0.0.1:${server.address().port}/mcp`, directTools: required,
  } } } })({
    on: (name, fn) => hooks.set(name, fn), events: new EventEmitter(),
    registerTool: tool => registered.set(tool.name, tool),
    registerCommand() {}, registerFlag() {}, getFlag() {},
    getAllTools: () => [...registered.values()], getActiveTools: () => active,
    setActiveTools: names => { active = names; },
  });
  await hooks.get('session_start')({}, { mode: 'print', hasUI: false, cwd: agentDir });
  const ready = required.every(name => [...registered.keys()].some(key => key.endsWith(name)));
  console.log(JSON.stringify({ readyBeforeFirstPrompt: ready, registered: [...registered.keys()] }));
  process.exitCode = ready ? 0 : 1;
} finally {
  await hooks.get('session_shutdown')?.();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  if (dirname(resolve(agentDir)) !== resolve(tmpdir())) throw new Error('Unexpected probe directory');
  rmSync(agentDir, { recursive: true, force: true });
}
