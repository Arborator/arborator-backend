from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api

from flask_login import LoginManager, current_user

from app.klang.config import KlangConfig

db = SQLAlchemy()
login_manager = LoginManager()


klang_config = KlangConfig()


def create_app(env=None):
    from app.config import config_by_name
    from app.routes import register_routes

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_by_name[env or "test"])
    klang_config.set_path(env or "test")
    api = Api(
        app,
        title="Arborator-Grew Backend",
        version="0.1.0",
        doc="/api/doc",
        endpoint="/api",
        base_url="/api",
    )

    register_routes(api, app)
    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint, url_prefix="/")

    @app.route("/health")
    def health():
        return jsonify("healthy")

    return app
