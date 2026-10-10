import sys
from pathlib import Path

# Make `app` importable the same way Lambda sees it (backend/src on the path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
