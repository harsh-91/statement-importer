# Private bug report receiver

This Cloudflare Worker accepts a small, bounded report from the desktop app and creates an issue in `harsh-91/statement-importer-bug-reports`. The GitHub token exists only as a Worker secret. The desktop app fetches the receiver URL from `https://harsh-91.github.io/neon-ledger/report-endpoint.json`, so the endpoint can change without repackaging the app.

## Setup

1. Create a **private** `harsh-91/statement-importer-bug-reports` repository and a `bug-report` label.
2. Create a fine-grained GitHub token restricted to that repository with **Issues: Read and write**. Do not put it in source control or in the desktop app.
3. Deploy `src/index.js` as the `statement-importer-report-relay` Cloudflare Worker. Configure the `REPORT_LIMITER` binding and `GITHUB_REPOSITORY` variable from `wrangler.toml`. The dashboard editor is sufficient; Wrangler OAuth is not required.
4. Add the restricted token as a production **Secret** named `GITHUB_TOKEN` in Worker Settings. The person creating the token enters it directly in Cloudflare; it must never be pasted into chat or source control.
5. In the Neon Ledger site repository, publish `report-endpoint.json` with `{"url":"https://<worker-host>/report"}`.
6. Send a synthetic test report and verify the private issue, then build new desktop downloads.

The receiver rejects large or malformed payloads and applies an IP-based limit. It does not accept browser CORS requests. Cloudflare and GitHub process the submitted report; update the site's privacy policy when activating it.
