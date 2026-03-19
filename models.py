from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# Shared SQLAlchemy instance; import from this module in app and other modules.
db = SQLAlchemy()


class RegretEntry(db.Model):
    __tablename__ = "regret_entry"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(512), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(8), nullable=False)
    frequency = db.Column(db.String(32), nullable=False)

    category = db.Column(db.String(32), nullable=False)
    sub_category = db.Column(db.String(64), nullable=False)
    sub_sub_category = db.Column(db.String(128), nullable=True)

    years = db.Column(db.Float, nullable=False, default=1.0)

    habit_gravity_score = db.Column(db.Float, nullable=True)
    rand_betrayal_score = db.Column(db.Float, nullable=True)
    inflation_creep_score = db.Column(db.Float, nullable=True)
    opportunity_ghost_score = db.Column(db.Float, nullable=True)
    time_thief_score = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SectorReturn(db.Model):
    __tablename__ = "sector_return"

    id = db.Column(db.Integer, primary_key=True)
    sector_name = db.Column(db.String(128), unique=True, nullable=False)
    annual_return_pct = db.Column(db.Float, nullable=False)
    example_stock = db.Column(db.String(128), nullable=True)
    keywords = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
