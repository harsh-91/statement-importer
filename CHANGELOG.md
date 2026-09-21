<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Changelog

Created by Harsh · Made in India 🇮🇳

## 1.3.5 - 2026-09-21

- Fixed setup remaining indefinitely on “Preparing to Install” while waiting for an older one-file application launcher to exit.
- Replaced the blocking close command with a non-blocking targeted close and a fixed two-second bounded wait before file replacement.

## 1.3.4 - 2026-09-21

- Removed Inno Setup's generic automatic application-closing phase, which could still show a blocking Restart Manager dialog.
- The installer now runs its own direct close routine before copying files: a controlled shutdown for new builds and a bounded compatibility close for older ones.
- The direct routine is only invoked when replacing an existing per-user Statement Importer installation.

## 1.3.3 - 2026-09-21

- Fixed upgrades getting stuck at “Closing applications.”
- Added a named Windows shutdown signal for controlled in-app exit during future upgrades.
- Added a bounded compatibility fallback that closes pre-1.3.3 processes before files are replaced.
- Setup now stops with an actionable message if the application still cannot be closed.

## 1.3.2 - 2026-09-21

- Prevented the existing-database wizard from hanging on unreachable PostgreSQL servers.
- Added a five-second timeout to every PostgreSQL connection.
- Made the embedded desktop web server concurrent so one failed connection cannot block the application.
- Added visible connection progress, port validation, and a layman-friendly failure message.

## 1.3.1 - 2026-09-21

- Relicensed this and future releases under Apache License 2.0.
- Added a NOTICE file preserving creator and Made in India attribution.
- Added SPDX `Apache-2.0` identifiers throughout the source distribution.
- Versions through 1.3.0 remain under their original MIT terms.

## 1.3.0 - 2026-09-21

- Added a privacy-conscious update center with manual and optional launch-time checks.
- Restricted release metadata and downloads to official GitHub HTTPS hosts.
- Added exact asset, size, SHA-256 manifest, GitHub digest, and SignPath Foundation Authenticode validation.
- Kept downloads and installation explicitly user initiated; offline behavior is unchanged.

## 1.2.0 - 2026-09-21

- Added one-click managed local PostgreSQL provisioning and automatic restart.
- Protected generated database credentials using Windows DPAPI.
- Added password-free read-only DBeaver credential creation for managed databases.

## 1.1.1 - 2026-09-21

- Released the project as open-source software under the MIT License.
- Added the MIT license to installed and portable distribution packages.

## 1.1.0 - 2026-09-21

- Added conventional x64 Windows installer and prerequisite detection.
- Added verified backup and read-only reporting-user workflows.
- Hardened temporary-file encryption, workbook validation, CSV export, API/MCP access, and import concurrency.
- Added unknown-bank mapping and dynamic unified PostgreSQL reporting view.
- Added REST API, MCP endpoint, import history, and transaction browser.
