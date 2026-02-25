from flask import Flask
from .extensions import db, migrate
from .routes import api

def create_app():
    app = Flask(__name__)

    # V1 config (SQLite locally)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jacktrack.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(api)

    return app