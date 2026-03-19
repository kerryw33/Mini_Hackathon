"""Automated tests for the Regret Simulator.

Run with:  python -m pytest test.py -v
"""

import pytest
from unittest.mock import patch

from calculator import (
    calculate_regret,
    calculate_habit_gravity,
    calculate_rand_betrayal,
    calculate_inflation_creep,
    calculate_opportunity_ghost,
    get_severity,
    _normalize_frequency,
    _calculate_total_spent_zar,
    WEIGHT_MATRIX,
    SUBCATEGORY_TO_SECTOR,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

MOCK_INFLATION = 0.056   # 5.6%
MOCK_ZAR_RATE  = 18.50   # USD → ZAR


def mock_get_exchange_rate(from_cur, to_cur="ZAR"):
    if from_cur == to_cur:
        return 1.0
    if from_cur == "USD" and to_cur == "ZAR":
        return MOCK_ZAR_RATE
    return 1.0


def mock_get_historical_exchange_rate(from_cur, to_cur="ZAR", date="2020-01-01"):
    # Simulate ZAR weaker historically (15.0 → 18.5 = ~23% depreciation)
    if from_cur == "USD" and to_cur == "ZAR":
        return 15.0
    return 1.0


def mock_get_inflation_rate(country_code="ZAF"):
    return MOCK_INFLATION


# ---------------------------------------------------------------------------
# _normalize_frequency
# ---------------------------------------------------------------------------

class TestNormalizeFrequency:
    def test_once_off(self):
        assert _normalize_frequency(100, "once-off", 5) == 100

    def test_daily(self):
        assert _normalize_frequency(30, "daily", 1) == 30 * 365

    def test_weekly(self):
        assert _normalize_frequency(200, "weekly", 2) == 200 * 52 * 2

    def test_monthly(self):
        assert _normalize_frequency(500, "monthly", 3) == 500 * 12 * 3

    def test_zero_years(self):
        assert _normalize_frequency(100, "daily", 0) == 0

    def test_unknown_frequency_defaults_to_multiplier_1(self):
        # Unknown frequency falls back to multiplier=1, so returns amount * years
        assert _normalize_frequency(100, "yearly", 1) == 100 * 1 * 1


# ---------------------------------------------------------------------------
# _calculate_total_spent_zar
# ---------------------------------------------------------------------------

class TestCalculateTotalSpentZar:
    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    def test_zar_daily(self, _):
        total, rate = _calculate_total_spent_zar(30, "ZAR", "daily", 1)
        assert rate == 1.0
        assert total == pytest.approx(30 * 365)

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    def test_usd_monthly(self, _):
        total, rate = _calculate_total_spent_zar(15, "USD", "monthly", 1)
        assert rate == MOCK_ZAR_RATE
        assert total == pytest.approx(15 * MOCK_ZAR_RATE * 12)

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    def test_once_off(self, _):
        total, rate = _calculate_total_spent_zar(500, "ZAR", "once-off", 5)
        assert total == pytest.approx(500)


# ---------------------------------------------------------------------------
# calculate_habit_gravity
# ---------------------------------------------------------------------------

class TestHabitGravity:
    def test_coffee_high(self):
        score = calculate_habit_gravity("habit", "coffee")
        assert score == pytest.approx(75.0)

    def test_food_low(self):
        score = calculate_habit_gravity("need", "food")
        assert score == pytest.approx(35.0)

    def test_travel_high(self):
        score = calculate_habit_gravity("want", "travel")
        assert score == pytest.approx(80.0)

    def test_unknown_subcategory_defaults(self):
        score = calculate_habit_gravity("need", "xyz_unknown")
        assert 0.0 <= score <= 100.0

    def test_score_bounded_for_all_known(self):
        for cat, subs in WEIGHT_MATRIX.items():
            for sub in subs:
                s = calculate_habit_gravity(cat, sub)
                assert 0.0 <= s <= 100.0


# ---------------------------------------------------------------------------
# calculate_rand_betrayal
# ---------------------------------------------------------------------------

class TestRandBetrayal:
    def test_zar_is_zero(self):
        score, explanation = calculate_rand_betrayal("ZAR", 1)
        assert score == 0.0
        assert "no currency exchange risk" in explanation.lower()

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    def test_usd_depreciation(self, _hist, _cur):
        score, explanation = calculate_rand_betrayal("USD", 3)
        # 15 → 18.5 ≈ 23.3% depreciation
        expected = (18.5 - 15.0) / 15.0 * 100
        assert score == pytest.approx(expected, abs=1)
        assert "USD" in explanation

    def test_score_capped_at_100(self):
        with (
            patch("calculator.get_exchange_rate", return_value=100.0),
            patch("calculator.get_historical_exchange_rate", return_value=1.0),
        ):
            score, _ = calculate_rand_betrayal("USD", 1)
            assert score <= 100.0

    def test_score_not_negative_when_rand_strengthened(self):
        with (
            patch("calculator.get_exchange_rate", return_value=10.0),
            patch("calculator.get_historical_exchange_rate", return_value=20.0),
        ):
            score, _ = calculate_rand_betrayal("USD", 1)
            assert score == 0.0


# ---------------------------------------------------------------------------
# calculate_inflation_creep
# ---------------------------------------------------------------------------

class TestInflationCreep:
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_one_year(self, _):
        score, rate, explanation = calculate_inflation_creep(1)
        expected_cumulative = (1 + MOCK_INFLATION) ** 1 - 1
        assert score == pytest.approx(expected_cumulative * 100, abs=0.01)
        assert rate == MOCK_INFLATION
        assert "5.6%" in explanation

    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_longer_period_higher_score(self, _):
        score1, _, _ = calculate_inflation_creep(1)
        score5, _, _ = calculate_inflation_creep(5)
        assert score5 > score1

    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_score_capped_at_100(self, _):
        score, _, _ = calculate_inflation_creep(1000)
        assert score <= 100.0


# ---------------------------------------------------------------------------
# calculate_opportunity_ghost
# ---------------------------------------------------------------------------

class TestOpportunityGhost:
    def test_zero_spend_returns_zero_score(self):
        score, ghost, _ = calculate_opportunity_ghost(0, "coffee", 1, "daily", None)
        assert score == 0.0
        assert ghost == 0.0

    def test_positive_spend_earns_ghost_money(self):
        score, ghost, _ = calculate_opportunity_ghost(10000, "coffee", 1, "daily", None)
        assert ghost > 0.0
        assert score > 0.0

    def test_longer_period_more_ghost(self):
        _, ghost1, _ = calculate_opportunity_ghost(10000, "coffee", 1, "daily", None)
        _, ghost5, _ = calculate_opportunity_ghost(10000, "coffee", 5, "daily", None)
        assert ghost5 > ghost1

    def test_unknown_subcategory_uses_default(self):
        score, ghost, _ = calculate_opportunity_ghost(5000, "xyz_unknown", 2, "monthly", None)
        assert score >= 0.0

    def test_explanation_contains_sector_name(self):
        _, _, explanation = calculate_opportunity_ghost(1000, "coffee", 1, "daily", None)
        assert "Coffee" in explanation


# ---------------------------------------------------------------------------
# get_severity
# ---------------------------------------------------------------------------

class TestGetSeverity:
    def test_low(self):
        assert get_severity(0) == "LOW"
        assert get_severity(10) == "LOW"
        assert get_severity(24.9) == "LOW"

    def test_medium(self):
        assert get_severity(25) == "MEDIUM"
        assert get_severity(49.9) == "MEDIUM"

    def test_high(self):
        assert get_severity(50) == "HIGH"
        assert get_severity(74.9) == "HIGH"

    def test_severe(self):
        assert get_severity(75) == "SEVERE"
        assert get_severity(100) == "SEVERE"


# ---------------------------------------------------------------------------
# calculate_regret (integration)
# ---------------------------------------------------------------------------

class TestCalculateRegret:
    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_returns_required_keys(self, _inf, _hist, _cur):
        result = calculate_regret({
            "amount": 30, "currency": "ZAR", "frequency": "daily",
            "category": "habit", "sub_category": "coffee", "years": 1,
        })
        required = {
            "total_spent_zar", "habit_gravity_score", "rand_betrayal_score",
            "inflation_creep_score", "opportunity_ghost_score", "time_thief_score",
            "opportunity_ghost_value", "inflation_explanation", "opportunity_explanation",
            "rand_explanation", "severity",
        }
        assert required.issubset(result.keys())

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_severity_dict_has_all_genes(self, _inf, _hist, _cur):
        result = calculate_regret({
            "amount": 30, "currency": "ZAR", "frequency": "daily",
            "category": "habit", "sub_category": "coffee", "years": 1,
        })
        assert set(result["severity"].keys()) == {
            "habit_gravity", "rand_betrayal", "inflation_creep", "opportunity_ghost"
        }

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_zar_daily_coffee_total(self, _inf, _hist, _cur):
        result = calculate_regret({
            "amount": 30, "currency": "ZAR", "frequency": "daily",
            "category": "habit", "sub_category": "coffee", "years": 1,
        })
        assert result["total_spent_zar"] == pytest.approx(30 * 365, abs=0.01)

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_usd_monthly_netflix_rand_betrayal(self, _inf, _hist, _cur):
        result = calculate_regret({
            "amount": 15, "currency": "USD", "frequency": "monthly",
            "category": "habit", "sub_category": "subscriptions", "years": 1,
        })
        expected_zar = 15 * MOCK_ZAR_RATE * 12
        assert result["total_spent_zar"] == pytest.approx(expected_zar, abs=0.01)
        assert result["rand_betrayal_score"] > 0

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_scores_bounded_0_to_100(self, _inf, _hist, _cur):
        result = calculate_regret({
            "amount": 999999, "currency": "USD", "frequency": "daily",
            "category": "habit", "sub_category": "gaming", "years": 50,
        })
        for key in ("habit_gravity_score", "rand_betrayal_score",
                    "inflation_creep_score", "opportunity_ghost_score", "time_thief_score"):
            assert 0.0 <= result[key] <= 100.0, f"{key} out of bounds: {result[key]}"

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_time_thief_is_equal_weighted_average(self, _inf, _hist, _cur):
        result = calculate_regret({
            "amount": 30, "currency": "ZAR", "frequency": "daily",
            "category": "habit", "sub_category": "coffee", "years": 1,
        })
        expected = round(
            0.25 * result["habit_gravity_score"]
            + 0.25 * result["rand_betrayal_score"]
            + 0.25 * result["inflation_creep_score"]
            + 0.25 * result["opportunity_ghost_score"],
            2,
        )
        assert result["time_thief_score"] == pytest.approx(expected, abs=0.01)

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_missing_optional_fields_dont_crash(self, _inf, _hist, _cur):
        result = calculate_regret({"amount": 100, "currency": "ZAR", "years": 1})
        assert "time_thief_score" in result

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_once_off_total_equals_amount(self, _inf, _hist, _cur):
        result = calculate_regret({
            "amount": 500, "currency": "ZAR", "frequency": "once-off",
            "category": "want", "sub_category": "clothing", "years": 1,
        })
        assert result["total_spent_zar"] == pytest.approx(500, abs=0.01)


# ---------------------------------------------------------------------------
# Flask app integration (in-memory SQLite, no real HTTP calls)
# ---------------------------------------------------------------------------

class TestFlaskApp:
    @pytest.fixture
    def client(self):
        import app as app_module
        flask_app = app_module.create_app()
        flask_app.config["TESTING"] = True
        flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        from models import db
        with flask_app.app_context():
            db.create_all()
        with flask_app.test_client() as c:
            yield c

    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_history_returns_200(self, client):
        resp = client.get("/history")
        assert resp.status_code == 200

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_calculate_redirects_to_result(self, _inf, _hist, _cur, client):
        resp = client.post("/calculate", data={
            "description": "Daily coffee test",
            "amount": "30",
            "currency": "ZAR",
            "frequency": "daily",
            "category": "habit",
            "sub_category": "coffee",
            "sub_sub_category": "cappuccino",
            "years": "1",
        })
        assert resp.status_code == 302
        assert "/result/" in resp.headers["Location"]

    @patch("calculator.get_exchange_rate", side_effect=mock_get_exchange_rate)
    @patch("calculator.get_historical_exchange_rate", side_effect=mock_get_historical_exchange_rate)
    @patch("calculator.get_inflation_rate", side_effect=mock_get_inflation_rate)
    def test_result_page_returns_200(self, _inf, _hist, _cur, client):
        resp = client.post("/calculate", data={
            "description": "Test entry",
            "amount": "50",
            "currency": "ZAR",
            "frequency": "monthly",
            "category": "need",
            "sub_category": "food",
            "years": "2",
        }, follow_redirects=False)
        location = resp.headers["Location"]
        result_resp = client.get(location)
        assert result_resp.status_code == 200

    def test_calculate_missing_description_shows_flash(self, client):
        resp = client.post("/calculate", data={
            "amount": "30", "currency": "ZAR",
            "frequency": "daily", "category": "habit",
            "sub_category": "coffee", "years": "1",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_calculate_invalid_amount_shows_flash(self, client):
        resp = client.post("/calculate", data={
            "description": "Test",
            "amount": "abc", "currency": "ZAR",
            "frequency": "daily", "category": "habit",
            "sub_category": "coffee", "years": "1",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_result_404_for_missing_entry(self, client):
        resp = client.get("/result/99999")
        assert resp.status_code == 404
