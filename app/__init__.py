from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api

from flask_login import LoginManager
from flask_caching import Cache
from flask_migrate import Migrate
from flask_mail import Mail

from app.klang.config import KlangConfig
from app.utils.grew_config import GrewConfig
from app.utils.arborator_parser_config import ParserConfig

cache = Cache()
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

klang_config = KlangConfig()
grew_config = GrewConfig()
parser_config = ParserConfig()

def create_app(env=None):
    from app.config import config_by_name
    from app.routes import register_routes
    app_env = env or "test"
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_by_name[app_env])
    klang_config.set_path(app_env)
    grew_config.set_url(app_env)
    parser_config.set_url(app_env)

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
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    mail.init_app(app)

    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint, url_prefix="/")

    @app.route("/health")
    def health():
        return jsonify("healthy")

    ## service for mp3 file, which will be taken from app/public folder
    @app.route('/media/<path:path>')
    def media(path):
        return send_from_directory('public', path)

    return app
