<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Code signing policy

## Current status

Statement Importer releases must not be represented as signed until a trusted Authenticode signature has been applied and independently verified. Check each GitHub release for its actual signing status.

The project is preparing an application for **free code signing provided by SignPath.io, certificate by SignPath Foundation**. Signing can begin only after the open-source project is reviewed and approved by SignPath Foundation.

## Team roles

- Committer and reviewer: [Harsh (@harsh-91)](https://github.com/harsh-91)
- Signing approver: [Harsh (@harsh-91)](https://github.com/harsh-91)

## Release policy

- Signed artifacts must be built from this public repository.
- Product name, product version and publisher metadata must match the release.
- Every signed release must publish SHA-256 checksums.
- Authenticode signatures and timestamps must be verified before upload.
- Unsigned historical releases remain clearly identified as unsigned.
- The in-app updater must reject any installer that Windows does not validate as signed by SignPath Foundation.
- Update installation is always initiated by the user; automatic checks never imply automatic download or installation.

## Privacy policy

Statement Importer will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it. Optional prerequisite downloads, REST API access and MCP access occur only when the user explicitly enables or requests them. Bank statements, statement passwords and imported transaction data remain on the user's computer.

Third-party runtime and build components retain their own licenses and privacy terms.
