"""Core calculation engine for the Regret Simulator.

Exports:
- calculate_regret(entry_data: dict) -> dict
- get_severity(score: float) -> str
"""

from datetime import date, timedelta
from typing import Dict, Optional, Tuple

from api_clients import get_inflation_rate, get_exchange_rate, get_historical_exchange_rate


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

# Default annual return % by sector name (used when DB is unavailable)
DEFAULT_SECTOR_RETURNS = {
    "Food & Beverage": 8.0,
    "General Retail": 7.0,
    "Health/Pharmacy": 9.0,
    "Transport/Fuel": 6.0,
    "Apparel/Clothing": 7.5,
    "Streaming/Entertainment": 12.0,
    "Technology/Electronics": 14.0,
    "Coffee/Café": 8.0,
    "Fitness/Gym": 7.0,
    "Gaming": 13.0,
}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _weight_for(category: str, sub_category: str) -> float:
    return WEIGHT_MATRIX.get(category, {}).get(sub_category, 0.3)


def _normalize_frequency(amount: float, frequency: str, years: float) -> float:
    frequency = (frequency or "").lower().strip()
    if frequency == "once-off":
        return amount

    multipliers = {"daily": 365, "weekly": 52, "monthly": 12}
    multiplier = multipliers.get(frequency, 1)
    return amount * multiplier * max(years, 0)


# ---------------------------------------------------------------------------
# Gene helper functions
# ---------------------------------------------------------------------------

def _calculate_total_spent_zar(
    amount: float, currency: str, frequency: str, years: float
) -> Tuple[float, float]:
    """Convert amount to ZAR and normalise by frequency/years.

    Returns (total_spent_zar, exchange_rate).
    """
    exchange_rate = get_exchange_rate(currency, "ZAR")
    total = _normalize_frequency(amount * exchange_rate, frequency, years)
    return total, exchange_rate


def calculate_habit_gravity(category: str, sub_category: str) -> float:
    """Score 0-100: how habitual/compulsive is this spending pattern."""
    weight = _weight_for(category, sub_category)
    return min(100.0, max(0.0, weight * 100.0))


def calculate_rand_betrayal(currency: str, years: float) -> Tuple[float, str]:
    """Score 0-100: ZAR depreciation against the foreign currency over the period.

    For ZAR spending the score is always 0.
    Returns (score, explanation).
    """
    currency = (currency or "ZAR").upper()

    if currency == "ZAR":
        return 0.0, "Your spending is in ZAR — no currency exchange risk applies."

    current_rate = get_exchange_rate(currency, "ZAR")
    historical_date = (date.today() - timedelta(days=int(max(years, 1) * 365))).isoformat()
    historical_rate = get_historical_exchange_rate(currency, "ZAR", historical_date)

    if historical_rate and historical_rate > 0:
        depreciation = (current_rate - historical_rate) / historical_rate
        score = min(100.0, max(0.0, depreciation * 100.0))
    else:
        score = 0.0

    explanation = (
        f"ZAR moved from {historical_rate:.2f} to {current_rate:.2f} vs {currency} "
        f"over {years:.1f} year(s) — your foreign-currency purchasing power shifted accordingly."
    )
    return score, explanation


def calculate_inflation_creep(years: float) -> Tuple[float, float, str]:
    """Score 0-100: cumulative purchasing-power erosion from SA inflation.

    Returns (score, inflation_rate, explanation).
    """
    inflation_rate = get_inflation_rate("ZAF")
    cumulative = (1 + inflation_rate) ** years - 1
    score = min(100.0, max(0.0, cumulative * 100.0))
    explanation = (
        f"At {inflation_rate * 100:.1f}% inflation, your money loses purchasing power "
        f"over {years:.1f} year(s) — cumulative erosion: {cumulative * 100:.1f}%."
    )
    return score, inflation_rate, explanation


def calculate_opportunity_ghost(
    total_spent_zar: float,
    sub_category: str,
    years: float,
    frequency: str,
    db_session=None,
) -> Tuple[float, float, str]:
    """Score 0-100: investment opportunity cost of the spending.

    Returns (score, ghost_value, explanation).
    ghost_value is how much extra money you'd have had vs just spending it.
    """
    sector_name = SUBCATEGORY_TO_SECTOR.get(sub_category, "General Retail")
    annual_return_pct = DEFAULT_SECTOR_RETURNS.get(sector_name, 7.0)

    if db_session is not None:
        try:
            from models import SectorReturn
            sector = db_session.query(SectorReturn).filter_by(sector_name=sector_name).one_or_none()
            if sector:
                annual_return_pct = sector.annual_return_pct
        except Exception:
            pass  # fall through to default

    annual_return = annual_return_pct / 100.0

    if total_spent_zar <= 0 or years <= 0:
        opportunity_value = max(0.0, total_spent_zar)
    else:
        opportunity_value = total_spent_zar * ((1 + annual_return) ** years)

    ghost_value = max(0.0, opportunity_value - total_spent_zar)

    if total_spent_zar > 0:
        score = min(100.0, max(0.0, (opportunity_value / total_spent_zar - 1.0) * 100.0))
    else:
        score = 0.0

    explanation = (
        f"If you had invested your total spend in {sector_name} "
        f"(≈{annual_return_pct:.1f}% p.a.), it could have grown to "
        f"R{opportunity_value:,.2f} in {years:.1f} year(s)."
    )
    return score, ghost_value, explanation


# ---------------------------------------------------------------------------
# Severity badge helper (used by templates)
# ---------------------------------------------------------------------------

def get_severity(score: float) -> str:
    """Returns a severity label for a gene score."""
    if score >= 75:
        return "SEVERE"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Master calculation function
# ---------------------------------------------------------------------------

def calculate_regret(entry_data: dict, db_session=None) -> dict:
    """Calculate all regret gene scores and supporting values.

    entry_data keys:
        amount           float  — e.g. 30.0
        currency         str    — e.g. "ZAR", "USD"
        frequency        str    — "daily" | "weekly" | "monthly" | "once-off"
        category         str    — "need" | "want" | "habit"
        sub_category     str    — e.g. "coffee", "food", "subscriptions"
        sub_sub_category str    — optional, e.g. "cappuccino" (not used in scoring)
        years            float  — e.g. 1.0

    Returns a dict with all scores, explanations, and severity badges.
    """
    amount = float(entry_data.get("amount", 0) or 0)
    currency = (entry_data.get("currency") or "ZAR").upper().strip()
    frequency = (entry_data.get("frequency") or "once-off").lower().strip()
    category = (entry_data.get("category") or "need").lower().strip()
    sub_category = (entry_data.get("sub_category") or "").lower().strip()
    years = float(entry_data.get("years", 1) or 1)

    # --- Total ZAR spent ---
    total_spent_zar, exchange_rate = _calculate_total_spent_zar(
        amount, currency, frequency, years
    )

    # --- Gene 1: Habit Gravity ---
    habit_gravity_score = calculate_habit_gravity(category, sub_category)

    # --- Gene 2: Rand Betrayal ---
    rand_betrayal_score, rand_explanation = calculate_rand_betrayal(currency, years)

    # --- Gene 3: Inflation Creep ---
    inflation_creep_score, inflation_rate, inflation_explanation = calculate_inflation_creep(years)

    # --- Gene 4: Opportunity Ghost ---
    opportunity_ghost_score, opportunity_ghost_value, opportunity_explanation = (
        calculate_opportunity_ghost(total_spent_zar, sub_category, years, frequency, db_session)
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
        "total_spent_zar": total_spent_zar,
        "exchange_rate_used": exchange_rate,
        "inflation_rate": inflation_rate,

        # Individual gene scores (0–100)
        "habit_gravity_score": habit_gravity_score,
        "rand_betrayal_score": rand_betrayal_score,
        "inflation_creep_score": inflation_creep_score,
        "opportunity_ghost_score": opportunity_ghost_score,

        # Final score
        "time_thief_score": time_thief_score,

        # Rich output
        "opportunity_ghost_value": opportunity_ghost_value,
        "inflation_explanation": inflation_explanation,
        "opportunity_explanation": opportunity_explanation,
        "rand_explanation": rand_explanation,

        # Severity badges for template
        "severity": {
            "habit_gravity": get_severity(habit_gravity_score),
            "rand_betrayal": get_severity(rand_betrayal_score),
            "inflation_creep": get_severity(inflation_creep_score),
            "opportunity_ghost": get_severity(opportunity_ghost_score),
        },
    }


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
        print(f"  TIME THIEF SCORE:      {result['time_thief_score']:.1f}/100")
        print(f"  Ghost Money:           R{result['opportunity_ghost_value']:,.2f}")
        print(f"  Severity:              {get_severity(result['time_thief_score'])}")
        print()
