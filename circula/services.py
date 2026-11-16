"""Validações e regras do empréstimo, independentes dos templates."""

import re
from datetime import date, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from circula.models import Equipment, Loan, Person, db

CATEGORIES = ("Notebook", "Projetor", "Tablet", "Câmera", "Áudio", "Outros")
CONDITIONS = {"ready": "Apto para empréstimo", "maintenance": "Em manutenção", "retired": "Desativado"}
ROLES = {"student": "Aluno(a)", "teacher": "Professor(a)", "staff": "Colaborador(a)"}
STATUSES = {"available": "Disponível", "borrowed": "Emprestado", "maintenance": "Manutenção", "retired": "Desativado", "active": "Em andamento", "overdue": "Em atraso", "returned": "Devolvido"}


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors


def text_field(form, field, label, maximum, errors, required=True):
    value = form.get(field, "").strip()
    if required and not value:
        errors[field] = f"Informe {label}."
    elif len(value) > maximum:
        errors[field] = f"Use no máximo {maximum} caracteres."
    return value


def save_equipment(form, equipment=None):
    errors = {}
    values = {
        "name": text_field(form, "name", "o nome do equipamento", 100, errors),
        "asset_code": text_field(form, "asset_code", "o patrimônio", 30, errors).upper(),
        "location": text_field(form, "location", "o local de guarda", 100, errors),
        "notes": text_field(form, "notes", "as observações", 500, errors, False),
        "category": form.get("category", ""),
        "condition": form.get("condition", "ready"),
    }
    if values["category"] not in CATEGORIES:
        errors["category"] = "Selecione uma categoria válida."
    if values["condition"] not in CONDITIONS:
        errors["condition"] = "Selecione uma situação válida."
    if equipment:
        # Serializa a alteração com novos empréstimos no PostgreSQL.
        equipment = db.session.scalar(select(Equipment).where(Equipment.id == equipment.id).with_for_update())
        if values["condition"] != "ready" and any(loan.returned_on is None for loan in equipment.loans):
            errors["condition"] = "Registre a devolução antes de alterar a situação."
    if errors:
        raise ValidationError(errors)
    equipment = equipment or Equipment()
    for key, value in values.items():
        setattr(equipment, key, value)
    db.session.add(equipment)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError({"asset_code": "Este patrimônio já está cadastrado. Use um código único por equipamento."})
    return equipment


def save_person(form, person=None):
    errors = {}
    values = {
        "name": text_field(form, "name", "o nome completo", 100, errors),
        "registration": text_field(form, "registration", "a matrícula ou identificação", 30, errors).upper(),
        "email": text_field(form, "email", "o e-mail", 120, errors).lower(),
        "role": form.get("role", ""),
        "active": form.get("active", "true") == "true",
    }
    if values["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]):
        errors["email"] = "Informe um e-mail válido, como nome@exemplo.com."
    if values["role"] not in ROLES:
        errors["role"] = "Selecione um vínculo válido."
    if form.get("active", "true") not in ("true", "false"):
        errors["active"] = "Selecione uma situação válida."
    if person:
        person = db.session.scalar(select(Person).where(Person.id == person.id).with_for_update())
        if not values["active"] and person.active_count:
            errors["active"] = "Conclua os empréstimos desta pessoa antes de desativá-la."
    if errors:
        raise ValidationError(errors)
    person = person or Person()
    for key, value in values.items():
        setattr(person, key, value)
    db.session.add(person)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError({"registration": "Esta identificação já está cadastrada."})
    return person


def parse_id(form, field, errors):
    try:
        value = int(form.get(field, ""))
        if value < 1:
            raise ValueError
        return value
    except (ValueError, TypeError):
        errors[field] = "Selecione um registro válido."


def create_loan(form, today):
    errors = {}
    equipment_id = parse_id(form, "equipment_id", errors)
    person_id = parse_id(form, "person_id", errors)
    notes = text_field(form, "notes", "as observações", 500, errors, False)
    due_on = None
    try:
        raw_date = form.get("due_on", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            raise ValueError
        due_on = date.fromisoformat(raw_date)
        if due_on < today:
            errors["due_on"] = "A devolução prevista deve ser hoje ou uma data futura."
    except ValueError:
        errors["due_on"] = "Informe uma data de devolução válida."

    equipment = db.session.scalar(select(Equipment).where(Equipment.id == equipment_id).with_for_update()) if equipment_id else None
    person = db.session.scalar(select(Person).where(Person.id == person_id).with_for_update()) if person_id else None
    if not equipment or equipment.status != "available":
        errors["equipment_id"] = "Selecione um equipamento disponível. Ele pode ter sido emprestado em outra sessão."
    if not person or not person.active:
        errors["person_id"] = "Selecione uma pessoa com cadastro ativo."
    if errors:
        raise ValidationError(errors)
    loan = Loan(equipment_id=equipment.id, person_id=person.id, borrowed_on=today, due_on=due_on, notes=notes)
    db.session.add(loan)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError({"equipment_id": "Este equipamento acabou de ser emprestado. Escolha outro disponível."})
    return loan


def return_loan(loan, form, today):
    errors = {}
    notes = text_field(form, "return_notes", "as observações", 500, errors, False)
    if errors:
        raise ValidationError(errors)
    result = db.session.execute(
        update(Loan).where(Loan.id == loan.id, Loan.returned_on.is_(None)).values(returned_on=today, return_notes=notes)
    )
    if result.rowcount != 1:
        db.session.rollback()
        raise ValidationError({"return_notes": "A devolução deste empréstimo já foi registrada."})
    db.session.commit()


def load_demo(today):
    if any(db.session.scalar(select(db.func.count()).select_from(model)) for model in (Equipment, Person, Loan)):
        raise ValidationError({"demo": "Os exemplos só podem ser carregados em um banco vazio."})
    equipment = [
        Equipment(name="Notebook Dell Latitude", asset_code="NT-001", category="Notebook", location="Laboratório 01", condition="ready"),
        Equipment(name="Notebook Lenovo ThinkPad", asset_code="NT-002", category="Notebook", location="Laboratório 01", condition="ready"),
        Equipment(name="Projetor Epson PowerLite", asset_code="PJ-001", category="Projetor", location="Sala de recursos", condition="ready"),
        Equipment(name="Projetor BenQ", asset_code="PJ-002", category="Projetor", location="Sala de recursos", condition="maintenance", notes="Aguardando troca da lâmpada."),
        Equipment(name="Tablet Samsung Galaxy", asset_code="TB-001", category="Tablet", location="Laboratório 02", condition="ready"),
        Equipment(name="Câmera Canon EOS", asset_code="CM-001", category="Câmera", location="Estúdio audiovisual", condition="ready"),
        Equipment(name="Kit de microfones", asset_code="AU-001", category="Áudio", location="Estúdio audiovisual", condition="ready"),
        Equipment(name="Notebook Acer Aspire", asset_code="NT-003", category="Notebook", location="Laboratório 02", condition="ready"),
    ]
    people = [
        Person(name="Ana Oliveira", registration="AL-001", email="ana@example.com", role="student"),
        Person(name="Lucas Santos", registration="AL-002", email="lucas@example.com", role="student"),
        Person(name="Mariana Costa", registration="PR-001", email="mariana@example.com", role="teacher"),
        Person(name="Pedro Almeida", registration="AL-003", email="pedro@example.com", role="student"),
        Person(name="Camila Rocha", registration="CO-001", email="camila@example.com", role="staff"),
    ]
    try:
        db.session.add_all(equipment + people)
        db.session.flush()
        db.session.add_all([
            Loan(equipment=equipment[0], person=people[0], borrowed_on=today - timedelta(days=5), due_on=today - timedelta(days=2), notes="Projeto de robótica. Fonte e bolsa incluídas."),
            Loan(equipment=equipment[2], person=people[2], borrowed_on=today - timedelta(days=1), due_on=today + timedelta(days=2), notes="Apresentação em sala de aula."),
            Loan(equipment=equipment[4], person=people[1], borrowed_on=today, due_on=today + timedelta(days=7)),
            Loan(equipment=equipment[5], person=people[3], borrowed_on=today - timedelta(days=12), due_on=today - timedelta(days=8), returned_on=today - timedelta(days=9), return_notes="Conferido e devolvido em boas condições."),
        ])
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError({"demo": "Os exemplos já foram carregados por outra sessão."})
