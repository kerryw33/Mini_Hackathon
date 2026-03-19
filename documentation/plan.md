# Financial Regret Simulator — Refined Plan

## Concept Summary

A Flask web app that accepts financial decisions from users and reveals the **hidden long-term cost** of those decisions through a "Time Regret" lens. The output is not just a score but a **Regret DNA profile** — a visual breakdown of exactly *how* and *why* a decision is hurting the user financially over time.

---

## Core User Flow

1. User lands on the home page
2. User enters one or more financial line items:
   - Description (e.g., "Daily coffee")
   - Amount
   - Currency (ZAR, USD, GBP, EUR, etc.)
   - Frequency (daily, weekly, monthly, once-off)
   - Category: **Need**, **Want**, or **Habit**
   - Sub-category: selected from a list specific to the chosen category (e.g., Need → Food)
   - Sub-sub-category: optional free-text or dropdown (e.g., Food → Bread)
3. User submits — app calculates and displays:
   - The **Regret DNA profile** (4 genes + final score)
   - A breakdown of each gene with plain-language explanation
   - Historical data stored to SQLite

---

## Regret DNA — The Four "Genes"

### 1. Habit Gravity (Category Weighting)
- Reflects how unconscious/compulsive the spending is
- Driven by the top-level category and the sub-category chosen
- The sub-sub-category is optional and purely descriptive (not used in scoring)

**Category taxonomy and weight matrix:**

| Category | Sub-category     | Weight | Linked Sector (Opportunity Ghost) |
|----------|------------------|--------|-----------------------------------|
| Need     | Food             | 0.20   | Food & Beverage                   |
| Need     | Housing          | 0.30   | Real Estate                       |
| Need     | Healthcare       | 0.25   | Health & Pharmacy                 |
| Need     | Transport        | 0.30   | Transport & Fuel                  |
| Need     | Education        | 0.35   | Education                         |
| Want     | Clothing         | 0.50   | Apparel                           |
| Want     | Dining Out       | 0.55   | Food & Beverage                   |
| Want     | Entertainment    | 0.50   | Streaming & Entertainment         |
| Want     | Technology       | 0.60   | Technology & Electronics          |
| Want     | Travel           | 0.65   | Travel & Leisure                  |
| Habit    | Coffee           | 0.80   | Food & Beverage                   |
| Habit    | Subscriptions    | 0.75   | Streaming & Entertainment         |
| Habit    | Alcohol & Social | 0.85   | Food & Beverage                   |
| Habit    | Fitness          | 0.70   | Fitness & Health                  |
| Habit    | Gaming           | 0.90   | Gaming                            |

**Sub-sub-category examples (optional, free text — shown on result page for context):**

| Sub-category  | Example sub-sub-categories          |
|---------------|-------------------------------------|
| Food          | Bread, Groceries, Meat, Dairy       |
| Coffee        | Cappuccino, Cold Brew, Filter       |
| Subscriptions | Netflix, Spotify, Adobe, iCloud     |
| Clothing      | Shoes, Jeans, Formal Wear           |
| Transport     | Petrol, Uber, Bus Pass              |

### 2. Rand Betrayal (Currency Erosion)
- Only relevant when spending in a foreign currency (e.g., USD subscriptions paid in ZAR)
- Uses **Frankfurter API** to calculate effective ZAR cost vs original amount
- Measures how much more you're actually paying due to exchange rate degradation
- If primary currency = spending currency → score is 0 (no erosion)

### 3. Inflation Creep
- Uses **World Bank API** to fetch historical inflation rate (South Africa default: ZAF indicator `FP.CPI.TOTL.ZG`)
- Calculates real purchasing power lost over the spending period
- The longer the habit, the higher the creep

### 4. Opportunity Ghost (Opportunity Cost)
- What could the user have earned if they invested that money instead?
- App uses **pre-seeded database** with category → stock sector mapping and historical returns
- Example: "Clothing" → Apparel sector → ~8% avg annual return
- Calculates compound growth over the spending period
- Shows the "ghost money" they never earned

### Final Time Thief Score Formula

```
Habit Gravity Score     = weight_matrix[category][sub_category] × 100
Rand Betrayal Score     = ((effective_ZAR_cost / original_amount) - 1) × 100 (capped at 100)
Inflation Creep Score   = (inflation_rate × years) × 100 (capped at 100)
Opportunity Ghost Score = (opportunity_value / total_spent - 1) × 100 (capped at 100)

Time Thief Score = (
  0.25 × Habit Gravity Score +
  0.25 × Rand Betrayal Score +
  0.25 × Inflation Creep Score +
  0.25 × Opportunity Ghost Score
)
```

Weights can be adjusted — equal weighting is a sensible starting point.

---

## Data Model (SQLAlchemy / SQLite)

### `RegretEntry`
| Field | Type | Description |
|-------|------|-------------|
| id | Integer PK | |
| description | String | e.g., "Daily coffee" |
| amount | Float | |
| currency | String | e.g., "ZAR", "USD" |
| frequency | String | daily/weekly/monthly/once-off |
| category | String | need/want/habit |
| sub_category | String | e.g., food, coffee, subscriptions |
| sub_sub_category | String (nullable) | e.g., bread, cappuccino, netflix |
| years | Float | Projection period |
| habit_gravity_score | Float | |
| rand_betrayal_score | Float | |
| inflation_creep_score | Float | |
| opportunity_ghost_score | Float | |
| time_thief_score | Float | Final 0–100 score |
| created_at | DateTime | |

### `SectorReturn` (pre-seeded)
| Field | Type | Description |
|-------|------|-------------|
| id | Integer PK | |
| sector | String | e.g., "Apparel", "Food & Beverage" |
| annual_return_pct | Float | Historical avg return |
| example_stock | String | e.g., "NKE" |
| keywords | String | Comma-separated match terms |

---

## Flask Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Home page — input form |
| `/calculate` | POST | Process inputs, calculate scores |
| `/result/<id>` | GET | Display Regret DNA for a saved entry |
| `/history` | GET | Show past regret entries from DB |

---

## External APIs

| API | Purpose | Endpoint |
|-----|---------|----------|
| World Bank | Inflation rate (ZAF) | `https://api.worldbank.org/v2/country/ZAF/indicator/FP.CPI.TOTL.ZG?format=json` |
| Frankfurter | Exchange rates | `https://api.frankfurter.app/latest?from=USD&to=ZAR` |

Both are free and require no API key.

---

## Frontend Design

- Clean, dark-themed UI with a financial/data aesthetic
- Home: form with dynamic "add line item" button (can enter multiple items)
- Result: animated **Regret DNA** card showing the four genes with color-coded severity
- Each gene has a label, severity badge (LOW/MEDIUM/HIGH/SEVERE), and a one-line plain-language explanation
- Final score displayed as a large dial/gauge

---

## Folder Structure

```
Mini_Hackathon/
├── app.py                  # Flask app entry point
├── models.py               # SQLAlchemy models
├── calculator.py           # Regret score calculation logic
├── api_clients.py          # World Bank + Frankfurter API calls
├── seed.py                 # Script to seed SectorReturn table
├── templates/
│   ├── base.html
│   ├── index.html          # Input form
│   ├── result.html         # Regret DNA display
│   └── history.html        # Past entries
├── static/
│   ├── style.css
│   └── script.js           # Dynamic form fields
├── instance/
│   └── regret.db           # SQLite database (auto-created)
└── requirements.txt
```

---

## Non-Goals (Scope Boundaries)

- No user authentication
- No live stock API (pre-seeded data only)
- No multi-currency output (output always in ZAR)
- No mobile-optimised design (desktop is fine for demo)
