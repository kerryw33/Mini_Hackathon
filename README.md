# Financial Regret Simulator

> ECO5040S Mini-Hackathon — *"What might I regret about this purchase later?"*

A Flask web application that transforms everyday spending decisions into a **Regret DNA** profile — four financial scores that reveal the hidden long-term cost of what you buy.

---

## What It Does

You enter a spending decision (e.g. "daily R30 coffee for 5 years"). The app calculates **four gene scores**, each measuring a different dimension of financial regret, and combines them into a final **Time Thief Score** (0–100).

---

## The Regret DNA — Four Gene Scores

| Gene | Emoji | What it measures |
|---|---|---|
| **Habit Gravity** | 🔥 | How unconscious/compulsive is this spending? A daily coffee habit scores higher than a planned vacation. |
| **Rand Betrayal** | 📉 | ZAR depreciation against the foreign currency over the spending period. Only applies to non-ZAR spending. |
| **Inflation Creep** | 🍎 | Purchasing power lost to SA inflation over the projection period, using live World Bank data. |
| **Opportunity Ghost** | 💸 | Investment opportunity cost — how much the money could have grown if invested in the relevant sector. |

**Time Thief Score** = equal-weighted average of all four genes (0–100).

| Score | Meaning |
|---|---|
| 0–24 | LOW — probably fine |
| 25–49 | MEDIUM — mild regret |
| 50–74 | HIGH — risky decision |
| 75–100 | SEVERE — high regret |

---

## How the Calculations Work

### Total Spend (ZAR)
1. Fetch live exchange rate (Frankfurter API)
2. Convert amount to ZAR
3. Apply frequency multiplier: daily ×365, weekly ×52, monthly ×12, once-off ×1
4. Multiply by years

### Habit Gravity
Looks up a pre-defined weight matrix by `category` + `sub_category`:
- **Need** (food, housing, healthcare, transport, education): 20–35
- **Want** (clothing, dining, entertainment, technology, travel): 60–80
- **Habit** (coffee, subscriptions, alcohol, fitness, gaming): 25–80

### Rand Betrayal
```
depreciation = (current_rate - historical_rate) / historical_rate
score = min(100, max(0, depreciation × 100))
```
Fetches current and historical (N years ago) exchange rates from Frankfurter. Score is 0 for ZAR spending.

### Inflation Creep
```
cumulative = (1 + inflation_rate) ^ years - 1
score = min(100, cumulative × 100)
```
Inflation rate fetched live from the World Bank API (SA CPI indicator).

### Opportunity Ghost
```
opportunity_value = total_spent × (1 + sector_return) ^ years
ghost_value = opportunity_value - total_spent
score = min(100, (opportunity_value / total_spent - 1) × 100)
```
`sub_category` maps to a real investment sector with a seeded annual return rate (e.g. Coffee/Café → 8%, Technology → 14%).

---

## Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Home page with spending input form |
| `/calculate` | POST | Validates input, runs calculation, saves to DB, redirects to result |
| `/result/<id>` | GET | Displays the full Regret DNA breakdown |
| `/history` | GET | Table of all past calculations |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask (Python) |
| Database | SQLite via SQLAlchemy |
| Templates | Jinja2 + HTML/CSS |
| Frontend interactivity | Vanilla JavaScript |
| Exchange rates | [Frankfurter API](https://frankfurter.dev/) (no key required) |
| Inflation data | [World Bank API](https://datahelpdesk.worldbank.org/) (no key required) |

---

## Data Models

**`RegretEntry`** — one row per user calculation
- `description`, `amount`, `currency`, `frequency`, `category`, `sub_category`, `sub_sub_category`, `years`
- `habit_gravity_score`, `rand_betrayal_score`, `inflation_creep_score`, `opportunity_ghost_score`, `time_thief_score`
- `created_at`

**`SectorReturn`** — seeded lookup table
- `sector_name`, `annual_return_pct`, `example_stock`, `keywords`

---

## Setup & Running

```bash
# Install dependencies
pip install flask flask-sqlalchemy requests pytest

# Seed the sector returns database
python seed.py

# Run the app
python app.py
# → http://127.0.0.1:5001
```

---

## Running Tests

```bash
python -m pytest test.py -v
```

45 tests covering:
- All helper/gene functions in isolation
- Full `calculate_regret` integration
- Flask route tests (index, history, calculate, result, 404) using in-memory SQLite
- All external API calls mocked for speed and reliability

---

## External API Fallbacks

Both APIs have hardcoded fallback values so the app never crashes if the network is unavailable:
- Inflation fallback: **5.6%** (SA historical average)
- Exchange rate fallbacks: USD→ZAR 18.50, GBP→ZAR 23.50, EUR→ZAR 20.00, AUD→ZAR 12.00

---

## Project Structure

```
Mini_Hackathon/
├── app.py              # Flask app factory and routes
├── calculator.py       # Core calculation engine (all gene functions)
├── api_clients.py      # World Bank + Frankfurter API wrappers
├── models.py           # SQLAlchemy models
├── seed.py             # Seeds SectorReturn table
├── test.py             # Full pytest test suite (45 tests)
├── requirements.txt    # Python dependencies
├── static/
│   ├── script.js       # Dynamic sub-category dropdown
│   └── style.css       # Dark-themed UI
└── templates/
    ├── base.html        # Base layout with navbar
    ├── index.html       # Input form
    ├── result.html      # Regret DNA results
    └── history.html     # Past calculations table
```
