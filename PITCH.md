---
marp: true
theme: default
class: invert
paginate: true
style: |
  section {
    font-family: 'Segoe UI', sans-serif;
    background-color: #0d1117;
    color: #e6edf3;
  }
  h1 { color: #58a6ff; }
  h2 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 0.3em; }
  h3 { color: #79c0ff; }
  blockquote {
    border-left: 4px solid #58a6ff;
    color: #8b949e;
    font-style: italic;
  }
  table { width: 100%; }
  th { background-color: #161b22; color: #58a6ff; }
  td { background-color: #0d1117; }
  tr:nth-child(even) td { background-color: #161b22; }
  code { background-color: #161b22; color: #f0883e; }
  pre { background-color: #161b22; border: 1px solid #30363d; }
  strong { color: #f0883e; }
  section.title {
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
  }
  section.title h1 { font-size: 2.8em; }
  section.title h3 { color: #8b949e; }
  section.closer {
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
  }
  section.closer h1 { font-size: 2.2em; margin: 0.4em 0; }
---

<!-- _class: title -->

# Financial Regret Simulator 😬

### ECO5040S Mini-Hackathon · 5-Minute Demo

---

<!-- _class: "" -->

# Is your daily coffee really just R30?

> **Spoiler: Over 5 years, it costs you R80,000.**

Most of us make financial decisions based on the sticker price.

We ignore what that money *could have become*.
We ignore what inflation is doing to our spending power.
We ignore the slow betrayal of the Rand.

**We built a tool that shows you the full picture.**

---

## The Problem

### Small decisions. Huge hidden costs.

| What you think you're paying | What you're actually paying |
|---|---|
| R30/day for coffee | R54,750 over 5 years + R25,696 in lost returns |
| $15/month Netflix | ZAR weakening = silent annual price hike |
| Weekly takeaways | Inflation erodes every rand you spend |

> "It's just coffee" is one of the most expensive sentences in personal finance.

The problem isn't the purchase — it's **not seeing the full cost** at the moment of decision.

---

## Our Solution

# The Financial Regret Simulator

A web app that takes any spending decision and reveals its **Regret DNA** —
four scores that quantify the hidden costs from four different angles.

&nbsp;

**Input:** What you bought · how much · how often · for how long

**Output:** A complete financial regret profile

---

## The Regret DNA

### Four genes. One score. The full truth.

```
🔥 Habit Gravity     ─── How unconscious is this spending?
📉 Rand Betrayal     ─── How much is the ZAR losing vs foreign currencies?
🍎 Inflation Creep   ─── How much purchasing power are you losing?
💸 Opportunity Ghost ─── What could you have earned if invested instead?
                                   ↓
                      ⏰  TIME THIEF SCORE  (0–100)
```

Each gene is scored **0–100**.
The **Time Thief Score** is the equal-weighted average.
Together they tell you not just *how much* you spent, but *why* you'll regret it.

---

## Gene Deep Dive (1 of 2)

### 🔥 Habit Gravity
Rooted in behavioural economics — unconscious spending causes more regret than deliberate spending.

- Daily coffee (habit): **75/100** — you barely think about it
- Planned holiday (want): **80/100** — deliberate but high-cost
- Buying food (need): **35/100** — necessary, minimal regret

### 📉 Rand Betrayal
South Africa-specific. Every dollar-denominated subscription gets a silent ZAR price increase each year.

- Uses **live + historical Frankfurter exchange rates**
- Quantifies cumulative ZAR depreciation over the spending period
- Always **0** for ZAR spending — fair for local purchases

---

## Gene Deep Dive (2 of 2)

### 🍎 Inflation Creep
Your money loses purchasing power. The cumulative effect over years is dramatic.

- Live SA inflation rate from the **World Bank API**
- 5.6% over 5 years → ~31% cumulative erosion
- The money you spent in year 1 buys 31% less by year 5

### 💸 Opportunity Ghost
The most eye-opening score. What could that money have grown into?

- Spending category maps to a **real investment sector** with historical returns
- Coffee → Coffee/Café stocks (~8% p.a.)
- Tech purchases → Technology sector (~14% p.a.)
- **Ghost value** = what you *could have had* but don't

---

## Live Demo

### "How expensive is that daily coffee really?"

**Input:** R30 · ZAR · Daily · Habit / Coffee · 5 years

| Gene | Score | Severity |
|---|---|---|
| 🔥 Habit Gravity | 75.0 | **SEVERE** |
| 📉 Rand Betrayal | 0.0 | LOW |
| 🍎 Inflation Creep | 23.8 | LOW |
| 💸 Opportunity Ghost | 46.9 | MEDIUM |
| ⏰ **Time Thief Score** | **36.4 / 100** | **MEDIUM** |

**Total spent:** R54,750 · **Ghost money:** R25,696 · **Could have been:** R80,445

> Your daily coffee isn't just R30. It's a R80,000 decision over 5 years.

---

## Technical Implementation

### Built in < 48 hours. Production-quality code.

| Requirement | How we met it |
|---|---|
| Flask ≥ 2 routes | 4 routes: `/` · `/calculate` · `/result/<id>` · `/history` |
| HTML/CSS + Jinja2 | Dark-themed UI with dynamic sub-category dropdowns |
| SQLAlchemy + SQLite | `RegretEntry` (calculations) + `SectorReturn` (seeded lookup) |
| External API | **2 APIs**: World Bank (inflation) + Frankfurter (FX rates) |
| Regret Score | 4-gene formula, equal-weighted, 0–100 |

**Bonus:** Graceful API fallbacks · 45 automated tests (100% passing) · History page · Sector-mapped returns

---

## What Makes This Different

### We went beyond the brief.

| Standard approach | Our approach |
|---|---|
| Single formula | 4-gene scoring system |
| Generic market returns | Sector-specific returns per spending type |
| Ignores currency | Dedicated Rand Betrayal gene |
| Static inflation | Live World Bank API per calculation |
| One result page | Full history to track decisions over time |

The **Regret DNA metaphor** makes complex economics feel intuitive.
Genes are a universal shorthand for "what makes something what it is."
Your Regret DNA is what makes a bad financial decision *specifically bad for you*.

---

## What We'd Build Next

### If we had more time:

1. **Comparison mode** — Coffee vs Investment: head-to-head chart
2. **Share your Regret DNA** — unique URL per result for social sharing
3. **Email reminder** — "You've spent R10,000 on coffee this year"
4. **Crypto gene** — volatility score for BTC/ETH spending decisions
5. **Goal planner** — "Stop the habit and reach your house deposit in X years"

---

<!-- _class: closer -->

# Your spending has a DNA.

# Now you can read it.

&nbsp;

`python app.py` → http://127.0.0.1:5001

&nbsp;

*Flask · SQLAlchemy · World Bank API · Frankfurter API*
*ECO5040S Mini-Hackathon*
