from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    app.config.from_object(Config)

    # Make sure the folders we write to actually exist
    os.makedirs(app.config["RESUME_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    from app.routes import main
    app.register_blueprint(main)

    from app.api_routes import api
    app.register_blueprint(api)

    with app.app_context():
        from app import models
        db.create_all()

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
