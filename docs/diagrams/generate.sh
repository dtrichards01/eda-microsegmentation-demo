#!/usr/bin/env python3
"""Regenerate docs/diagrams/*.png — run from repo root or this folder."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("generate_diagrams.py")), run_name="__main__")
