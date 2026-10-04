#!/usr/bin/env python3
"""
v2_cli_test.py — Legacy Shim
============================
Deprecated: use laya_v2_cli.py instead.
Maintained as a thin backward-compatibility shim.
"""

import sys
import warnings
from laya_v2_cli import main

warnings.warn("v2_cli_test.py is deprecated; use laya_v2_cli.py instead.", DeprecationWarning, stacklevel=2)

if __name__ == "__main__":
    sys.exit(main())