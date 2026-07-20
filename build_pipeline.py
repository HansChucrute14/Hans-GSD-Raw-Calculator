#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pipeline.py — GSD Diet Calc V10.4 — thin CLI wrapper.

All real logic lives in the `gsd` package (src/gsd/). This file exists only
so `python build_pipeline.py <mode>` keeps working as documented; the
package's own console-script entry point (`gsd <mode>`, see pyproject.toml)
is equivalent.

Requires the package to be installed (editable is fine):
    pip install -e .

Modes: see `gsd.cli.main` / README.md.
"""

from gsd.cli import main

if __name__ == "__main__":
    main()
