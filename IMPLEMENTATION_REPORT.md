<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Statement Importer implementation report

Created by Harsh · Made in India 🇮🇳

This public report intentionally excludes personal statement names, passwords, account identifiers, transaction counts, database dumps, and other private verification data.

## 1. Database foundation

- Added PostgreSQL tables for SBI, ICICI Bank, IndusInd Bank, mapped banks, bank profiles, import batches, file results, errors, settings, API credentials, and audit events.
- Added stable SHA-256 transaction fingerprints and unique indexes for idempotent imports.
- Added a normalized `unified_bank_transactions` reporting view.
- Kept schema creation and migrations idempotent.

## 2. Deterministic parsing and reconciliation

- Uses exact `Decimal` monetary arithmetic and explicit date formats.
- Detects known banks from workbook structure rather than filenames.
- Verifies running balances before insertion.
- Applies statement-specific controls where available.
- Rejects malformed amounts, ambiguous debit/credit rows, out-of-period dates, suspicious OOXML archives, and unsafe mapping definitions.

## 3. Desktop workflow

- Added a local Flask service hosted inside a pywebview desktop window.
- Added multi-file upload, per-file passwords, batch fallback password, result summaries, transaction browsing, import history, and CSV export.
- Added the 1980s retro 8-bit visual system and reduced-effects control.
- Added visible creator attribution: Harsh · Made in India.

## 4. Unknown-bank mapping

- Stores pending documents only on the local machine.
- Protects pending payloads with Windows DPAPI and expires them after 24 hours.
- Requires explicit column mapping and running-balance reconciliation.
- Creates a sanitized bank table and refreshes the unified view transactionally.

## 5. API and MCP

- Added opt-in read-only REST endpoints for transactions, accounts, banks, balances, schema, and import history.
- Added a bounded JSON-RPC MCP tools surface.
- Keeps both services disabled by default and bound to localhost.
- Hashes API keys, supports revocation, adds request throttling, and emits restrictive browser-security headers.

## 6. Operational safety

- Serializes concurrent imports per bank with PostgreSQL advisory locks.
- Writes transaction rows and per-file success audits atomically.
- Marks interrupted imports during recovery.
- Neutralizes spreadsheet-formula prefixes in CSV exports.
- Adds verified PostgreSQL custom-format backups.
- Adds a least-privilege reporting-user workflow.
- Uses Windows DPAPI for saved PostgreSQL credentials.

## 7. Windows packaging

- Added a standalone PyInstaller desktop executable.
- Added an Inno Setup x64 installer with stable application ID, upgrades, shortcuts, Programs & Features registration, prerequisite detection, and data-preserving uninstall.
- Locked runtime and build dependency versions.
- Publishes SHA-256 checksums with release artifacts.

## Verification performed

- Parser primitive and security unit tests.
- DPAPI pending-file round trip and expiry tests.
- Malformed and suspiciously compressed workbook tests.
- CSV formula-injection tests.
- Unknown-bank mapping integration test using synthetic data.
- REST, CSV, API-key, and MCP integration tests.
- Real PostgreSQL backup creation and `pg_restore --list` verification.
- Isolated installer install, application launch, health check, and uninstall cycle.

## Current assurance boundary

The project is suitable for personal use and controlled beta evaluation. It is not represented as regulated financial software. Public production deployment still benefits from Authenticode signing, independent penetration testing, clean-machine compatibility testing, hostile-file fuzzing, and documented organizational backup and recovery procedures.

## 8. Layman-friendly local database setup (v1.2.0)

- Added a recommended one-click first-run path that initializes an isolated local PostgreSQL cluster.
- Generates separate owner and least-privilege application credentials with cryptographically secure randomness.
- Protects generated credentials with Windows DPAPI and never places passwords on a command line.
- Binds the managed server to `127.0.0.1`, selects a dedicated local port, and starts it automatically on later launches.
- Preserves the existing manual PostgreSQL connection form under an Advanced section.
- Makes missing-prerequisite installer tasks selected by default when PostgreSQL or WebView2 is absent.

### v1.2.0 verification record

- Python compile check: passed for application, desktop host, installer launcher, modules, scripts, and tests.
- Unit suite: 13 of 13 tests passed, including dedicated-port selection and least-privilege managed settings.
- First-run page render check: passed for the recommended one-click action and Advanced manual fallback.
- PyInstaller Windows x64 application build: passed.
- Inno Setup 6.7.3 installer compile: passed; product version verified as 1.2.0.
- SHA-256 generated for the setup package and embedded application executable.
- Authenticode status remains `NotSigned` until the submitted SignPath Foundation application is approved.
- A full temporary-cluster smoke run was attempted in the Codex sandbox. PostgreSQL initialization completed, but `pg_ctl` rejected the sandbox's restricted Windows token before server start (`error code 87`). This is an environment boundary, not recorded as a pass; clean-machine non-elevated verification remains required before broad distribution.

## 9. Safe in-app updates (v1.3.0)

- Added a dedicated update screen with a manual check and an opt-in launch-time check.
- Uses only the official `harsh-91/statement-importer` GitHub release endpoint and allowlisted GitHub HTTPS download hosts.
- Requires the exact versioned x64 installer and `SHA256SUMS.txt` release assets.
- Enforces a 250 MB download limit, exact byte count, published SHA-256, and the GitHub asset digest when available.
- Uses Windows Authenticode verification and requires a valid SignPath Foundation signer before a download is promoted to installable state.
- Re-verifies both file hash and Authenticode immediately before opening the installer.
- Never downloads or installs silently. Background checks swallow offline failures and do not affect local statement processing.

### v1.3.0 verification record

- Python compile check: passed.
- Unit suite: 19 of 19 tests passed, including strict version and URL handling, exact checksum selection, verified-download success, and unsigned-download rejection.
- Flask update-page render check without network access: passed.
- Live read-only GitHub release API check: passed; v1.2.0 was correctly identified as older than the running v1.3.0 code.
- PyInstaller Windows x64 application build: passed.
- Inno Setup 6.7.3 installer compile: passed; product version verified as 1.3.0.
- SHA-256: installer `589FAE2985D8A4C65B7C038F47DD26C7130A0EAF21A9BAD7DC8654050B90E5C2`; application `CA8DC6E47912ABB9403415185AAC1F1AD1F35622F63A2DFE4C8D557B7582B39B`.
- Authenticode inspection: both artifacts remain `NotSigned`; this is disclosed, and the updater intentionally refuses them until SignPath Foundation signing is available.

## 10. Apache-2.0 licensing (v1.3.1)

- Replaced the MIT license for version 1.3.1 and future releases with the complete Apache License 2.0 text from the Apache Software Foundation.
- Added a distributable `NOTICE` with copyright, creator, and Made in India attribution.
- Added SPDX `Apache-2.0` identifiers throughout the source and documentation files.
- Included both `LICENSE.md` and `NOTICE` in the Windows installer and portable setup payload.
- Preserved the historical licensing record: versions through 1.3.0 remain available under their original MIT terms.

### v1.3.1 verification record

- Official Apache License 2.0 text comparison: passed after whitespace normalization.
- Python compile check: passed.
- Unit suite: 19 of 19 tests passed.
- PyInstaller Windows x64 application build: passed.
- Inno Setup 6.7.3 installer compile: passed and confirmed inclusion of `LICENSE.md` and `NOTICE`; product version verified as 1.3.1.
- SHA-256: installer `D094B90E4577A020438B50462FFA1FF8CA7D3A90271A63B3A43C3E66CD50081A`; application `FB27BD0B20868290314ACADAA192AED820AF375EAF3B0850A9B8D85115C4CDD3`.
- Authenticode inspection: `NotSigned`; public signing-status disclosure remains required.
