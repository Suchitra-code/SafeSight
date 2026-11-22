"""
Vercel Serverless Function Entrypoint for SafeSight AI.
"""
import os
import sys

# Ensure root directory is on Python module search path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from run import app
