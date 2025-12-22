from app.api.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names
from typing import Optional

def compute_country_norm(raw_country: Optional[str]) -> Optional[str]:
    """
    Calcule la clé canonique d'un pays à partir du champ brut.
    Retourne None si inconnu ou non géoréférencé.
    """
    if not raw_country:
        return None
    # Refuse explicitement les pays d'une seule lettre (hors emoji)
    if isinstance(raw_country, str) and len(raw_country.strip()) == 1:
        return None
    norm_list = normalize_country_names(raw_country, COUNTRY_ALIASES)
    for norm in norm_list:
        if norm in COUNTRY_COORDS:
            return norm
    return None
