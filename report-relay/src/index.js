const MAX_BYTES = 16 * 1024;
const REPOSITORY = "harsh-91/statement-importer-bug-reports";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function boundedText(value, limit) {
  return typeof value === "string" ? value.trim().slice(0, limit) : "";
}

function validate(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const description = boundedText(payload.description, 2001);
  const diagnostics = payload.diagnostics;
  if (description.length < 10 || description.length > 2000 || !diagnostics || typeof diagnostics !== "object") return null;
  const reportId = boundedText(diagnostics.report_id, 50);
  const version = boundedText(diagnostics.application_version, 30);
  if (!/^SI-[A-Za-z0-9-]{1,47}$/.test(reportId) || !/^[0-9][A-Za-z0-9.+-]{0,29}$/.test(version)) return null;
  if (!Array.isArray(diagnostics.checks) || diagnostics.checks.length > 20) return null;
  const checks = diagnostics.checks.map((item) => {
    if (!item || typeof item !== "object" || !["pass", "warn", "fail"].includes(item.status)) return null;
    return { name: boundedText(item.name, 80), status: item.status, detail: boundedText(item.detail, 500) };
  });
  if (checks.some((item) => !item)) return null;
  const system = diagnostics.system;
  if (!system || typeof system !== "object") return null;
  return {
    description,
    diagnostics: {
      report_id: reportId,
      application_version: version,
      system: {
        os: boundedText(system.os, 80),
        release: boundedText(system.release, 80),
        architecture: boundedText(system.architecture, 80),
      },
      checks,
    },
  };
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST" || new URL(request.url).pathname !== "/report") return json({ error: "Not found" }, 404);
    if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") return json({ error: "JSON required" }, 415);
    const length = Number(request.headers.get("content-length") || 0);
    if (length > MAX_BYTES) return json({ error: "Report too large" }, 413);
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const allowance = await env.REPORT_LIMITER.limit({ key: ip });
    if (!allowance.success) return json({ error: "Try again later" }, 429);
    const raw = await request.text();
    if (new TextEncoder().encode(raw).length > MAX_BYTES) return json({ error: "Report too large" }, 413);
    let payload;
    try { payload = validate(JSON.parse(raw)); } catch { return json({ error: "Invalid JSON" }, 400); }
    if (!payload) return json({ error: "Invalid report" }, 400);
    if (!env.GITHUB_TOKEN || env.GITHUB_REPOSITORY !== REPOSITORY) return json({ error: "Receiver unavailable" }, 503);
    const { diagnostics, description } = payload;
    const fence = String.fromCharCode(96).repeat(3);
    const issue = {
      title: "[Bug] Statement Importer " + diagnostics.application_version + " " + diagnostics.report_id,
      body: "## User description\n\n" + description + "\n\n## Diagnostics\n\n" + fence + "json\n" +
        JSON.stringify(diagnostics, null, 2).replaceAll(fence, String.fromCharCode(96) + " " + String.fromCharCode(96) + " " + String.fromCharCode(96)) + "\n" + fence + "\n",
      labels: ["bug-report"],
    };
    let result;
    try {
      result = await fetch("https://api.github.com/repos/" + REPOSITORY + "/issues", {
        method: "POST",
        headers: {
          authorization: "Bearer " + env.GITHUB_TOKEN,
          accept: "application/vnd.github+json",
          "content-type": "application/json",
          "user-agent": "statement-importer-report-relay",
          "x-github-api-version": "2022-11-28",
        },
        body: JSON.stringify(issue),
      });
    } catch { return json({ error: "GitHub unavailable" }, 502); }
    if (!result.ok) return json({ error: "GitHub rejected the report" }, 502);
    const created = await result.json();
    if (typeof created.html_url !== "string" || !created.html_url.startsWith("https://github.com/" + REPOSITORY + "/issues/")) {
      return json({ error: "Unexpected GitHub response" }, 502);
    }
    return json({ issue_url: created.html_url }, 201);
  },
};
