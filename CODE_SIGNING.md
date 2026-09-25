<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Code signing policy

## Current status

Statement Importer releases must not be represented as signed until a trusted Authenticode signature has been applied and independently verified. Check each GitHub release for its actual signing status.

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
- Legacy installations retain strict SHA-256 and Authenticode checks; they are not represented as Store-signed.
- Update installation is always initiated by the user; automatic checks never imply automatic download or installation.

## Privacy policy

Statement Importer will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it. Optional prerequisite downloads, REST API access and MCP access occur only when the user explicitly enables or requests them. Bank statements, statement passwords and imported transaction data remain on the user's computer.

Third-party runtime and build components retain their own licenses and privacy terms.
