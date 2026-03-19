"""
api_clients.py — External API integrations
Ticket 04: World Bank (inflation) + Frankfurter (exchange rates)
"""

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORLD_BANK_URL = (
    "https://api.worldbank.org/v2/country/{country_code}"
    "/indicator/FP.CPI.TOTL.ZG?format=json&mrv=1"
)

FRANKFURTER_LATEST_URL = "https://api.frankfurter.app/latest"
FRANKFURTER_HISTORICAL_URL = "https://api.frankfurter.app/{date}"

# Fallback values used when APIs are unreachable
FALLBACK_INFLATION_RATE = 0.056          # 5.6% — SA average
FALLBACK_ZAR_RATE = {                    # ZAR per 1 unit of foreign currency
    "USD": 18.50,
    "GBP": 23.50,
    "EUR": 20.00,
    "AUD": 12.00,
    "ZAR": 1.00,
}


# ---------------------------------------------------------------------------
# World Bank — Inflation Rate
# ---------------------------------------------------------------------------

def get_inflation_rate(country_code: str = "ZAF") -> float:
    """
    Fetch the most recent annual inflation rate for the given country.

    Returns a decimal (e.g. 0.056 for 5.6%).
    Falls back to FALLBACK_INFLATION_RATE if the API is unavailable.
    """
    try:
        url = WORLD_BANK_URL.format(country_code=country_code)
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        # World Bank response: [metadata_dict, [entry, entry, ...]]
        entries = data[1]
        if not entries:
            print("[api_clients] World Bank returned no entries — using fallback")
            return FALLBACK_INFLATION_RATE

        # Find the first entry with a non-null value
        for entry in entries:
            value = entry.get("value")
            if value is not None:
                rate = round(value / 100, 6)   # convert 5.6 → 0.056
                print(f"[api_clients] Inflation rate ({country_code}): {rate}")
                return rate

        print("[api_clients] All World Bank entries are null — using fallback")
        return FALLBACK_INFLATION_RATE

    except Exception as e:
        print(f"[api_clients] World Bank API error: {e} — using fallback")
        return FALLBACK_INFLATION_RATE


# ---------------------------------------------------------------------------
# Frankfurter — Exchange Rates
# ---------------------------------------------------------------------------

def get_exchange_rate(from_currency: str, to_currency: str = "ZAR") -> float:
    """
    Fetch the latest exchange rate from from_currency to to_currency.

    Returns the rate as a float (e.g. 18.5 means 1 USD = 18.5 ZAR).
    Falls back to FALLBACK_ZAR_RATE if the API is unavailable.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    # Same currency — no conversion needed
    if from_currency == to_currency:
        return 1.0

    try:
        response = requests.get(
            FRANKFURTER_LATEST_URL,
            params={"from": from_currency, "to": to_currency},
            timeout=5,
        )
        response.raise_for_status()

        data = response.json()
        rate = data["rates"][to_currency]
        print(f"[api_clients] Exchange rate {from_currency}→{to_currency}: {rate}")
        return float(rate)

    except Exception as e:
        print(f"[api_clients] Frankfurter API error: {e} — using fallback")
        # Try to return a sensible fallback
        if to_currency == "ZAR":
            return FALLBACK_ZAR_RATE.get(from_currency, 1.0)
        return 1.0


def get_historical_exchange_rate(
    from_currency: str,
    to_currency: str = "ZAR",
    date: str = "2020-01-01",
) -> float:
    """
    Fetch the exchange rate on a specific historical date.

    date format: "YYYY-MM-DD"
    Falls back to get_exchange_rate() (latest) if the historical call fails.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0

    try:
        url = FRANKFURTER_HISTORICAL_URL.format(date=date)
        response = requests.get(
            url,
            params={"from": from_currency, "to": to_currency},
            timeout=5,
        )
        response.raise_for_status()

        data = response.json()
        rate = data["rates"][to_currency]
        print(f"[api_clients] Historical rate {from_currency}→{to_currency} on {date}: {rate}")
        return float(rate)

    except Exception as e:
        print(f"[api_clients] Frankfurter historical API error: {e} — falling back to latest rate")
        return get_exchange_rate(from_currency, to_currency)


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Smoke Test: api_clients.py ===\n")

    inflation = get_inflation_rate("ZAF")
    print(f"SA Inflation Rate : {inflation:.4f} ({inflation * 100:.2f}%)\n")

    usd_to_zar = get_exchange_rate("USD", "ZAR")
    print(f"USD → ZAR (latest): {usd_to_zar}\n")

    gbp_to_zar = get_exchange_rate("GBP", "ZAR")
    print(f"GBP → ZAR (latest): {gbp_to_zar}\n")

    hist = get_historical_exchange_rate("USD", "ZAR", "2020-01-01")
    print(f"USD → ZAR on 2020-01-01: {hist}\n")

    same = get_exchange_rate("ZAR", "ZAR")
    print(f"ZAR → ZAR (should be 1.0): {same}\n")
