import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/index.js";

const payload = {
  description: "Database setup fails on first launch",
  diagnostics: {
    report_id: "SI-20260928-120000-ABC123",
    application_version: "1.6.2",
    system: { os: "Windows", release: "11", architecture: "AMD64" },
    checks: [{ name: "PostgreSQL tools", status: "fail", detail: "Tools missing" }],
  },
};
const env = {
  GITHUB_TOKEN: "test-token",
  GITHUB_REPOSITORY: "harsh-91/statement-importer-bug-reports",
  REPORT_LIMITER: { limit: async () => ({ success: true }) },
};
const request = (data) => new Request("https://relay.example/report", {
  method: "POST", headers: { "content-type": "application/json", "cf-connecting-ip": "127.0.0.1" }, body: JSON.stringify(data),
});

test("creates a private triage issue from a valid report", async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify({ html_url: "https://github.com/harsh-91/statement-importer-bug-reports/issues/1" }), { status: 201 });
  };
  try {
    const response = await worker.fetch(request(payload), env);
    assert.equal(response.status, 201);
    assert.equal(captured.url, "https://api.github.com/repos/harsh-91/statement-importer-bug-reports/issues");
    assert.equal(JSON.parse(captured.options.body).labels[0], "bug-report");
    assert.equal((await response.json()).issue_url, "https://github.com/harsh-91/statement-importer-bug-reports/issues/1");
  } finally { globalThis.fetch = originalFetch; }
});

test("rejects invalid and rate limited reports before contacting GitHub", async () => {
  assert.equal((await worker.fetch(request({ ...payload, description: "short" }), env)).status, 400);
  assert.equal((await worker.fetch(request(payload), { ...env, REPORT_LIMITER: { limit: async () => ({ success: false }) } })).status, 429);
});
