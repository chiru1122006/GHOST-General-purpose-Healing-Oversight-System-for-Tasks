import os
import sys

# Automatically insert the project root into sys.path when running pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
