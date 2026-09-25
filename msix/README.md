<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Microsoft Store MSIX packaging

This directory builds the Store submission package. Microsoft signs the accepted package; do not place certificates, PFX files, tokens, or passwords in this repository.

## One-time Partner Center setup

1. Register an individual Microsoft Store developer account.
2. Reserve the app name **Neon Ledger**.
3. Copy the exact **Package/Identity/Name** and **Package/Identity/Publisher** values from Partner Center.
4. Add them as GitHub repository variables named `MSIX_IDENTITY_NAME` and `MSIX_PUBLISHER`.
5. Run the **Build Microsoft Store MSIX** workflow and submit its `.msix` artifact through Partner Center.

The defaults are development placeholders and will not be accepted as a production Store identity unless they exactly match Partner Center.

## What the package contains

- An x64, full-trust packaged desktop build of Neon Ledger.
- Verified PostgreSQL 17.11 Windows binaries from EDB, pinned by SHA-256.
- PostgreSQL data and application configuration remain outside the immutable package under the current user's profile, so Store updates preserve them.
- Microsoft Store owns installation, signing, repair, uninstall, and updates. The package does not run an installer, request administrator access, or install a Windows service.

## Local build

Install the Windows SDK and the locked Python build dependencies, then run:

```powershell
.\msix\build_msix.ps1 -IdentityName 'YOUR_PARTNER_CENTER_NAME' -Publisher 'YOUR_PARTNER_CENTER_PUBLISHER'
```

The build downloads the pinned PostgreSQL archive only when it is absent from `.cache`. Core application use remains offline.
