// Local stdio bridge for Claude Desktop. No network destination is configurable:
// transaction requests are sent only to the Statement Importer loopback server.
const readline = require('node:readline');

const ENDPOINT = 'http://127.0.0.1:8765/mcp';
const key = process.env.NEON_LEDGER_API_KEY;
const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

function reply(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

async function forward(line) {
  let request;
  try {
    request = JSON.parse(line);
  } catch {
    console.error('Neon Ledger MCP: invalid JSON from client');
    return;
  }
  if (!request || typeof request !== 'object' || Array.isArray(request)) return;
  // Claude may send notifications without ids. The app needs initialized; it
  // does not require cancellation or other notification methods.
  if (request.id === undefined && request.method !== 'notifications/initialized') return;
  if (!key) {
    if (request.id !== undefined) reply({ jsonrpc: '2.0', id: request.id, error: {
      code: -32000, message: 'Add a read-only key in the Neon Ledger extension settings.'
    } });
    return;
  }

  try {
    const response = await fetch(ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        Authorization: `Bearer ${key}`
      },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(30000)
    });
    if (request.id === undefined) return;
    const body = await response.json();
    if (body && body.jsonrpc === '2.0' && (body.result !== undefined || body.error !== undefined)) {
      reply(body);
      return;
    }
    const message = response.status === 401 ? 'The read-only key is invalid or revoked.'
      : response.status === 403 ? 'Enable MCP in Statement Importer > API / MCP.'
      : `Statement Importer returned HTTP ${response.status}.`;
    reply({ jsonrpc: '2.0', id: request.id, error: { code: -32000, message } });
  } catch (error) {
    if (request.id !== undefined) reply({ jsonrpc: '2.0', id: request.id, error: {
      code: -32000,
      message: error.cause?.code === 'ECONNREFUSED'
        ? 'Open Statement Importer and enable MCP in API / MCP.'
        : 'Could not reach the local Statement Importer MCP server.'
    } });
  }
}

input.on('line', (line) => { void forward(line); });
