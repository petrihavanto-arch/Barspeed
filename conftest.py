"""Ensures the project root is on sys.path so tests can import
`sensors` and `analysis` the same way main.py does -- both packages
assume the project root is importable, not just the tests/ directory.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
