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

## 11. Existing-database failure recovery (v1.3.2)

- Added a five-second libpq connection timeout to all PostgreSQL connections, including managed setup.
- Changed the desktop WSGI server to threaded operation so a slow connection attempt cannot block unrelated local requests.
- Validates manual ports against the TCP range before connecting.
- Shows a visible bounded-progress state and returns a concise error with fields the user should verify.
- Added regression tests for timeout propagation, actionable error formatting, and threaded server configuration.

### v1.3.2 verification record

- Python compile check: passed.
- Unit suite: 23 of 23 tests passed, including the complete failed-manual-connection route.
- Real unreachable-host check against the reserved TEST-NET address: returned `ConnectionTimeout` in 5.01 seconds.
- PyInstaller Windows x64 application build: passed.
- Inno Setup 6.7.3 installer compile: passed; product version verified as 1.3.2.
- SHA-256: installer `8817714BFE8E0716A6697B23838B3A29E0994C6AD8B5147B9414ABA2E47BB27F`; application `B5FE82BD1DC48DD6DEF8AE24B432FD3084CF1C3EBFF838D126B9F9C9327B6DF8`.
- Authenticode inspection: `NotSigned`; public signing-status disclosure remains required.

## 12. Reliable application shutdown during upgrade (v1.3.3)

- Added a named Windows event that lets the installer request shutdown from v1.3.3 and later.
- The desktop listener stops the local web server before terminating the packaged process and releasing its executable.
- Installer upgrades first invoke the installed app with `--shutdown`, then wait up to three seconds.
- For older builds without shutdown support, setup uses `taskkill` once and waits up to five seconds.
- If the application still owns its mutex, setup stops with an actionable error rather than overwriting locked files.

### v1.3.3 verification record

- Python compile check: passed.
- Unit suite: 24 of 24 tests passed, including named-event shutdown signalling.
- Packaged `StatementImporter.exe --shutdown` smoke check: passed with exit code 0.
- PyInstaller Windows x64 application build: passed.
- Inno Setup 6.7.3 installer compile: passed; product version verified as 1.3.3.
- SHA-256: the exact installer digest is published in `SHA256SUMS.txt`; application `6CF3DDBEF39C787A38B1ABD67E36CEFC5472D2DECB13073F1BB0107577E2A04E`.
- Authenticode inspection: `NotSigned`; public signing-status disclosure remains required until SignPath Foundation approval.
- The compatibility fallback was not run against the user's active installed copy during verification, so no user process or data was disturbed.

## 13. Direct installer close path (v1.3.4)

- Disabled Inno Setup's generic `CloseApplications` feature, which was still emitting a blocking Restart Manager dialog on the user's Windows installation.
- Before file replacement, setup now directly invokes the installed copy with `--shutdown`, waits three seconds, then applies a bounded `taskkill` compatibility close only when replacing an existing per-user installation.
- The generic application-closing UI is no longer part of this installation path.

### v1.3.4 verification record

- Python compile check: passed.
- Unit suite: 24 of 24 tests passed.
- PyInstaller Windows x64 application build: passed.
- Inno Setup 6.7.3 installer compile: passed; product version verified as 1.3.4.
- SHA-256: the exact installer digest is published in `SHA256SUMS.txt`; application `F9998E0DEF877439D3D8C9C6F61964450416C5A3E9329CD78D9E1A28A00FB1DD`.
- Authenticode inspection: `NotSigned`; public signing-status disclosure remains required until SignPath Foundation approval.
- The actual forced close was not run against the user's active installation during verification, so no user process or data was disturbed.

## 14. Bounded upgrade preparation (v1.3.5)

- Replaced the blocking installer calls that could wait indefinitely for a previous PyInstaller launcher.
- The installer now starts the targeted compatibility close without waiting for that command, then pauses only two seconds before file replacement.
- Inno Setup's generic application-closing feature remains disabled.

### v1.3.5 verification record

- Python compile check: passed.
- Unit suite: 24 of 24 tests passed.
- PyInstaller Windows x64 application build: passed.
- Inno Setup 6.7.3 installer compile: passed; product version verified as 1.3.5.
- SHA-256: the exact installer digest is published in `SHA256SUMS.txt`.
- The new targeted close was not run against the user's active installation during verification, so no user process or data was disturbed.

## 15. Verified upgrades and visible onboarding (v1.4.0, 2026-09-22)

Earlier 1.3.x checks did not exercise the actual installer with a running executable. The fixed-delay/name-wide shutdown approach did not establish that files were released. Those records must not be interpreted as proof that all upgrade hangs were resolved.

- Replaced name-wide taskkill with exact-path process matching, normal window closure, and user-confirmed force closure.
- Each installer close check shows elapsed time, returns within a 20-second polling budget, and requires an exclusive executable-open check before allowing replacement. Failure blocks installation and offers retry/cancel or a restart fallback.
- Added an isolated compiler test mode without shortcuts or uninstall registration. The test installer blocks on a real running fixture process without changing its binary, then succeeds after closure and installs a byte-identical packaged executable.
- Added visible desktop startup and corrected Windows handle argument types and failed-wait handling.
- Database setup reports actual stages and elapsed time, rejects simultaneous setup attempts, restores controls on error, and opens the importer on success. The first-run page and navigation use clearer action labels.
- Database status subprocesses now have time limits; schema operations have a 10-second lock timeout and a 120-second per-statement timeout.
- Optional third-party prerequisite installation displays vendor/download windows and explains where to follow progress.

### Verification

- All 28 tests passed with RUN_INSTALLER_TEST=1, including the compiled installer test, exact-path force-close isolation, live progress, session separation, duplicate prevention, and failure recovery.
- Browser interaction test passed: progress/elapsed display, disabled duplicate submission, failure and retry, successful navigation, and no JavaScript errors. Screenshot reviewed at 1020px width.
- PyInstaller Windows application build passed. Production installer is compiled separately without TEST_BUILD.
- Tests use disposable fixture processes and installation folders; they do not terminate the user's installed app or change the user's financial database.
- Verification was performed on this Windows 11 host. A clean Windows 10/11 machine matrix, corporate PowerShell restrictions, and third-party prerequisite download failures remain additional compatibility work; this is not a universal compatibility certification.
- Published artifacts remain unsigned until trusted signing is available; SHA256SUMS.txt is authoritative for the release digest.

## 16. Database diagnostics and guided bug reports (v1.5.0, 2026-09-25)

- Added a local Diagnostics screen linked from the main navigation and database setup page.
- Added checks for supported Windows/runtime details, PostgreSQL tools, partial managed-cluster state, local port availability, managed-port reachability, saved database access, diagnostic-folder permissions and free space.
- Added a bounded 512 KiB setup event log with run identifiers, UTC timestamps, stages, completion timing and sanitized failures.
- Added a ZIP generator containing only a system summary, controlled check results and redacted setup events. It explicitly excludes bank statements, transactions, database contents, passwords, API keys, protected configuration values and raw PostgreSQL log contents.
- Added a guided email draft and report-folder action. The user reviews and manually attaches the ZIP; no diagnostic data is uploaded or sent automatically.

### Verification

- Python compilation passed for the application, desktop entry point, diagnostics module and tests.
- All 33 unit tests passed, including redaction, report contents, CSRF-protected report creation, setup-failure logging and email-draft path privacy.
- Both compiled-installer integration tests passed: the installer refused replacement while a target executable was busy, preserved an unrelated same-name process, and completed after safe release.
- Hardened the consented close helper with canonical Windows path comparison, a Win32 process-information fallback and a wait for the exact target process tree to exit; the bounded check remains below the installer's 20-second outer timeout.
- Browser checks passed at 320, 390, 760 and 1100 pixel widths with no horizontal overflow or JavaScript errors.
- The diagnostics and setup troubleshooting screens were visually reviewed on Windows 11.
- Raw PostgreSQL logs were intentionally excluded because they can contain user, database or statement-related identifiers.

## 17. Microsoft Store MSIX distribution (v1.6.0, 2026-09-25)

- Added an x64 full-trust MSIX manifest targeting supported Windows 10 and Windows 11 desktop systems.
- Added a deterministic PowerShell package builder that produces a PyInstaller onedir payload, retro tile assets, an unsigned Store submission MSIX and a SHA-256 sidecar.
- Pinned the EDB PostgreSQL 17.11 Windows binary archive to SHA-256 `B9424EE7BC60B52450FF910A3630225DF32E633F3CB29C1D126D9299D59AEA28` before bundling it.
- Changed PostgreSQL discovery to prefer the package-local runtime while retaining explicit override, PATH and conventional installation fallbacks.
- Kept database files, protected credentials and user settings under the Windows user profile so Store replacement does not erase them.
- Added Windows package-identity detection. MSIX installations use Store-managed updates and never open the legacy GitHub installer flow.
- Added a separate GitHub Actions workflow with locked Python dependencies, PostgreSQL archive caching and Store-package artifact upload.
- Documented the required Partner Center identity variables and made clear that development placeholders are not production identities.

### Verification

- All 36 unit tests passed; one optional compiled legacy-installer integration test was skipped by design.
- The Store-managed update page test confirms that installer download controls are absent in MSIX mode.
- Python compilation, PowerShell parsing and Appx manifest XML parsing passed.
- The PyInstaller onedir payload completed successfully and its non-UI `--shutdown` smoke path exited with code 0.
- A production-trusted package cannot be generated locally: Microsoft applies the trusted signature only after Partner Center submission and certification. Final Store identity validation and Windows clean-machine installation remain release-gate checks.

### Partner Center reservation

- Individual developer enrollment and Microsoft identity verification completed on 2026-09-25.
- **Neon Ledger** reserved as a draft MSIX app with Store ID `9NDGSCG87PVT`.
- Package identity confirmed directly in Partner Center: name `HarshNair.NeonLedger`, publisher `CN=2AD2CE84-2334-4A3E-AFF4-2D43D2936CB8`, and display name `Harsh Nair`.
- These values were added to the MSIX build defaults. A Store submission and certification have not yet occurred.

### First Store package build and submission draft

- Added a path-scoped `main` push trigger to the Store MSIX workflow; manual dispatch and version-tag builds remain available.
- GitHub Actions run [36161828030](https://github.com/harsh-91/statement-importer/actions/runs/36161828030) succeeded on 2026-09-25 for commit `45315ec`. It built the x64 desktop payload, verified and bundled the pinned PostgreSQL archive, packed the unsigned MSIX, generated its SHA-256 sidecar, and uploaded the `neon-ledger-msix` artifact (384 MB).
- The only job annotation is a non-blocking GitHub Actions Node.js 20 deprecation warning for `actions/cache@v4` and `actions/upload-artifact@v4`.
- The downloaded GitHub artifact ZIP matched its published SHA-256 digest `D3ADBF29F833FCF7FAC319CFAE77574893C1E5C408887FCD98559F580EDAC900`. The contained MSIX matched its sidecar SHA-256 `298A7703C47F752EA987B83D0EFBA2E61F13BDA141E8D75CA3CE510B5DB97AE1`, and its manifest contained the reserved identity, version `1.6.0.0`, x64 architecture, application executable and bundled PostgreSQL server.
- Partner Center submission 1 was started as a draft. The MSIX was uploaded and the Packages section became **Complete**, targeted only to Windows 10/11 Desktop. Partner Center warned that the `runFullTrust` restricted capability requires approval during certification.
- Pricing and availability, properties (including a privacy policy), age ratings, and the Store listing remain incomplete. The app has not been submitted for certification or published.
