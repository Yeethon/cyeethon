import sys

try:
    import layout
except ImportError:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from layout.main import main

sys.exit(int((main() or 0)))
