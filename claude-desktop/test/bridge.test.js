const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const test = require('node:test');

const bridge = path.join(__dirname, '..', 'server', 'index.js');

test('forwards MCP requests to loopback with the configured key', () => {
  const mockFetch = `global.fetch = async (url, options) => {
    if (url !== 'http://127.0.0.1:8765/mcp' || options.headers.Authorization !== 'Bearer test-key') {
      throw new Error('unexpected destination or credential');
    }
    return { json: async () => ({ jsonrpc: '2.0', id: 7, result: { tools: [] } }) };
  }; require(${JSON.stringify(bridge)});`;
  const run = spawnSync(process.execPath, ['-e', mockFetch], {
    env: { ...process.env, NEON_LEDGER_API_KEY: 'test-key' },
    input: '{"jsonrpc":"2.0","id":7,"method":"tools/list"}\n',
    encoding: 'utf8'
  });
  assert.equal(run.status, 0, run.stderr);
  assert.deepEqual(JSON.parse(run.stdout), { jsonrpc: '2.0', id: 7, result: { tools: [] } });
});

test('does not print a configured key when the app is unavailable', () => {
  const run = spawnSync(process.execPath, [bridge], {
    env: { ...process.env, NEON_LEDGER_API_KEY: 'private-test-key' },
    input: '{"jsonrpc":"2.0","id":8,"method":"tools/list"}\n',
    encoding: 'utf8'
  });
  assert.equal(run.status, 0, run.stderr);
  assert.equal(JSON.parse(run.stdout).error.code, -32000);
  assert.doesNotMatch(run.stdout + run.stderr, /private-test-key/);
});
