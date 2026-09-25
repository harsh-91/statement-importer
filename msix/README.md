<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Microsoft Store MSIX packaging

This directory builds the Store submission package. Microsoft signs the accepted package; do not place certificates, PFX files, tokens, or passwords in this repository.

## One-time Partner Center setup

1. Individual Microsoft Store developer account: created and verified.
2. App name **Neon Ledger**: reserved as a draft MSIX app.
3. Run the **Build Microsoft Store MSIX** workflow and submit its `.msix` artifact through Partner Center.

The build defaults now match the Store's exact identity values:

| Partner Center field | Value |
| --- | --- |
| Package/Identity/Name | `HarshNair.NeonLedger` |
| Package/Identity/Publisher | `CN=2AD2CE84-2334-4A3E-AFF4-2D43D2936CB8` |
| Package/Properties/PublisherDisplayName | `Harsh Nair` |
| Store ID | `9NDGSCG87PVT` |

If Partner Center ever changes these values, use the `MSIX_IDENTITY_NAME` and `MSIX_PUBLISHER` GitHub repository variables to override the build defaults.

## What the package contains

- An x64, full-trust packaged desktop build of Neon Ledger.
- Verified PostgreSQL 17.11 Windows binaries from EDB, pinned by SHA-256.
- PostgreSQL data and application configuration remain outside the immutable package under the current user's profile, so Store updates preserve them.
- Microsoft Store owns installation, signing, repair, uninstall, and updates. The package does not run an installer, request administrator access, or install a Windows service.

## Local build

Install the Windows SDK and the locked Python build dependencies, then run:

```powershell
.\msix\build_msix.ps1
```

The build downloads the pinned PostgreSQL archive only when it is absent from `.cache`. Core application use remains offline.
