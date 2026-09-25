<!-- Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0 -->
# Contributing

Created by Harsh · Made in India 🇮🇳

Contributions are welcome through focused issues and pull requests. Never commit real bank statements, passwords, account numbers, `.env` files, database dumps, API keys, or screenshots containing financial data.

For database setup bugs, run **Diagnostics → Create privacy-safe report**, review the ZIP, and send it privately to the support address shown in the app. Do not attach diagnostic reports to public issues without checking them first.

Unless you explicitly state otherwise, contributions intentionally submitted for inclusion are licensed under the project's [Apache License 2.0](LICENSE.md), as described in section 5 of that license.

Before opening a pull request:

1. Use synthetic fixtures only.
2. Run `python -m unittest discover -s tests -v`.
3. Run `python -m compileall -q app.py desktop.py setup_launcher.py statement_importer scripts tests`.
4. Explain data-model or reconciliation changes and their failure behavior.
5. Preserve offline-first operation and localhost-only defaults.
