"""
The proof workbook is checked against the engine, sheet by sheet and row by
row, so the examples a person reads can never drift from what the tool does.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.chdir(ROOT)

import make_proof_workbook as proof

ok = proof.verify()
sys.exit(0 if ok else 1)
