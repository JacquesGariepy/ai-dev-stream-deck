"""Copy legacy data to the space-free AIDev directory; retain the old backup."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aidev.migration import migrate_legacy

if __name__ == '__main__':
    print(json.dumps(migrate_legacy(),indent=2))
