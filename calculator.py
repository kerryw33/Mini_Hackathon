"""
calculator.py — Regret Score Calculation Engine
Ticket 05: Computes all four Regret DNA gene scores + final Time Thief Score
"""

from api_clients import get_inflation_rate, get_exchange_rate

# ---------------------------------------------------------------------------
# Weight matrix — Habit Gravity
# Maps (category, sub_category) → habit weight (0.0–1.0)
# ---------------------------------------------------------------------------

WEIGHT_MATRIX = {
    "need": {
        "food":       0.20,
        "housing":    0.30,
        "healthcare": 0.25,
        "transport":  0.30,
        "education":  0.35,
    },
    "want": {
        "clothing":      0.50,
        "dining out":    0.55,
        "entertainment": 0.50,
        "technology":    0.60,
        "travel":        0.65,
    },
    "habit": {
        "coffee":           0.80,
        "subscriptions":    0.75,
        "alcohol & social": 0.85,
        "fitness":          0.70,
        "gaming":           0.90,
    },
}

# ---------------------------------------------------------------------------
# Sector mapping — sub_category → sector name used in SectorReturn table
# ---------------------------------------------------------------------------

SECTOR_MAP = {
    "food":             "Food & Beverage",
    "housing":          "Real Estate",
    "healthcare":       "Health & Pharmacy",
    "transport":        "Transport & Fuel",
    "education":        "Education",
    "clothing":         "Apparel",
    "dining out":       "Food & Beverage",
    "entertainment":    "Streaming & Entertainment",
    "technology":       "Technology & Electronics",
    "travel":           "Travel & Leisure",
    "coffee":           "Food & Beverage",
    "subscriptions":    "Streaming & Entertainment",
    "alcohol & social": "Food & Beverage",
    "fitness":          "Fitness & Health",
    "gaming":           "Gaming",
}

# Fallback sector returns (pct as decimal) if DB lookup fails
FALLBACK_SECTOR_RETURNS = {
    "Food & Beverage":            0.07,
    "Real Estate":                0.08,
    "Health & Pharmacy":          0.08,
    "Transport & Fuel":           0.05,
    "Education":                  0.06,
    "Apparel":                    0.08,
    "Streaming & Entertainment":  0.11,
    "Technology & Electronics":   0.14,
    "Travel & Leisure":           0.07,
    "Fitness & Health":           0.06,
    "Gaming":                     0.12,
}

DEFAULT_RETURN = 0.07   # 7% fallback if sector not found at all


# ---------------------------------------------------------------------------
# Helper: total ZAR spent over the period
# ---------------------------------------------------------------------------

def _calculate_total_spent_zar(
    amount: float,
    currency: str,
    frequency: str,
    years: float,
) -> tuple[float, float]:
    """
    Returns (total_spent_zar, exchange_rate_used).

    Converts amount to ZAR using the latest exchange rate, then
    multiplies by the number of transactions over `years`.
    """
    # Number of payments over the period
    payments_per_year = {
        "daily":    365,
        "weekly":   52,
        "monthly":  12,
        "once-off": 1,
    }
    n_payments = payments_per_year.get(frequency.lower(), 12) * years

    # Convert to ZAR
    rate = get_exchange_rate(currency, "ZAR")
    amount_in_zar = amount * rate

    total_zar = amount_in_zar * n_payments
    return round(total_zar, 2), rate


# ---------------------------------------------------------------------------
# Gene 1 — Habit Gravity Score (0–100)
# ---------------------------------------------------------------------------

def calculate_habit_gravity(category: str, sub_category: str) -> float:
    """
    Looks up the weight matrix and returns a score 0–100.
    A higher score = more unconscious/compulsive spending.
    """
    cat = category.lower().strip()
    sub = sub_category.lower().strip()

    weight = WEIGHT_MATRIX.get(cat, {}).get(sub, 0.20)
    score = weight * 100
    return round(score, 2)


# ---------------------------------------------------------------------------
# Gene 2 — Rand Betrayal Score (0–100)
# ---------------------------------------------------------------------------

def calculate_rand_betrayal(
    currency: str,
    amount: float,
    exchange_rate: float,
) -> tuple[float, str]:
    """
    Measures how much more you're paying in ZAR terms due to currency erosion.

    Score = ((effective_ZAR_cost / original_amount) - 1) × 100, capped at 100.
    If currency is ZAR, score = 0 (no erosion).

    Returns (score, explanation).
    """
    currency = currency.upper()

    if currency == "ZAR":
        return 0.0, "No currency erosion — spending in ZAR."

    effective_zar = amount * exchange_rate
    erosion_ratio = (effective_zar / amount) - 1   # how many extra ZAR per unit
    score = min(erosion_ratio * 100, 100)

    explanation = (
        f"1 {currency} = R{exchange_rate:.2f}. "
        f"Your R{amount:.0f} {currency} spend costs R{effective_zar:.2f} in real ZAR terms — "
        f"that's {erosion_ratio * 100:.1f}% more than face value."
    )
    return round(score, 2), explanation


# ---------------------------------------------------------------------------
# Gene 3 — Inflation Creep Score (0–100)
# ---------------------------------------------------------------------------

def calculate_inflation_creep(years: float) -> tuple[float, float, str]:
    """
    Uses the World Bank API to get SA's inflation rate.
    Score = inflation_rate × years × 100, capped at 100.

    Returns (score, inflation_rate, explanation).
    """
    inflation_rate = get_inflation_rate("ZAF")
    score = min(inflation_rate * years * 100, 100)

    explanation = (
        f"At SA's inflation rate of {inflation_rate * 100:.1f}%, "
        f"over {years:.0f} year(s) your purchasing power shrinks by "
        f"{inflation_rate * years * 100:.1f}%. "
        f"What costs R100 today will cost R{100 * (1 + inflation_rate) ** years:.0f} then."
    )
    return round(score, 2), inflation_rate, explanation


# ---------------------------------------------------------------------------
# Gene 4 — Opportunity Ghost Score (0–100)
# ---------------------------------------------------------------------------

def calculate_opportunity_ghost(
    total_spent_zar: float,
    sub_category: str,
    years: float,
    frequency: str,
    db_session=None,
) -> tuple[float, float, str]:
    """
    Calculates the compound investment value of the money spent.
    Score = ((opportunity_value / total_spent) - 1) × 100, capped at 100.

    Returns (score, opportunity_value_zar, explanation).

    If db_session is provided, attempts a SectorReturn DB lookup first.
    Falls back to FALLBACK_SECTOR_RETURNS dict.
    """
    sub = sub_category.lower().strip()
    sector = SECTOR_MAP.get(sub, "Food & Beverage")

    # Try DB lookup first
    annual_return = None
    if db_session is not None:
        try:
            from models import SectorReturn
            record = db_session.query(SectorReturn).filter_by(sector=sector).first()
            if record:
                annual_return = record.annual_return_pct / 100
        except Exception as e:
            print(f"[calculator] DB sector lookup failed: {e}")

    # Fall back to in-memory dict
    if annual_return is None:
        annual_return = FALLBACK_SECTOR_RETURNS.get(sector, DEFAULT_RETURN)

    # Compound growth: monthly contributions over `years`
    # FV = PMT × [((1 + r/n)^(n×t) − 1) / (r/n)]
    payments_per_year = {
        "daily":    365,
        "weekly":   52,
        "monthly":  12,
        "once-off": 1,
    }
    n = payments_per_year.get(frequency.lower(), 12)   # compounding periods/year
    r = annual_return
    t = years

    if frequency.lower() == "once-off":
        # Lump-sum compound growth
        opportunity_value = total_spent_zar * (1 + r) ** t
    else:
        pmt = total_spent_zar / (n * t)    # payment per period
        opportunity_value = pmt * (((1 + r / n) ** (n * t) - 1) / (r / n))

    ghost_money = opportunity_value - total_spent_zar
    score = min(((opportunity_value / total_spent_zar) - 1) * 100, 100)

    explanation = (
        f"Invested in the {sector} sector (avg {annual_return * 100:.0f}%/yr), "
        f"R{total_spent_zar:,.0f} could have grown to R{opportunity_value:,.0f} "
        f"over {years:.0f} year(s). "
        f"That's R{ghost_money:,.0f} in ghost money you never earned."
    )
    return round(score, 2), round(opportunity_value, 2), explanation


# ---------------------------------------------------------------------------
# Master function — calculate_regret()
# ---------------------------------------------------------------------------

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
    rand_betrayal_score, rand_explanation = calculate_rand_betrayal(
        currency, amount, exchange_rate
    )

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
