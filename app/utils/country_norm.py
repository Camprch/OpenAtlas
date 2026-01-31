from app.api.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names
from typing import Optional

def compute_country_norm(raw_country: Optional[str]) -> Optional[str]:
    """
    Compute a canonical country key from a raw country field.
    Returns None if unknown or not geocoded.
    """
    if not raw_country:
        return None
    # Explicitly reject single-letter country strings (non-emoji noise)
    if isinstance(raw_country, str) and len(raw_country.strip()) == 1:
        return None
    # Normalize and pick the first known country with coordinates
    norm_list = normalize_country_names(raw_country, COUNTRY_ALIASES)
    for norm in norm_list:
        if norm in COUNTRY_COORDS:
            return norm
    return None
