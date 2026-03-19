"""Seed the database with a base set of sector return data.

Run:
    python seed.py

This script is idempotent: re-running it will not create duplicate sector records.
"""

from app import create_app
from models import db, SectorReturn


SECTOR_DATA = [
    {
        "sector_name": "Food & Beverage",
        "annual_return_pct": 7.0,
        "example_stock": "Nestlé",
        "keywords": "food,beverage,groceries,eating",
    },
    {
        "sector_name": "Apparel/Clothing",
        "annual_return_pct": 8.0,
        "example_stock": "Nike",
        "keywords": "clothing,fashion,apparel,shoes",
    },
    {
        "sector_name": "Technology/Electronics",
        "annual_return_pct": 14.0,
        "example_stock": "Apple",
        "keywords": "technology,electronics,gadgets,software,devices",
    },
    {
        "sector_name": "Coffee/Café",
        "annual_return_pct": 9.0,
        "example_stock": "Starbucks",
        "keywords": "coffee,cafe,espresso,latte",
    },
    {
        "sector_name": "Streaming/Entertainment",
        "annual_return_pct": 11.0,
        "example_stock": "Netflix",
        "keywords": "streaming,entertainment,movies,tv,subscription",
    },
    {
        "sector_name": "Transport/Fuel",
        "annual_return_pct": 5.0,
        "example_stock": "Shell",
        "keywords": "transport,fuel,gas,petrol,travel",
    },
    {
        "sector_name": "Fitness/Gym",
        "annual_return_pct": 6.0,
        "example_stock": "Planet Fitness",
        "keywords": "fitness,gym,workout,health,exercise",
    },
    {
        "sector_name": "Gaming",
        "annual_return_pct": 12.0,
        "example_stock": "Activision",
        "keywords": "gaming,video games,esports,console",
    },
    {
        "sector_name": "Health/Pharmacy",
        "annual_return_pct": 8.0,
        "example_stock": "Pfizer",
        "keywords": "health,pharmacy,medicine,drugs,wellness",
    },
    {
        "sector_name": "General Retail",
        "annual_return_pct": 6.0,
        "example_stock": "Walmart",
        "keywords": "retail,shopping,store,supermarket",
    },
]


def seed():
    app = create_app()
    with app.app_context():
        for entry in SECTOR_DATA:
            sector = (
                SectorReturn.query.filter_by(sector_name=entry["sector_name"]).one_or_none()
            )
            if sector is None:
                sector = SectorReturn(**entry)
                db.session.add(sector)
            else:
                # Update existing record if data has changed
                sector.annual_return_pct = entry["annual_return_pct"]
                sector.example_stock = entry["example_stock"]
                sector.keywords = entry["keywords"]
        db.session.commit()

    print(f"Seeded {len(SECTOR_DATA)} sectors into sector_return table.")


if __name__ == "__main__":
    seed()
