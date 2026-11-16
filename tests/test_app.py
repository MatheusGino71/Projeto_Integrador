"""Testes de integração com banco real temporário e cliente HTTP do Flask."""

import csv
import io
import os
import re
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from circula import create_app, today
from circula.models import Equipment, Loan, Person, db


class ApplicationTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "SECRET_KEY": "test-only-key", "WTF_CSRF_ENABLED": False, "ADMIN_PASSWORD": "", "CLOUD": False, "DEPLOYMENT_ERRORS": []})
        self.client = self.app.test_client()
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def equipment(self, **overrides):
        values = {"name": "Notebook de teste", "asset_code": "NT-TEST", "category": "Notebook", "location": "Laboratório 01", "condition": "ready", "notes": "Com carregador"}
        values.update(overrides)
        return self.client.post("/equipamentos/novo", data=values)

    def person(self, **overrides):
        values = {"name": "Pessoa de teste", "registration": "AL-TEST", "email": "teste@example.com", "role": "student", "active": "true"}
        values.update(overrides)
        return self.client.post("/pessoas/nova", data=values)

    def loan(self, **overrides):
        values = {"equipment_id": "1", "person_id": "1", "due_on": (today() + timedelta(days=3)).isoformat(), "notes": "Atividade acadêmica"}
        values.update(overrides)
        return self.client.post("/emprestimos/novo", data=values)

    def setup_records(self):
        self.assertEqual(self.equipment().status_code, 302)
        self.assertEqual(self.person().status_code, 302)

    def test_empty_pages_and_assets_render(self):
        for path in ("/", "/equipamentos", "/equipamentos/novo", "/pessoas", "/pessoas/nova", "/emprestimos", "/emprestimos/novo", "/sobre", "/styles.css", "/favicon.svg", "/health"):
            with self.subTest(path=path):
                with self.client.get(path) as response:
                    self.assertEqual(response.status_code, 200)
        self.assertIn("Explorar com dados fictícios", self.client.get("/").text)
        self.assertEqual(self.client.get("/inexistente").status_code, 404)

    def test_complete_loan_return_and_reloan_flow(self):
        self.setup_records()
        self.assertEqual(self.loan().status_code, 302)
        equipment = db.session.get(Equipment, 1)
        self.assertEqual(equipment.status, "borrowed")
        self.assertEqual(db.session.get(Person, 1).active_count, 1)
        self.assertIn("Notebook de teste", self.client.get("/emprestimos/1").text)
        self.assertEqual(self.client.get("/emprestimos/1/devolver").status_code, 200)
        self.assertEqual(self.client.post("/emprestimos/1/devolver", data={"return_notes": "Conferido, sem danos"}).status_code, 302)
        self.assertEqual(db.session.get(Equipment, 1).status, "available")
        self.assertEqual(db.session.get(Loan, 1).return_notes, "Conferido, sem danos")
        self.assertEqual(self.loan().status_code, 302)
        self.assertEqual(db.session.query(Loan).count(), 2)

    def test_duplicate_active_loan_is_rejected(self):
        self.setup_records()
        self.loan()
        response = self.loan()
        self.assertEqual(response.status_code, 422)
        self.assertIn("Selecione um equipamento disponível", response.text)
        self.assertEqual(db.session.query(Loan).count(), 1)

    def test_database_index_prevents_duplicate_even_without_http_validation(self):
        self.setup_records()
        self.loan()
        db.session.add(Loan(equipment_id=1, person_id=1, borrowed_on=today(), due_on=today()))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(db.session.query(Loan).count(), 1)

    def test_double_return_does_not_change_first_return(self):
        self.setup_records()
        self.loan()
        self.client.post("/emprestimos/1/devolver", data={"return_notes": "Primeira conferência"})
        self.client.post("/emprestimos/1/devolver", data={"return_notes": "Outra tentativa"})
        self.assertEqual(db.session.get(Loan, 1).return_notes, "Primeira conferência")

    def test_maintenance_and_inactive_people_cannot_borrow(self):
        self.equipment(condition="maintenance")
        self.person(active="false")
        response = self.loan()
        self.assertEqual(response.status_code, 422)
        self.assertIn("cadastro ativo", response.text)
        self.assertEqual(db.session.query(Loan).count(), 0)

    def test_past_dates_and_malformed_identifiers_are_rejected(self):
        self.setup_records()
        for values in ({"due_on": (today() - timedelta(days=1)).isoformat()}, {"due_on": "2026-02-30"}, {"due_on": "20261116"}, {"person_id": "abc"}, {"equipment_id": "999"}):
            with self.subTest(values=values):
                self.assertEqual(self.loan(**values).status_code, 422)
        self.assertEqual(db.session.query(Loan).count(), 0)

    def test_due_today_is_allowed_and_not_overdue(self):
        self.setup_records()
        self.assertEqual(self.loan(due_on=today().isoformat()).status_code, 302)
        loan = db.session.get(Loan, 1)
        self.assertEqual(loan.status_on(today()), "active")
        self.assertEqual(loan.status_on(today() + timedelta(days=1)), "overdue")
        self.assertEqual(loan.late_days(today() + timedelta(days=2)), 2)

    def test_returned_status_and_late_days_stop_at_return(self):
        self.setup_records()
        loan = Loan(equipment_id=1, person_id=1, borrowed_on=today() - timedelta(days=10), due_on=today() - timedelta(days=5), returned_on=today() - timedelta(days=3))
        db.session.add(loan)
        db.session.commit()
        self.assertEqual(loan.status_on(today()), "returned")
        self.assertEqual(loan.late_days(today() + timedelta(days=100)), 2)

    def test_duplicate_codes_and_invalid_fields(self):
        self.setup_records()
        self.assertEqual(self.equipment(asset_code="nt-test").status_code, 422)
        self.assertEqual(self.person(registration="al-test").status_code, 422)
        self.assertEqual(self.equipment(asset_code="NT-2", name=" ").status_code, 422)
        self.assertEqual(self.person(registration="AL-2", email="invalido").status_code, 422)
        self.assertEqual(self.equipment(asset_code="NT-2", category="categoria inválida").status_code, 422)
        self.assertEqual(self.equipment(asset_code="NT-2", notes="a" * 501).status_code, 422)
        self.assertEqual(db.session.query(Equipment).count(), 1)
        self.assertEqual(db.session.query(Person).count(), 1)

    def test_edits_and_status_change_with_loan_pending(self):
        self.setup_records()
        equipment_data = {"name": "Nome atualizado", "asset_code": "NT-TEST", "category": "Notebook", "location": "Laboratório 02", "condition": "ready"}
        self.assertEqual(self.client.post("/equipamentos/1/editar", data=equipment_data).status_code, 302)
        self.assertEqual(db.session.get(Equipment, 1).location, "Laboratório 02")
        self.loan()
        equipment_data["condition"] = "retired"
        self.assertEqual(self.client.post("/equipamentos/1/editar", data=equipment_data).status_code, 422)
        person_data = {"name": "Pessoa de teste", "registration": "AL-TEST", "email": "teste@example.com", "role": "student", "active": "false"}
        self.assertEqual(self.client.post("/pessoas/1/editar", data=person_data).status_code, 422)
        self.client.post("/emprestimos/1/devolver", data={})
        self.assertEqual(self.client.post("/equipamentos/1/editar", data=equipment_data).status_code, 302)
        self.assertEqual(self.client.post("/pessoas/1/editar", data=person_data).status_code, 302)
        self.assertEqual(db.session.get(Equipment, 1).status, "retired")

    def test_demo_is_explicit_and_cannot_be_loaded_twice(self):
        self.assertEqual(db.session.query(Equipment).count(), 0)
        self.client.post("/demonstracao")
        self.client.post("/demonstracao")
        self.assertEqual(db.session.query(Equipment).count(), 8)
        self.assertEqual(db.session.query(Person).count(), 5)
        self.assertEqual(db.session.query(Loan).count(), 4)
        for path in ("/", "/equipamentos", "/pessoas", "/emprestimos", "/emprestimos/1", "/emprestimos/4", "/emprestimos/novo", "/equipamentos/1/editar", "/pessoas/1/editar"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_filters_and_export_use_same_records(self):
        self.client.post("/demonstracao")
        response = self.client.get("/emprestimos?status=overdue")
        self.assertIn("Ana Oliveira", response.text)
        self.assertNotIn("Mariana Costa", response.text)
        response = self.client.get("/equipamentos?q=NT-002&status=available")
        self.assertIn("Lenovo", response.text)
        self.assertNotIn("Dell Latitude", response.text)
        response = self.client.get("/emprestimos/exportar.csv?status=overdue")
        rows = list(csv.reader(io.StringIO(response.data.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][3], "Ana Oliveira")

    def test_untrusted_content_is_escaped_and_csv_formulas_are_neutralized(self):
        self.setup_records()
        self.loan(notes="<script>alert(1)</script>\n=teste")
        response = self.client.get("/emprestimos/1")
        self.assertNotIn("<script>alert(1)</script>", response.text)
        self.assertIn("&lt;script&gt;", response.text)
        equipment = db.session.get(Equipment, 1)
        equipment.name = "=HYPERLINK(1)"
        db.session.commit()
        self.assertIn("'=HYPERLINK(1)", self.client.get("/emprestimos/exportar.csv").text)

    def test_foreign_keys_are_enforced(self):
        db.session.add(Loan(equipment_id=999, person_id=999, borrowed_on=today(), due_on=today()))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_csrf_is_required_on_real_forms(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.post("/demonstracao").status_code, 400)
        html = self.client.get("/").text
        token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        self.assertEqual(self.client.post("/demonstracao", data={"csrf_token": token}).status_code, 302)
        self.assertEqual(db.session.query(Equipment).count(), 8)

    def test_password_protects_pages_and_writes_and_logout(self):
        self.app.config["ADMIN_PASSWORD"] = "test-password"
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.post("/demonstracao").status_code, 302)
        self.assertEqual(db.session.query(Equipment).count(), 0)
        self.assertIn("Senha incorreta", self.client.post("/entrar", data={"password": "wrong"}).text)
        self.assertEqual(self.client.post("/entrar", data={"password": "test-password"}).status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.client.post("/sair")
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_missing_cloud_configuration_has_clear_setup_page(self):
        self.app.config["DEPLOYMENT_ERRORS"] = ["DATABASE_URL", "SECRET_KEY"]
        response = self.client.get("/")
        self.assertEqual(response.status_code, 503)
        self.assertIn("DATABASE_URL", response.text)

    def test_initialization_command_preserves_existing_records(self):
        self.setup_records()
        result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(db.session.query(Equipment).count(), 1)

    def test_postgresql_configuration_and_unique_index_compile_without_network(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DATABASE_URL": "postgres://user:dummy@example.invalid/circula?sslmode=require", "SECRET_KEY": "test-key", "ADMIN_PASSWORD": "test-password"}):
            cloud_app = create_app()
        self.assertEqual(cloud_app.config["DEPLOYMENT_ERRORS"], [])
        self.assertTrue(cloud_app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://"))
        self.assertTrue(cloud_app.config["SESSION_COOKIE_SECURE"])
        index = next(index for index in Loan.__table__.indexes if index.name == "one_active_loan_per_equipment")
        sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        self.assertIn("UNIQUE INDEX", sql)
        self.assertIn("WHERE returned_on IS NULL", sql)
        with cloud_app.app_context():
            db.engine.dispose()

    def test_neon_postgres_url_is_accepted_when_database_url_is_empty(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DATABASE_URL": "", "POSTGRES_URL": "postgresql://user:dummy@example.invalid/circula?sslmode=require", "SECRET_KEY": "test-key", "ADMIN_PASSWORD": "test-password"}):
            cloud_app = create_app()
        self.assertEqual(cloud_app.config["DEPLOYMENT_ERRORS"], [])
        self.assertTrue(cloud_app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://"))
        with cloud_app.app_context():
            db.engine.dispose()

    def test_database_url_takes_precedence_over_neon_alias(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DATABASE_URL": "postgresql://user:dummy@preferred.invalid/circula", "POSTGRES_URL": "postgresql://user:dummy@fallback.invalid/circula", "SECRET_KEY": "test-key", "ADMIN_PASSWORD": "test-password"}):
            cloud_app = create_app()
        self.assertIn("preferred.invalid", cloud_app.config["SQLALCHEMY_DATABASE_URI"])
        self.assertNotIn("fallback.invalid", cloud_app.config["SQLALCHEMY_DATABASE_URI"])
        with cloud_app.app_context():
            db.engine.dispose()


class PersistenceTest(unittest.TestCase):
    def test_data_survives_a_new_application_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "persistence.db"
            config = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}", "WTF_CSRF_ENABLED": False, "ADMIN_PASSWORD": "", "CLOUD": False, "DEPLOYMENT_ERRORS": []}
            first = create_app(config)
            first.test_client().post("/pessoas/nova", data={"name": "Persistência", "registration": "P-01", "email": "persistencia@example.com", "role": "staff", "active": "true"})
            with first.app_context():
                db.session.remove()
                db.engine.dispose()
            second = create_app(config)
            with second.app_context():
                self.assertEqual(db.session.scalar(select(Person)).name, "Persistência")
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
