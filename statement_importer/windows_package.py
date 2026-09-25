# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


APPMODEL_ERROR_NO_PACKAGE = 15700
ERROR_INSUFFICIENT_BUFFER = 122


def is_msix_package() -> bool:
    """Return True only when the current process has Windows package identity."""
    forced = os.environ.get("STATEMENT_IMPORTER_MSIX")
    if forced is not None:
        return forced.strip().lower() in {"1", "true", "yes"}
    if os.name != "nt" or not hasattr(ctypes, "windll"):
        return False
    length = wintypes.UINT(0)
    result = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
    return result in {ERROR_INSUFFICIENT_BUFFER, 0} and result != APPMODEL_ERROR_NO_PACKAGE
