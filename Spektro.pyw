import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import spektro

sys.exit(spektro.pyw_main())
