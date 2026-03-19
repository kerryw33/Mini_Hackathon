"""API clients for external data used by the Regret Simulator.

This module provides a small abstraction over the World Bank and Frankfurter APIs.
All functions are defensive and fall back to sensible defaults when the network is
unavailable.
"""

import logging

import requests


WORLD_BANK_URL = (
    "https://api.worldbank.org/v2/country/{country_code}"
    "/indicator/FP.CPI.TOTL.ZG?format=json&mrv=1"
)

FRANKFURTER_LATEST_URL = "https://api.frankfurter.app/latest"
FRANKFURTER_HISTORICAL_URL = "https://api.frankfurter.app/{date}"

# Fallback values used when APIs are unreachable
FALLBACK_INFLATION_RATE = 0.056  # 5.6% — SA average
FALLBACK_ZAR_RATE = {  # ZAR per 1 unit of foreign currency
    "USD": 18.50,
    "GBP": 23.50,
    "EUR": 20.00,
    "AUD": 12.00,
    "ZAR": 1.00,
}


def get_inflation_rate(country_code: str = "ZAF") -> float:
    """Return the most recent annual inflation rate as a decimal.

    Falls back to FALLBACK_INFLATION_RATE if the API is unavailable.
    """

    try:
        url = WORLD_BANK_URL.format(country_code=country_code)
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list) and len(data) >= 2 and data[1]:
            latest = data[1][0]
            value = latest.get("value")
            if value is not None:
                value = float(value)
                if abs(value) > 1:
                    value = value / 100.0
                return value

        logging.warning("World Bank returned no valid entries — using fallback")
    except Exception as e:
        logging.warning("Failed to fetch inflation rate: %s", e)

    return FALLBACK_INFLATION_RATE


def get_exchange_rate(from_currency: str, to_currency: str = "ZAR") -> float:
    """Return the exchange rate from `from_currency` to `to_currency`.

    Falls back to a sensible default if the API is unreachable.
    """

    from_currency = (from_currency or "").upper().strip()
    to_currency = (to_currency or "").upper().strip()

    if from_currency == to_currency:
        return 1.0

    try:
        resp = requests.get(
            FRANKFURTER_LATEST_URL,
            params={"from": from_currency, "to": to_currency},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates") or {}
        rate = rates.get(to_currency)
        if rate is not None:
            return float(rate)

    except Exception as e:
        logging.warning("Failed to fetch exchange rate %s->%s: %s", from_currency, to_currency, e)

    if to_currency == "ZAR":
        return FALLBACK_ZAR_RATE.get(from_currency, 1.0)
    return 1.0


def get_historical_exchange_rate(
    from_currency: str,
    to_currency: str = "ZAR",
    date: str = "2020-01-01",
) -> float:
    """Fetch the exchange rate on a specific historical date.

    Falls back to the latest rate if the historical call fails.
    """

    from_currency = (from_currency or "").upper().strip()
    to_currency = (to_currency or "").upper().strip()

    if from_currency == to_currency:
        return 1.0

    try:
        url = FRANKFURTER_HISTORICAL_URL.format(date=date)
        resp = requests.get(
            url,
            params={"from": from_currency, "to": to_currency},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates") or {}
        rate = rates.get(to_currency)
        if rate is not None:
            return float(rate)

    except Exception as e:
        logging.warning(
            "Failed to fetch historical exchange rate %s->%s on %s: %s",
            from_currency,
            to_currency,
            date,
            e,
        )

    return get_exchange_rate(from_currency, to_currency)


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
