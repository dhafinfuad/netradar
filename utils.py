import re
from typing import Optional

def normalize_mac(mac: Optional[str]) -> Optional[str]:
    """
    Normalizes a MAC address string:
    - Trims whitespace
    - Replaces hyphens with colons
    - Converts to UPPERCASE (e.g. '00:1a:6b:53:ba:70' -> '00:1A:6B:53:BA:70')
    """
    if not mac:
        return None
    cleaned = mac.strip().replace('-', ':').upper()
    return cleaned if cleaned else None
