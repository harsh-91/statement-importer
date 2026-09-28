<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Statement Importer for macOS (beta)

The Mac beta uses the same local statement parser, PostgreSQL schema, desktop interface, REST API, and MCP endpoint as the Windows app. Builds are produced separately for Apple Silicon (`arm64`) and Intel (`x64`) Macs.

## Requirements

- macOS 15 or newer on Apple Silicon or Intel. Earlier versions have not been tested.
- PostgreSQL 17 tools installed with [Postgres.app](https://postgresapp.com/) or Homebrew (`brew install postgresql@17`). The app creates its own database cluster and does not need the Homebrew PostgreSQL service running.
- An unlocked login Keychain. Statement Importer stores its local encryption key there; the database and pending statement files stay under `~/Library/Application Support/StatementImporter`.

## Install and start

1. Download the ZIP for your Mac architecture from the official beta release and compare its SHA-256 with the release's checksum.
2. Extract `Statement Importer.app` and move it to Applications.
3. Open the app and choose **Set up storage and continue**. If PostgreSQL tools are not found, install them and reopen the app. You can also connect an existing PostgreSQL server under **Advanced**.
4. Create a verified backup from **Safety** before relying on the beta for important data.

This beta is ad hoc signed for local execution, but it is **not Developer ID signed or notarized**. macOS may block a downloaded copy. Use it only if you trust the official GitHub release and its SHA-256. A broadly distributable build requires Apple Developer ID signing and notarization.

The Mac beta checks neither downloads nor installs updates automatically. Check the official release page for later versions and replace the app manually. User data and Keychain credentials remain outside the app bundle.

## Build

The `Build macOS beta` GitHub Actions workflow creates separate Apple Silicon and Intel app ZIPs and checksums. It runs the Mac support and parser tests, verifies the app's ad hoc signature, and uploads temporary workflow artifacts. Release assets and website download links must only be published after a build is inspected and tested on a Mac.
