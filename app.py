import os

from flask import Flask, render_template, request, redirect, url_for, flash, abort

from calculator import calculate_regret
from models import db, RegretEntry


def _severity_label(score: float) -> str:
    if score >= 75:
        return "SEVERE"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "devsecret")

    # Ensure the instance folder exists (used for the sqlite database file).
    os.makedirs(app.instance_path, exist_ok=True)

    db_path = os.path.join(app.instance_path, "regret.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Create DB tables on startup if they don't exist.
    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/calculate", methods=["POST"])
    def calculate():
        # Basic validation
        description = request.form.get("description", "").strip()
        amount = request.form.get("amount", "")
        currency = request.form.get("currency", "ZAR")
        frequency = request.form.get("frequency", "once-off")
        category = request.form.get("category", "need")
        sub_category = request.form.get("sub_category", "")
        sub_sub_category = request.form.get("sub_sub_category", "").strip()
        years = request.form.get("years", "1")

        if not description:
            flash("Please enter a description of your spending.")
            return redirect(url_for("index"))

        try:
            amount_f = float(amount)
            years_f = float(years)
            if amount_f <= 0 or years_f <= 0:
                raise ValueError
        except Exception:
            flash("Amount and years must be numbers greater than zero.")
            return redirect(url_for("index"))

        entry_data = {
            "amount": amount_f,
            "currency": currency,
            "frequency": frequency,
            "category": category,
            "sub_category": sub_category,
            "sub_sub_category": sub_sub_category,
            "years": years_f,
        }

        result = calculate_regret(entry_data)

        entry = RegretEntry(
            description=description,
            amount=amount_f,
            currency=currency,
            frequency=frequency,
            category=category,
            sub_category=sub_category,
            sub_sub_category=sub_sub_category or None,
            years=years_f,
            habit_gravity_score=result["habit_gravity_score"],
            rand_betrayal_score=result["rand_betrayal_score"],
            inflation_creep_score=result["inflation_creep_score"],
            opportunity_ghost_score=result["opportunity_ghost_score"],
            time_thief_score=result["time_thief_score"],
        )

        db.session.add(entry)
        db.session.commit()

        return redirect(url_for("result", entry_id=entry.id))

    @app.route("/result/<int:entry_id>")
    def result(entry_id):
        entry = RegretEntry.query.get_or_404(entry_id)
        entry_data = {
            "amount": entry.amount,
            "currency": entry.currency,
            "frequency": entry.frequency,
            "category": entry.category,
            "sub_category": entry.sub_category,
            "sub_sub_category": entry.sub_sub_category or "",
            "years": entry.years,
        }
        result = calculate_regret(entry_data)
        return render_template("result.html", result=result)

    @app.route("/history")
    def history():
        entries = RegretEntry.query.order_by(RegretEntry.created_at.desc()).all()
        enriched = []
        for entry in entries:
            enriched.append(
                {
                    "id": entry.id,
                    "description": entry.description,
                    "amount": entry.amount,
                    "currency": entry.currency,
                    "frequency": entry.frequency,
                    "category": entry.category,
                    "time_thief_score": entry.time_thief_score or 0.0,
                    "time_thief_badge": _severity_label(entry.time_thief_score or 0.0),
                    "created_at": entry.created_at,
                }
            )
        return render_template("history.html", entries=enriched)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
