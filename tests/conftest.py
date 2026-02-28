import os
import sys
from pathlib import Path

# Get the project root directory (two levels up from tests/)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Add project root to sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
