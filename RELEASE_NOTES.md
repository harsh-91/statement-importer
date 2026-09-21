<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Statement Importer 1.3.5

Created by **Harsh** ([@harsh-91](https://github.com/harsh-91)) · Made in India 🇮🇳

## Highlights

- Fixed Windows Setup remaining indefinitely on “Preparing to Install” during an upgrade.
- Setup no longer waits for an older application launcher to exit.
- Setup uses a non-blocking targeted close for the existing installed copy, then waits a fixed two seconds before replacing files.

- Fixed the Advanced existing-database wizard freezing when PostgreSQL is unreachable.
- Connection attempts now stop after five seconds and return an actionable error.
- The embedded server remains responsive while a database connection is being attempted.

- Changed the project license for this and future releases to Apache License 2.0.
- Added an Apache `NOTICE` preserving creator attribution: Harsh Nair · Made in India.
- Added SPDX `Apache-2.0` identifiers throughout the source distribution.

- Offline-first Windows desktop statement importer backed by PostgreSQL.
- Structural recognition and reconciliation for SBI, ICICI Bank, and IndusInd Bank statements.
- Safe mapping workflow for additional CSV and Excel layouts.
- Duplicate-safe bank tables and normalized unified reporting view.
- Local transaction browser, import audit history, and formula-safe CSV export.
- Opt-in localhost REST API and MCP tools with hashed access keys.
- Verified database backups and read-only reporting-user creation.
- Conventional x64 Windows setup with PostgreSQL and WebView2 checks.
- Retro 1980s 8-bit interface.
- One-click first-run setup of an isolated, localhost-only PostgreSQL cluster.
- Generated owner and least-privilege app credentials protected with Windows DPAPI.
- Automatic managed-database startup and password-free creation of read-only DBeaver credentials.
- Existing PostgreSQL connections remain available in the Advanced setup section.
- New in-app update center with manual checks and optional launch-time checks.
- Update discovery is restricted to the official GitHub release and never uploads financial data.
- Downloads and installation require explicit clicks; no silent or forced updates.
- Installers are blocked unless the release checksum matches and Windows validates a SignPath Foundation Authenticode signature.
- Offline importing, reconciliation, PostgreSQL, REST, and MCP operation are unchanged.

## Requirements

- Windows 10 build 17763 or newer, or Windows 11, on x64 hardware.
- PostgreSQL; version 17 is the primary tested version.
- Microsoft Edge WebView2 Runtime.

The installer can offer optional winget prerequisite downloads. Once prerequisites are present, core operation requires no internet connection.

## Install

1. Cancel any older installer currently showing a closing-applications error.
2. Download `StatementImporter-1.3.5-Setup-x64.exe` and `SHA256SUMS.txt`.
3. Verify the installer SHA-256 checksum.
4. Run the installer; it safely closes the previous application version during upgrade.
5. Launch Statement Importer and click **Create my local database automatically**.

## Distribution notice

Statement Importer 1.3.5 is open-source software distributed under the Apache License 2.0. Versions through 1.3.0 retain their original MIT terms. Check the release page for the signing status of this installer, verify its published SHA-256, and review the [code signing policy](https://github.com/harsh-91/statement-importer/blob/main/CODE_SIGNING.md). The in-app updater refuses unsigned installers. This release is not represented as regulated financial software and should receive independent review before regulated or high-risk use.
