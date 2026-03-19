"""Core calculation engine for the Regret Simulator.

Exports:
- calculate_regret(entry_data: dict) -> dict
"""

from typing import Dict

from api_clients import get_exchange_rate, get_inflation_rate
from models import SectorReturn


# A basic weight matrix for habit gravity. Values are 0..1 and will be scaled to 0..100.
WEIGHT_MATRIX = {
    "need": {
        "food": 0.35,
        "housing": 0.25,
        "healthcare": 0.3,
        "transport": 0.25,
        "education": 0.2,
    },
    "want": {
        "clothing": 0.6,
        "dining out": 0.7,
        "entertainment": 0.7,
        "technology": 0.6,
        "travel": 0.8,
    },
    "habit": {
        "coffee": 0.75,
        "subscriptions": 0.55,
        "alcohol & social": 0.8,
        "fitness": 0.25,
        "gaming": 0.6,
    },
}

# Map sub_category to the SectorReturn sector name.
SUBCATEGORY_TO_SECTOR = {
    "food": "Food & Beverage",
    "housing": "General Retail",
    "healthcare": "Health/Pharmacy",
    "transport": "Transport/Fuel",
    "education": "General Retail",
    "clothing": "Apparel/Clothing",
    "dining out": "Food & Beverage",
    "entertainment": "Streaming/Entertainment",
    "technology": "Technology/Electronics",
    "travel": "General Retail",
    "coffee": "Coffee/Café",
    "subscriptions": "Streaming/Entertainment",
    "alcohol & social": "Food & Beverage",
    "fitness": "Fitness/Gym",
    "gaming": "Gaming",
}


def _weight_for(category: str, sub_category: str) -> float:
    return WEIGHT_MATRIX.get(category, {}).get(sub_category, 0.3)


def _normalize_frequency(amount: float, frequency: str, years: float) -> float:
    frequency = (frequency or "").lower().strip()
    if frequency == "once-off":
        return amount

    multipliers = {"daily": 365, "weekly": 52, "monthly": 12}
    multiplier = multipliers.get(frequency, 1)
    return amount * multiplier * max(years, 0)


def _severity_label(score: float) -> str:
    if score >= 75:
        return "SEVERE"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def calculate_regret(entry_data: Dict) -> Dict:
    """Calculate all regret gene scores and supporting values.

    Returns a dict with the same structure described in the tickets.
    """

    amount = float(entry_data.get("amount", 0) or 0)
    currency = (entry_data.get("currency") or "ZAR").upper().strip()
    frequency = (entry_data.get("frequency") or "once-off").lower().strip()
    category = (entry_data.get("category") or "need").lower().strip()
    sub_category = (entry_data.get("sub_category") or "").lower().strip()
    years = float(entry_data.get("years", 1) or 1)

    # Total spent in ZAR (converts currency if needed, and accounts for frequency/year)
    exchange_rate = get_exchange_rate(currency, "ZAR")
    total_spent_zar = _normalize_frequency(amount * exchange_rate, frequency, years)

    # Habit gravity
    habit_weight = _weight_for(category, sub_category)
    habit_gravity_score = min(100.0, max(0.0, habit_weight * 100.0))

    # Rand betrayal
    rand_betrayal_score = 0.0
    if currency != "ZAR" and amount > 0:
        # (effective_ZAR / original_amount) - 1
        try:
            rand_betrayal_score = (exchange_rate - 1.0) * 100.0
        except Exception:
            rand_betrayal_score = 0.0
        rand_betrayal_score = min(100.0, max(0.0, rand_betrayal_score))

    # Inflation creep
    inflation_rate = get_inflation_rate("ZAF")
    inflation_creep_score = min(100.0, max(0.0, inflation_rate * years * 100.0))

    # Opportunity ghost
    sector_name = SUBCATEGORY_TO_SECTOR.get(sub_category, "General Retail")
    sector = SectorReturn.query.filter_by(sector_name=sector_name).one_or_none()
    annual_return_pct = sector.annual_return_pct if sector else 7.0
    annual_return = annual_return_pct / 100.0

    if total_spent_zar <= 0 or years <= 0:
        opportunity_value = total_spent_zar
    else:
        opportunity_value = total_spent_zar * ((1 + annual_return) ** years)

    opportunity_ghost_score = 0.0
    if total_spent_zar > 0:
        opportunity_ghost_score = (opportunity_value / total_spent_zar - 1.0) * 100.0
        opportunity_ghost_score = min(100.0, max(0.0, opportunity_ghost_score))

    opportunity_ghost_value = max(0.0, opportunity_value - total_spent_zar)

    inflation_explanation = (
        f"At {inflation_rate*100:.1f}% inflation, your money loses purchasing power over {years:.1f} year(s)."
    )

    opportunity_explanation = (
        f"If you had invested your total spend in {sector_name} (≈{annual_return_pct:.1f}% p.a.), it could have grown to {opportunity_value:,.2f} ZAR in {years:.1f} year(s)."
    )

    time_thief_score = (
        habit_gravity_score + rand_betrayal_score + inflation_creep_score + opportunity_ghost_score
    ) / 4.0

    return {
        "total_spent_zar": total_spent_zar,
        "habit_gravity_score": habit_gravity_score,
        "rand_betrayal_score": rand_betrayal_score,
        "inflation_creep_score": inflation_creep_score,
        "opportunity_ghost_score": opportunity_ghost_score,
        "time_thief_score": time_thief_score,
        "opportunity_ghost_value": opportunity_ghost_value,
        "inflation_explanation": inflation_explanation,
        "opportunity_explanation": opportunity_explanation,
        "severity": {
            "habit_gravity": _severity_label(habit_gravity_score),
            "rand_betrayal": _severity_label(rand_betrayal_score),
            "inflation_creep": _severity_label(inflation_creep_score),
            "opportunity_ghost": _severity_label(opportunity_ghost_score),
        },
    }

def calculate_regret(entry_data: dict, db_session=None) -> dict:
    """
    Master calculation function. Accepts an entry_data dict and returns
    a full results dict with all four gene scores and the final Time Thief Score.

    entry_data keys:
        amount          float   — e.g. 30.0
        currency        str     — e.g. "ZAR", "USD"
        frequency       str     — "daily" | "weekly" | "monthly" | "once-off"
        category        str     — "need" | "want" | "habit"
        sub_category    str     — e.g. "coffee", "food", "subscriptions"
        sub_sub_category str    — optional, e.g. "cappuccino" (not used in scoring)
        years           float   — e.g. 1.0
    """
    amount       = float(entry_data["amount"])
    currency     = entry_data["currency"].upper()
    frequency    = entry_data["frequency"].lower()
    category     = entry_data["category"].lower()
    sub_category = entry_data["sub_category"].lower()
    years        = float(entry_data["years"])

    # --- Total ZAR spent ---
    total_spent_zar, exchange_rate = _calculate_total_spent_zar(
        amount, currency, frequency, years
    )

    # --- Gene 1: Habit Gravity ---
    habit_gravity_score = calculate_habit_gravity(category, sub_category)

    # --- Gene 2: Rand Betrayal ---
    # Remove exchange_rate from the rand betrayal call
    rand_betrayal_score, rand_explanation = calculate_rand_betrayal(currency, years)
    # --- Gene 3: Inflation Creep ---
    inflation_creep_score, inflation_rate, inflation_explanation = calculate_inflation_creep(years)

    # --- Gene 4: Opportunity Ghost ---
    opportunity_ghost_score, opportunity_value, opportunity_explanation = calculate_opportunity_ghost(
        total_spent_zar, sub_category, years, frequency, db_session
    )

    # --- Final Time Thief Score (equal-weighted average) ---
    time_thief_score = round(
        0.25 * habit_gravity_score
        + 0.25 * rand_betrayal_score
        + 0.25 * inflation_creep_score
        + 0.25 * opportunity_ghost_score,
        2,
    )

    return {
        # Core financials
        "total_spent_zar":        total_spent_zar,
        "exchange_rate_used":     exchange_rate,
        "inflation_rate":         inflation_rate,

        # Individual gene scores (0–100)
        "habit_gravity_score":    habit_gravity_score,
        "rand_betrayal_score":    rand_betrayal_score,
        "inflation_creep_score":  inflation_creep_score,
        "opportunity_ghost_score": opportunity_ghost_score,

        # Final score
        "time_thief_score":       time_thief_score,

        # Rich output
        "opportunity_ghost_value": opportunity_value,
        "inflation_explanation":   inflation_explanation,
        "opportunity_explanation": opportunity_explanation,
        "rand_explanation":        rand_explanation,
    }


# ---------------------------------------------------------------------------
# Severity badge helper (used by templates)
# ---------------------------------------------------------------------------

def get_severity(score: float) -> str:
    """Returns a severity label for a gene score."""
    if score < 25:
        return "LOW"
    elif score < 50:
        return "MEDIUM"
    elif score < 75:
        return "HIGH"
    else:
        return "SEVERE"


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Smoke Test: calculator.py ===\n")

    test_cases = [
        {
            "label": "Daily R30 coffee (ZAR, habit)",
            "entry": {
                "amount": 30, "currency": "ZAR", "frequency": "daily",
                "category": "habit", "sub_category": "coffee",
                "sub_sub_category": "cappuccino", "years": 1,
            },
        },
        {
            "label": "Monthly $15 Netflix (USD, habit)",
            "entry": {
                "amount": 15, "currency": "USD", "frequency": "monthly",
                "category": "habit", "sub_category": "subscriptions",
                "sub_sub_category": "netflix", "years": 1,
            },
        },
        {
            "label": "Daily R50 fruit (ZAR, need)",
            "entry": {
                "amount": 50, "currency": "ZAR", "frequency": "daily",
                "category": "need", "sub_category": "food",
                "sub_sub_category": "fruit", "years": 1,
            },
        },
    ]

    for tc in test_cases:
        print(f"--- {tc['label']} ---")
        result = calculate_regret(tc["entry"])
        print(f"  Total Spent (ZAR):     R{result['total_spent_zar']:,.2f}")
        print(f"  Habit Gravity:         {result['habit_gravity_score']:.1f}/100")
        print(f"  Rand Betrayal:         {result['rand_betrayal_score']:.1f}/100")
        print(f"  Inflation Creep:       {result['inflation_creep_score']:.1f}/100")
        print(f"  Opportunity Ghost:     {result['opportunity_ghost_score']:.1f}/100")
        print(f"  ⏰ TIME THIEF SCORE:   {result['time_thief_score']:.1f}/100")
        print(f"  💸 Ghost Money:        R{result['opportunity_ghost_value']:,.2f}")
        print(f"  Severity:              {get_severity(result['time_thief_score'])}")
        print()
