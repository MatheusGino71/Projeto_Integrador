"""Modelo relacional compartilhado pelo SQLite e pelo PostgreSQL."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index, text

db = SQLAlchemy()


class Equipment(db.Model):
    __tablename__ = "equipment"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    asset_code = db.Column(db.String(30), nullable=False, unique=True)
    category = db.Column(db.String(40), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(20), nullable=False, default="ready")
    notes = db.Column(db.String(500), nullable=False, default="")
    loans = db.relationship("Loan", back_populates="equipment", lazy="selectin")

    __table_args__ = (
        CheckConstraint("condition IN ('ready', 'maintenance', 'retired')", name="equipment_condition"),
    )

    @property
    def status(self):
        if any(loan.returned_on is None for loan in self.loans):
            return "borrowed"
        return "available" if self.condition == "ready" else self.condition


class Person(db.Model):
    __tablename__ = "person"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    registration = db.Column(db.String(30), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    loans = db.relationship("Loan", back_populates="person", lazy="selectin")

    __table_args__ = (
        CheckConstraint("role IN ('student', 'teacher', 'staff')", name="person_role"),
    )

    @property
    def active_count(self):
        return sum(loan.returned_on is None for loan in self.loans)


class Loan(db.Model):
    __tablename__ = "loan"

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    borrowed_on = db.Column(db.Date, nullable=False)
    due_on = db.Column(db.Date, nullable=False)
    returned_on = db.Column(db.Date)
    notes = db.Column(db.String(500), nullable=False, default="")
    return_notes = db.Column(db.String(500), nullable=False, default="")
    equipment = db.relationship("Equipment", back_populates="loans", lazy="joined")
    person = db.relationship("Person", back_populates="loans", lazy="joined")

    __table_args__ = (
        CheckConstraint("due_on >= borrowed_on", name="loan_due_date"),
        CheckConstraint("returned_on IS NULL OR returned_on >= borrowed_on", name="loan_return_date"),
        Index(
            "one_active_loan_per_equipment", "equipment_id", unique=True,
            sqlite_where=text("returned_on IS NULL"),
            postgresql_where=text("returned_on IS NULL"),
        ),
    )

    def status_on(self, today):
        if self.returned_on:
            return "returned"
        return "overdue" if self.due_on < today else "active"

    def late_days(self, today):
        return max(0, ((self.returned_on or today) - self.due_on).days)
