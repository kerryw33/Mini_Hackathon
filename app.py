import os

from flask import Flask, render_template

from models import db


def create_app():
    app = Flask(__name__, instance_relative_config=True)

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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
