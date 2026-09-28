<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Code signing policy

## Current status

Statement Importer releases must not be represented as signed until a trusted Authenticode signature has been applied and independently verified. Check each GitHub release for its actual signing status.

The [macOS beta prerelease](https://github.com/harsh-91/statement-importer/releases/tag/v1.6.4-mac-beta.1) is ad hoc signed for local execution, without Apple Developer ID signing or notarization. Its Apple Silicon and Intel ZIPs include SHA-256 checksums. The in-app Updates control verifies and reveals the ZIP; replacing the app remains manual.

The primary release route is now Microsoft Store MSIX distribution. Microsoft signs an accepted MSIX package during Store publishing, so this repository never stores a private signing key.

The SignPath Foundation application was not approved at the project's current adoption level. It may be reconsidered later, but it is not a dependency of the Store route.

## Team roles

- Committer and reviewer: [Harsh (@harsh-91)](https://github.com/harsh-91)
- Signing approver: [Harsh (@harsh-91)](https://github.com/harsh-91)

## Release policy

- Signed artifacts must be built from this public repository.
- Product name, product version and publisher metadata must match the release.
- Every signed release must publish SHA-256 checksums.
- Authenticode signatures and timestamps must be verified before upload.
- Unsigned historical releases remain clearly identified as unsigned.
- MSIX installations use Microsoft Store updates and disable the legacy installer updater.
- Legacy installations verify the official GitHub asset digest and release SHA-256 before enabling the installer button. Signed installers must have a valid SignPath Foundation Authenticode signature; invalid or unexpected signatures are blocked. Unsigned beta installers are labeled and require an explicit click to open.
- Update installation is always initiated by the user; automatic checks never imply automatic download or installation.

## Privacy policy

Statement Importer will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it. Optional prerequisite downloads, REST API access and MCP access occur only when the user explicitly enables or requests them. Bank statements, statement passwords and imported transaction data remain on the user's computer.

Third-party runtime and build components retain their own licenses and privacy terms.
