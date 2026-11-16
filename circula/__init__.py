"""Configuração da aplicação. Nenhum serviço Node ou Java é necessário."""

import hmac
import os
import secrets
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import click
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from circula.models import db

csrf = CSRFProtect()
TIMEZONE = ZoneInfo("America/Sao_Paulo")


def today():
    return datetime.now(TIMEZONE).date()


@event.listens_for(Engine, "connect")
def configure_sqlite(connection, _record):
    if connection.__class__.__module__ == "sqlite3":
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, template_folder="../templates", static_folder="../public", static_url_path="")
    cloud = os.getenv("VERCEL") == "1"
    database_url = (os.getenv("DATABASE_URL", "").strip() or os.getenv("POSTGRES_URL", "").strip())
    if database_url.startswith(("postgres://", "postgresql://")):
        database_url = "postgresql+psycopg://" + database_url.split("://", 1)[1]
    missing = [name for name in ("SECRET_KEY", "ADMIN_PASSWORD") if not os.getenv(name, "").strip()] if cloud else []
    if cloud and not database_url:
        missing.insert(0, "DATABASE_URL ou POSTGRES_URL")
    if cloud and database_url and not database_url.startswith("postgresql+psycopg://"):
        missing.append("DATABASE_URL ou POSTGRES_URL deve ser uma conexão PostgreSQL")

    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=database_url or ("sqlite://" if cloud else "sqlite:///circula.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"poolclass": NullPool} if database_url.startswith("postgresql") else {},
        ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD", ""),
        DEPLOYMENT_ERRORS=missing,
        CLOUD=cloud,
        MAX_CONTENT_LENGTH=64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cloud,
        WTF_CSRF_TIME_LIMIT=3600,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["CLOUD"]:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    # Local: banco criado automaticamente. Nuvem: criação explícita pelo comando init-db.
    if not app.config["CLOUD"]:
        with app.app_context():
            db.create_all()

    @app.before_request
    def check_access():
        if request.endpoint == "static":
            return None
        if app.config["DEPLOYMENT_ERRORS"]:
            return render_template("setup.html", missing=app.config["DEPLOYMENT_ERRORS"]), 503
        if request.endpoint in ("login", "health"):
            return None
        if app.config["ADMIN_PASSWORD"] and not session.get("authenticated"):
            return redirect(url_for("login"))

    @app.route("/entrar", methods=["GET", "POST"])
    def login():
        error = None
        if not app.config["ADMIN_PASSWORD"]:
            return redirect(url_for("web.dashboard"))
        if request.method == "POST":
            if hmac.compare_digest(request.form.get("password", "").encode(), app.config["ADMIN_PASSWORD"].encode()):
                session.clear()
                session["authenticated"] = True
                return redirect(url_for("web.dashboard"))
            error = "Senha incorreta. Confira a senha de acesso e tente novamente."
        return render_template("login.html", error=error)

    @app.post("/sair")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/health")
    def health():
        # Liveness público; o funcionamento do banco é validado pelas páginas e pelo init-db.
        return {"status": "ok", "app": "circula"}

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return render_template("error.html", title="Este formulário expirou", message="Reabra a página e envie o formulário novamente.", code=400), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", title="Página não encontrada", message="O endereço não existe ou o registro não está mais disponível.", code=404), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("error.html", title="Não foi possível concluir", message="Tente novamente. Se o problema continuar, confira a conexão do banco e a inicialização descrita no README.", code=500), 500

    @app.context_processor
    def template_context():
        return {"today": today(), "password_enabled": bool(app.config["ADMIN_PASSWORD"])}

    @app.template_filter("brdate")
    def brdate(value):
        return value.strftime("%d/%m/%Y") if value else "—"

    @app.cli.command("init-db")
    def init_db():
        """Cria tabelas e índices sem apagar os registros existentes."""
        if app.config["DEPLOYMENT_ERRORS"]:
            raise click.ClickException("Configure as variáveis obrigatórias antes de inicializar.")
        db.create_all()
        click.echo("Banco inicializado. Nenhum registro existente foi apagado.")

    from circula.routes import web
    app.register_blueprint(web)
    return app
