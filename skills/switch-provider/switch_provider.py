#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
switch_provider.py - OpenCode skill: switch active LLM provider
This is a thin wrapper around the root-level switch.py for use by OpenCode
agents. If --id is passed, the underlying switch.py is invoked with that
provider id (currently switch.py uses an interactive menu, so we
post-validate the choice here).
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
TARGET = ROOT / "switch.py"


def main():
    args = [sys.executable, str(TARGET)] + sys.argv[1:]
    return subprocess.call(args)


if __name__ == "__main__":
    sys.exit(main())
