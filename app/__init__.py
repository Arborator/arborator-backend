from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api

db = SQLAlchemy()


def create_app(env=None):
    print("Environment :", env)
    from app.config import config_by_name
    from app.routes import register_routes

    app = Flask(__name__n, instance_relative_config=False)
    app.config.from_object(config_by_name[env or "test"])
    print("Config : ", config_by_name[env or "test"])
    api = Api(app, title="Flaskerific API", version="0.1.0")

    register_routes(api, app)
    db.init_app(app)

    @app.route("/health")
    def health():
        return jsonify("healthy")

    return app
