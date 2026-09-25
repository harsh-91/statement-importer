<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Security policy

Created by Harsh · Made in India 🇮🇳

## Supported version

Security fixes are currently applied to the latest `1.x` release.

## Reporting a vulnerability

Do not publish security vulnerabilities, credentials, bank statements, account numbers, or reproduction data in a public issue. Contact the repository owner privately through the GitHub profile at [@harsh-91](https://github.com/harsh-91) and provide a minimal reproduction containing synthetic data only.

## Data-handling promise

The application is offline-first, binds services to localhost, and does not include telemetry. Users remain responsible for PostgreSQL security, backups, operating-system access, and compliance obligations.

The built-in diagnostic utility creates its report locally and never uploads it automatically. Reports contain controlled system checks and redacted setup-stage events; they exclude statements, transaction records, database contents, credentials, protected configuration values and raw PostgreSQL logs. Users must review and explicitly attach and send a report.
