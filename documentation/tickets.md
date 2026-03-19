# Financial Regret Simulator — Build Tickets

Tickets are ordered to respect dependencies. Each ticket is self-contained enough to hand to an AI agent.

---

## Phase 1 — Project Scaffold

### TICKET-01: Flask Project Setup
**Priority:** Critical | **Depends on:** Nothing

Set up the base Flask project structure.

**Tasks:**
- Create `app.py` with Flask app factory
- Create `requirements.txt` with: `flask`, `flask-sqlalchemy`, `requests`
- Create folder structure: `templates/`, `static/`, `instance/`
- Create `base.html` Jinja2 template (HTML shell with head, navbar placeholder, block content)
- Add a `GET /` route that renders `index.html` with a placeholder "Coming soon" message
- Confirm app runs with `flask run`

**Acceptance criteria:** `flask run` starts without errors; visiting `http://localhost:5000` renders the base template.

---

### TICKET-02: Database Models
**Priority:** Critical | **Depends on:** TICKET-01

Define and initialise the SQLAlchemy data models.

**Tasks:**
- Create `models.py` with two models:
  1. `RegretEntry` — stores user input and all four gene scores + final score:
     - `id`, `description`, `amount`, `currency`, `frequency`
     - `category` (need/want/habit)
     - `sub_category` (e.g., food, coffee, subscriptions, clothing — see full list in `documentation/refined_plan.md`)
     - `sub_sub_category` (nullable String — e.g., bread, cappuccino, netflix — free text, optional)
     - `years`, `habit_gravity_score`, `rand_betrayal_score`, `inflation_creep_score`, `opportunity_ghost_score`, `time_thief_score`, `created_at`
  2. `SectorReturn` — stores sector → average annual return mapping (see schema in `documentation/refined_plan.md`)
- Wire models into `app.py` (import, `db.init_app`, `db.create_all` in app context)
- Confirm tables are created when app starts

**Acceptance criteria:** Running the app creates `instance/regret.db` with both tables visible (can verify with `sqlite3 instance/regret.db .tables`).

---

### TICKET-03: Seed Sector Returns Data
**Priority:** High | **Depends on:** TICKET-02

Pre-populate the `SectorReturn` table with representative data so the Opportunity Ghost score can be calculated without a live stock API.

**Tasks:**
- Create `seed.py` as a standalone script
- Seed at least 10 sectors with realistic historical average annual returns:
  - Food & Beverage → 7% (e.g., Nestlé)
  - Apparel/Clothing → 8% (e.g., Nike)
  - Technology/Electronics → 14% (e.g., Apple)
  - Coffee/Café → 9% (e.g., Starbucks)
  - Streaming/Entertainment → 11% (e.g., Netflix)
  - Transport/Fuel → 5% (e.g., Shell)
  - Fitness/Gym → 6% (e.g., Planet Fitness)
  - Gaming → 12% (e.g., Activision)
  - Health/Pharmacy → 8% (e.g., Pfizer)
  - General Retail → 6% (e.g., Walmart)
- Each record must include: sector name, annual_return_pct, example_stock, keywords (comma-separated words a user might type)
- Script must be idempotent (don't double-insert on re-run)
- Add a CLI command `flask seed` or just run `python seed.py`

**Acceptance criteria:** Running `python seed.py` populates the `sector_return` table with ≥10 rows.

---

## Phase 2 — Core Logic

### TICKET-04: API Clients Module
**Priority:** High | **Depends on:** TICKET-01

Build reusable functions for calling the two external APIs.

**Tasks:**
- Create `api_clients.py`
- Implement `get_inflation_rate(country_code="ZAF") -> float`:
  - Calls World Bank API: `https://api.worldbank.org/v2/country/{country_code}/indicator/FP.CPI.TOTL.ZG?format=json&mrv=1`
  - Returns the most recent annual inflation rate as a decimal (e.g., 0.056 for 5.6%)
  - Fallback: return `0.056` if API fails
- Implement `get_exchange_rate(from_currency: str, to_currency: str = "ZAR") -> float`:
  - Calls Frankfurter API: `https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}`
  - Returns the exchange rate as a float (e.g., 18.5 for USD→ZAR)
  - Fallback: return `1.0` if same currency, `18.5` for USD→ZAR if API fails
- Both functions must handle HTTP errors gracefully (try/except, log the error, return fallback)
- Write a simple `if __name__ == "__main__"` test block that prints results

**Acceptance criteria:** Running `python api_clients.py` prints a valid inflation rate and exchange rate without crashing.

---

### TICKET-05: Regret Score Calculator
**Priority:** Critical | **Depends on:** TICKET-03, TICKET-04

Implement the core calculation engine that produces all four gene scores and the final Time Thief Score.

**Tasks:**
- Create `calculator.py`
- Implement `calculate_regret(entry_data: dict) -> dict` that accepts:
  ```python
  {
    "amount": float,           # e.g., 30.0
    "currency": str,           # e.g., "ZAR"
    "frequency": str,          # "daily" | "weekly" | "monthly" | "once-off"
    "category": str,           # "need" | "want" | "habit"
    "sub_category": str,       # e.g., "coffee", "food", "subscriptions", "clothing"
    "sub_sub_category": str,   # optional, e.g., "cappuccino", "bread" — can be empty string
    "years": float,            # e.g., 1.0
  }
  ```
- Returns a dict with:
  ```python
  {
    "total_spent_zar": float,
    "habit_gravity_score": float,     # 0–100
    "rand_betrayal_score": float,     # 0–100
    "inflation_creep_score": float,   # 0–100
    "opportunity_ghost_score": float, # 0–100
    "time_thief_score": float,        # 0–100 (weighted average)
    "opportunity_ghost_value": float, # ZAR amount they "missed"
    "inflation_explanation": str,     # plain-language string
    "opportunity_explanation": str,
  }
  ```

**Gene formulas (see refined_plan.md for weight matrix):**
1. **Habit Gravity:** Look up `weight_matrix[category][sub_category]` → multiply by 100. The sub_sub_category is stored but does not affect scoring.
2. **Rand Betrayal:** `((effective_ZAR / original_amount) - 1) × 100`, capped at 100. If same currency, score = 0.
3. **Inflation Creep:** `inflation_rate × years × 100`, capped at 100
4. **Opportunity Ghost:** The `sub_category` maps directly to a sector (see weight matrix in refined_plan.md — "Linked Sector" column). Look up that sector in `SectorReturn`. Compound the total ZAR spent at that return rate over `years`. Score = `((opportunity_value / total_spent) - 1) × 100`, capped at 100. Default to 7% if no match.

**Final score:** equal-weighted average of the four gene scores.

**Acceptance criteria:** Unit-testable function. Call it with known inputs and verify the output dict contains all keys with values in range [0, 100].

---

## Phase 3 — Routes & Templates

### TICKET-06: Home Page — Input Form
**Priority:** High | **Depends on:** TICKET-01, TICKET-02

Build the user-facing input form.

**Tasks:**
- Create `templates/index.html` (extends `base.html`)
- Form fields per line item:
  - Description (text input)
  - Amount (number input)
  - Currency (dropdown: ZAR, USD, GBP, EUR, AUD)
  - Frequency (dropdown: daily, weekly, monthly, once-off)
  - Category (dropdown: Need, Want, Habit)
  - Sub-category (dropdown — options change based on category selection via JS):
    - Need → Food, Housing, Healthcare, Transport, Education
    - Want → Clothing, Dining Out, Entertainment, Technology, Travel
    - Habit → Coffee, Subscriptions, Alcohol & Social, Fitness, Gaming
  - Sub-sub-category (text input, optional — placeholder: "e.g. bread, cappuccino, Netflix")
  - Years to project (number input, default: 1)
- Submit button: "Calculate My Regret"
- Form `action="/calculate"` method `POST`
- **JS behaviour:** When the Category dropdown changes, dynamically repopulate the Sub-category dropdown with the correct options (defined in `static/script.js`). Sub-sub-category is always a free-text input — no JS needed.
- Style: clean, dark theme. Use CSS in `static/style.css`.

**Acceptance criteria:** Form renders at `/`, all dropdowns work, form submits correctly (even if `/calculate` just echoes back the data for now).

---

### TICKET-07: Calculate Route & Result Page
**Priority:** Critical | **Depends on:** TICKET-05, TICKET-06

Wire the calculation engine to the `/calculate` route and display the Regret DNA result.

**Tasks:**
- In `app.py`, add `POST /calculate` route:
  - Parse form data
  - Call `calculate_regret()` from `calculator.py`
  - Save a `RegretEntry` to the database
  - Redirect to `GET /result/<id>`
- Add `GET /result/<id>` route:
  - Load `RegretEntry` by ID
  - Render `result.html`
- Create `templates/result.html` displaying the Regret DNA card:
  ```
  🧬 REGRET DNA
  ├── 🔥 Habit Gravity:     [severity badge]
  ├── 📉 Rand Betrayal:     [severity badge]
  ├── 🍎 Inflation Creep:   [severity badge]
  ├── 💸 Opportunity Ghost: [severity badge]  (R{amount} never earned)
  └── ⏰ Time Thief Score:  {score}/100
  ```
- Severity badge logic: 0–25 = LOW, 25–50 = MEDIUM, 50–75 = HIGH, 75–100 = SEVERE
- Show total spent in ZAR and total "ghost money" missed
- Add a "Try Another" button linking back to `/`

**Acceptance criteria:** Submitting the form produces a result page with all four gene rows and a final score. Score is in range [0, 100].

---

### TICKET-08: History Page
**Priority:** Medium | **Depends on:** TICKET-07

Show past regret calculations.

**Tasks:**
- Add `GET /history` route in `app.py`
- Query all `RegretEntry` records, ordered by `created_at DESC`
- Create `templates/history.html` showing a table/list with:
  - Description, amount, currency, frequency, category
  - Final Time Thief Score (color-coded)
  - Link to `/result/<id>` for each entry
- Add nav link to History in `base.html`

**Acceptance criteria:** `/history` renders a list of past entries. Clicking an entry shows its full Regret DNA.

---

## Phase 4 — Polish & Demo Prep

### TICKET-09: UI Polish & Regret DNA Styling
**Priority:** Medium | **Depends on:** TICKET-07

Make the result page visually impressive for the demo.

**Tasks:**
- Style the Regret DNA card to look like a fingerprint/profile card:
  - Dark background, monospace font for the tree
  - Color-coded severity: green (LOW), yellow (MEDIUM), orange (HIGH), red (SEVERE)
  - Animated score counter on page load (CSS/JS)
- Style the score as a large number with a progress bar or gauge underneath
- Ensure the home form looks clean and professional
- Add basic responsive layout (flexbox/grid)
- All styling in `static/style.css`; any JS in `static/script.js`

**Acceptance criteria:** Result page looks polished on a 1080p screen. Score animates in on load. Severity badges are color-coded.

---

### TICKET-10: Error Handling & Edge Cases
**Priority:** Medium | **Depends on:** TICKET-07

Make the app robust enough for a live demo.

**Tasks:**
- Handle API failures gracefully (fallback values already in `api_clients.py` — verify they work)
- Validate form input: amount must be > 0, years must be > 0
- Show a user-friendly error message (flash message or inline) if validation fails
- Handle DB errors (wrap commits in try/except)
- Handle `/result/<id>` with a non-existent ID → 404 page

**Acceptance criteria:** App does not crash when the World Bank API is slow or down. Invalid form input shows an error without 500ing.

---

### TICKET-11: README & Demo Prep
**Priority:** Low | **Depends on:** All above

Finalize documentation and prepare for the 5-minute demo.

**Tasks:**
- Update `README.md` with:
  - Project description
  - Setup instructions (`pip install -r requirements.txt`, `python seed.py`, `flask run`)
  - How to use the app
  - Brief explanation of the Regret DNA formula
- Prepare 3 demo scenarios to show during presentation:
  1. Daily R30 coffee habit (1 year) → Habit + Inflation + Ghost
  2. USD Netflix subscription in ZAR → Rand Betrayal focus
  3. Monthly clothing spend → Opportunity Ghost (Apparel sector)
- Ensure the GitHub repo has a clear commit history

**Acceptance criteria:** Someone unfamiliar with the project can clone and run it in under 5 minutes using only the README.

---

## Ticket Order Summary

```
Phase 1 (Foundation)
  TICKET-01: Flask Project Setup
  TICKET-02: Database Models          ← needs TICKET-01
  TICKET-03: Seed Sector Data         ← needs TICKET-02

Phase 2 (Logic — can run in parallel with Phase 1 after TICKET-01)
  TICKET-04: API Clients              ← needs TICKET-01
  TICKET-05: Calculator               ← needs TICKET-03 + TICKET-04

Phase 3 (Routes & UI)
  TICKET-06: Home Page Form           ← needs TICKET-01
  TICKET-07: Calculate Route + Result ← needs TICKET-05 + TICKET-06
  TICKET-08: History Page             ← needs TICKET-07

Phase 4 (Polish)
  TICKET-09: UI Polish                ← needs TICKET-07
  TICKET-10: Error Handling           ← needs TICKET-07
  TICKET-11: README & Demo            ← needs all
```

### Parallelisation opportunities for AI agents:
- After TICKET-01 is done, an agent can start TICKET-04 (API clients) at the same time another starts TICKET-02+03 (DB).
- After TICKET-05 and TICKET-06 are done (can be parallel), TICKET-07 can proceed.
- TICKET-09 and TICKET-10 can run in parallel after TICKET-07.
