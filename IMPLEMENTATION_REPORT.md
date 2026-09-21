<!-- Created by Harsh (@harsh-91) | Made in India -->
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
