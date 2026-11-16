"""Rotas HTML: formulários enviados ao Python, com renderização no servidor."""

import csv
import io
from collections import Counter
from datetime import timedelta

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from circula import today
from circula.models import Equipment, Loan, Person, db
from circula.services import CATEGORIES, CONDITIONS, ROLES, STATUSES, ValidationError, create_loan, load_demo, return_loan, save_equipment, save_person

web = Blueprint("web", __name__)


def all_equipment():
    return list(db.session.scalars(select(Equipment).order_by(Equipment.name)).unique())


def all_people():
    return list(db.session.scalars(select(Person).order_by(Person.name)).unique())


def all_loans():
    return list(db.session.scalars(select(Loan).order_by(Loan.id.desc())).unique())


def get_record(model, record_id):
    return db.get_or_404(model, record_id)


@web.context_processor
def shared():
    return {"categories": CATEGORIES, "conditions": CONDITIONS, "roles": ROLES, "statuses": STATUSES}


@web.get("/")
def dashboard():
    items, people, loans = all_equipment(), all_people(), all_loans()
    current = today()
    active = sorted((loan for loan in loans if not loan.returned_on), key=lambda loan: (loan.due_on, loan.id))
    overdue = [loan for loan in active if loan.due_on < current]
    available = sum(item.status == "available" for item in items)
    counts = Counter(item.category for item in items if item.condition != "retired")
    return render_template("dashboard.html", page="dashboard", equipment=items, people=people, loans=loans,
                           active_loans=active, overdue=overdue, available=available,
                           category_counts=counts.most_common(), total_in_use=sum(counts.values()),
                           empty=not items and not people and not loans)


@web.post("/demonstracao")
def demo():
    try:
        load_demo(today())
        flash("Exemplos fictícios carregados. Você já pode testar os empréstimos e as devoluções.", "success")
    except ValidationError as error:
        db.session.rollback()
        flash(next(iter(error.errors.values())), "error")
    return redirect(url_for("web.dashboard"))


@web.get("/equipamentos")
def equipment_list():
    query = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "all")
    category = request.args.get("category", "all")
    items = all_equipment()
    filtered = [item for item in items if (not query or query.casefold() in f"{item.name} {item.asset_code} {item.location}".casefold())
                and (status == "all" or item.status == status) and (category == "all" or item.category == category)]
    return render_template("equipment.html", page="equipment", items=filtered, total=len(items), q=query, status=status, category=category)


@web.route("/equipamentos/novo", methods=["GET", "POST"])
@web.route("/equipamentos/<int:record_id>/editar", methods=["GET", "POST"])
def equipment_form(record_id=None):
    item = get_record(Equipment, record_id) if record_id else None
    values = request.form.to_dict() if request.method == "POST" else ({field: getattr(item, field) for field in ("name", "asset_code", "category", "location", "condition", "notes")} if item else {"condition": "ready"})
    errors = {}
    if request.method == "POST":
        try:
            save_equipment(request.form, item)
            flash("Equipamento atualizado." if item else "Equipamento cadastrado. Pronto para circular!", "success")
            return redirect(url_for("web.equipment_list"))
        except ValidationError as error:
            db.session.rollback()
            errors = error.errors
    return render_template("equipment_form.html", page="equipment", item=item, values=values, errors=errors,
                           category_options=[(name, name) for name in CATEGORIES]), 422 if errors else 200


@web.get("/pessoas")
def people_list():
    query = request.args.get("q", "").strip()[:100]
    role = request.args.get("role", "all")
    people = all_people()
    filtered = [person for person in people if (not query or query.casefold() in f"{person.name} {person.registration} {person.email}".casefold()) and (role == "all" or role == person.role)]
    return render_template("people.html", page="people", people=filtered, total=len(people), q=query, role=role)


@web.route("/pessoas/nova", methods=["GET", "POST"])
@web.route("/pessoas/<int:record_id>/editar", methods=["GET", "POST"])
def person_form(record_id=None):
    person = get_record(Person, record_id) if record_id else None
    values = request.form.to_dict() if request.method == "POST" else ({"name": person.name, "registration": person.registration, "email": person.email, "role": person.role, "active": "true" if person.active else "false"} if person else {"role": "student", "active": "true"})
    errors = {}
    if request.method == "POST":
        try:
            save_person(request.form, person)
            flash("Cadastro atualizado." if person else "Pessoa cadastrada com sucesso.", "success")
            return redirect(url_for("web.people_list"))
        except ValidationError as error:
            db.session.rollback()
            errors = error.errors
    return render_template("person_form.html", page="people", person=person, values=values, errors=errors), 422 if errors else 200


def filtered_loans():
    query = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "all")
    loans = [loan for loan in all_loans() if (not query or query.casefold() in f"{loan.equipment.name} {loan.equipment.asset_code} {loan.person.name} {loan.person.registration}".casefold())
             and (status == "all" or (status == "open" and not loan.returned_on) or loan.status_on(today()) == status)]
    return loans, query, status


@web.get("/emprestimos")
def loan_list():
    loans, query, status = filtered_loans()
    return render_template("loans.html", page="loans", loans=loans, q=query, status=status)


@web.route("/emprestimos/novo", methods=["GET", "POST"])
def loan_form():
    errors = {}
    values = request.form.to_dict() if request.method == "POST" else {"equipment_id": request.args.get("equipment", ""), "due_on": (today() + timedelta(days=7)).isoformat()}
    if request.method == "POST":
        try:
            loan = create_loan(request.form, today())
            flash(f"Empréstimo #{loan.id:04d} registrado. A disponibilidade já foi atualizada.", "success")
            return redirect(url_for("web.loan_list"))
        except ValidationError as error:
            db.session.rollback()
            errors = error.errors
    available = [item for item in all_equipment() if item.status == "available"]
    people = [person for person in all_people() if person.active]
    return render_template("loan_form.html", page="loans", values=values, errors=errors, available=available, people=people,
                           equipment_options=[(item.id, f"{item.name} · {item.asset_code}") for item in available],
                           people_options=[(person.id, f"{person.name} · {person.registration}") for person in people]), 422 if errors else 200


@web.route("/emprestimos/<int:record_id>/devolver", methods=["GET", "POST"])
def loan_return(record_id):
    loan = get_record(Loan, record_id)
    errors = {}
    if loan.returned_on:
        flash("Este empréstimo já foi devolvido. O registro permanece no histórico.", "info")
        return redirect(url_for("web.loan_list"))
    if request.method == "POST":
        try:
            return_loan(loan, request.form, today())
            flash("Devolução registrada. O equipamento está disponível novamente.", "success")
            return redirect(url_for("web.loan_list"))
        except ValidationError as error:
            db.session.rollback()
            errors = error.errors
    return render_template("loan_return.html", page="loans", loan=loan, errors=errors, values=request.form), 422 if errors else 200


@web.get("/emprestimos/<int:record_id>")
def loan_detail(record_id):
    return render_template("loan_detail.html", page="loans", loan=get_record(Loan, record_id))


@web.get("/emprestimos/exportar.csv")
def export_loans():
    loans, _, _ = filtered_loans()
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Empréstimo", "Equipamento", "Patrimônio", "Responsável", "Identificação", "Retirada", "Devolução prevista", "Devolvido em", "Situação", "Observações", "Observações da devolução"])
    for loan in loans:
        row = [f"{loan.id:04d}", loan.equipment.name, loan.equipment.asset_code, loan.person.name, loan.person.registration, loan.borrowed_on.isoformat(), loan.due_on.isoformat(), loan.returned_on.isoformat() if loan.returned_on else "", STATUSES[loan.status_on(today())], loan.notes, loan.return_notes]
        # Evita interpretar conteúdo digitado como fórmula ao abrir em planilhas.
        writer.writerow(["'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value for value in row])
    return Response("\ufeff" + output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=circula-emprestimos.csv"})


@web.get("/sobre")
def about():
    return render_template("about.html", page="about")
