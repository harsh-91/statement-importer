<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Statement Importer

**Created by [Harsh (@harsh-91)](https://github.com/harsh-91) · Made in India 🇮🇳**

Offline-first Windows desktop application for reconciling bank statements into PostgreSQL. The UI uses an accessible 1980s terminal and 8-bit visual system.

## Install

Download `StatementImporter-1.3.3-Setup-x64.exe` from the repository's [latest release](https://github.com/harsh-91/statement-importer/releases/latest). The standard Windows wizard provides per-user installation, controlled application shutdown during upgrades, shortcut choices, Programs & Features registration, and a data-preserving uninstaller.

This build targets supported 64-bit Intel/AMD editions of Windows 10 (build 17763+) and Windows 11. The setup checks the platform, PostgreSQL, and Microsoft Edge WebView2; PostgreSQL and WebView2 can be installed through winget or supplied manually.

The setup detects PostgreSQL and Microsoft Edge WebView2. If either is unavailable, select its optional winget task when internet is available or install it independently.

The application itself, statement processing, PostgreSQL access, REST API, and MCP endpoint require no internet connection.

From version 1.3.0, open **Updates** to check the official GitHub release manually or opt in to a launch-time check. The app never downloads or installs an update silently. A downloaded installer is accepted only when its SHA-256 matches the published manifest and Windows reports a valid SignPath Foundation Authenticode signature. Users on an earlier build must install 1.3.0 manually once to gain this updater.

On first launch, choose **Create my local database automatically**. The app creates an isolated local PostgreSQL cluster, database, and least-privilege application login. Generated credentials are protected for the current Windows account with DPAPI. Manual server fields remain available under **Advanced**.

## Supported statements

- State Bank of India
- ICICI Bank
- IndusInd Bank
- Unknown CSV or Excel layouts through the safe mapping terminal

Files are detected from their structure rather than filename. Encrypted statements support per-file passwords or one batch password. Statement passwords are never saved.

> Never upload real statements, `.env` files, database backups, API keys, or screenshots containing account data to GitHub. This repository intentionally contains no personal financial data.

## Database

Bank tables use safe names such as:

- `bank_sbi_transactions`
- `bank_icici_transactions`
- `bank_indusind_transactions`

`unified_bank_transactions` exposes the normalized reporting layer. Transaction fingerprints prevent duplicate imports across renamed and overlapping files.

## REST and MCP

Open **API / MCP** inside the app. Both services are disabled by default and bind to `127.0.0.1:8765`.

- REST base: `http://127.0.0.1:8765/api/v1`
- OpenAPI: `http://127.0.0.1:8765/api/v1/openapi.json`
- MCP: `http://127.0.0.1:8765/mcp`

Generate a read-only key and send it as `X-API-Key` or `Authorization: Bearer`.

Excel, Power BI, Tableau, and DBeaver may also connect directly to PostgreSQL and query `unified_bank_transactions`.

## Safety controls

- Unknown statement files are encrypted for the current Windows user with DPAPI and expire after 24 hours.
- Imports reconcile balances before insertion, use exact decimals, run transactionally, serialize per bank, and deduplicate with stable SHA-256 fingerprints.
- Spreadsheet exports neutralize formula prefixes.
- Local browser responses use restrictive security headers; API and MCP calls are authenticated and rate-limited.
- Open **Safety** to create and verify a PostgreSQL backup or create a least-privilege reporting login using one-time administrator credentials.
- Runtime and build dependency versions are locked in the supplied manifests.

## Development

```powershell
.\setup_utility.ps1
.\run_utility.ps1
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe .\scripts\smoke_access.py
.\.venv\Scripts\python.exe .\scripts\smoke_mapping.py
.\.venv\Scripts\python.exe .\scripts\smoke_maintenance.py
```

Build the app and setup executable:

```powershell
.\build_windows.ps1
```

When Inno Setup 6/7 or the project-local compiler is available, the build also produces the conventional `StatementImporter-1.3.3-Setup-x64.exe` installer from `installer\StatementImporter.iss`.

See `IMPLEMENTATION_REPORT.md` for the full incremental implementation and test record.

## Creator and license

Created by **Harsh** ([@harsh-91](https://github.com/harsh-91)) and made in India. 🇮🇳

Statement Importer releases from version 1.3.1 are open-source software under the [Apache License 2.0](LICENSE.md), including its explicit patent grant and redistribution conditions. Preserve the [NOTICE](NOTICE) attribution in derivative distributions. Versions through 1.3.0 remain available under their original MIT terms. See [SECURITY.md](SECURITY.md) before reporting a vulnerability and [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## Public distribution

Release artifacts must be checked individually: the release page and [code signing policy](CODE_SIGNING.md) state whether a build is signed. Unsigned builds may trigger Windows SmartScreen and cannot be installed by the in-app updater. Always verify the supplied SHA-256 checksum. This software is suitable for personal use and controlled beta testing, not regulated financial processing without independent security review and clean-machine certification.
