from app.api.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names
from app.database import get_db
from app.models.message import Message
from sqlmodel import select

def find_unmatched_countries():
    session = next(get_db())
    countries = set()
    for msg in session.exec(select(Message)):
        if msg.country:
            norm_list = normalize_country_names(msg.country, COUNTRY_ALIASES)
            found = any(norm in COUNTRY_COORDS for norm in norm_list)
            if not found:
                countries.add(msg.country)
    print("Pays non reconnus par la normalisation :")
    for c in sorted(countries):
        print("-", c)

if __name__ == "__main__":
    find_unmatched_countries()
