# Private bug report receiver

This Cloudflare Worker accepts a small, bounded report from the desktop app and creates an issue in `harsh-91/statement-importer-bug-reports`. The GitHub token exists only as a Worker secret. The desktop app fetches the receiver URL from `https://harsh-91.github.io/neon-ledger/report-endpoint.json`, so the endpoint can change without repackaging the app.

## Setup

1. Create a **private** `harsh-91/statement-importer-bug-reports` repository and a `bug-report` label.
2. Create a fine-grained GitHub token restricted to that repository with **Issues: Read and write**. Do not put it in source control or in the desktop app.
3. Sign in to Cloudflare Wrangler and deploy from this directory with `npx wrangler deploy`.
4. Set `GITHUB_TOKEN` with `npx wrangler secret put GITHUB_TOKEN` and paste the token only into Wrangler's secret prompt.
5. In the Neon Ledger site repository, publish `report-endpoint.json` with `{"url":"https://<worker-host>/report"}`.
6. Send a synthetic test report and verify the private issue, then build new desktop downloads.

The receiver rejects large or malformed payloads and applies an IP-based limit. It does not accept browser CORS requests. Cloudflare and GitHub process the submitted report; update the site's privacy policy when activating it.
