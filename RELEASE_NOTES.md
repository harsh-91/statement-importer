<!-- Created by Harsh (@harsh-91) | Made in India -->
# Statement Importer 1.1.0

Created by **Harsh** ([@harsh-91](https://github.com/harsh-91)) · Made in India 🇮🇳

## Highlights

- Offline-first Windows desktop statement importer backed by PostgreSQL.
- Structural recognition and reconciliation for SBI, ICICI Bank, and IndusInd Bank statements.
- Safe mapping workflow for additional CSV and Excel layouts.
- Duplicate-safe bank tables and normalized unified reporting view.
- Local transaction browser, import audit history, and formula-safe CSV export.
- Opt-in localhost REST API and MCP tools with hashed access keys.
- Verified database backups and read-only reporting-user creation.
- Conventional x64 Windows setup with PostgreSQL and WebView2 checks.
- Retro 1980s 8-bit interface.

## Requirements

- Windows 10 build 17763 or newer, or Windows 11, on x64 hardware.
- PostgreSQL; version 17 is the primary tested version.
- Microsoft Edge WebView2 Runtime.

The installer can offer optional winget prerequisite downloads. Once prerequisites are present, core operation requires no internet connection.

## Install

1. Download `StatementImporter-1.1.0-Setup-x64.exe` and `SHA256SUMS.txt`.
2. Verify the installer SHA-256 checksum.
3. Run the installer and review its prerequisite screen.
4. Launch Statement Importer and configure the local PostgreSQL connection.

## Distribution notice

Statement Importer is open-source software distributed under the MIT License. The installer is not Authenticode-signed, so Windows SmartScreen may show an unknown-publisher warning. This release is not represented as regulated financial software and should receive independent review before regulated or high-risk use.
