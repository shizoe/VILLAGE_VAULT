import secrets
from datetime import timedelta

import flask
from flask_login import LoginManager, current_user
from mail import mail
from main import main as main_blueprint
from auth import auth as auth_blueprint
from flask import Flask, session, g
from flask_security import Security, SQLAlchemyUserDatastore

from database import init_db, db_session
from models import User
from security import security, user_datastore

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
# app.config['SECRET_KEY'] = '72beyg23jnij2jhhweju723u9'
app.config['SECURITY_PASSWORD_SALT'] = '+G*wW}uSGIr>Mi&'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'live.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'api'
app.config['MAIL_PASSWORD'] = 'b4ff14cfeca871006f233cb4f091cd27'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.register_blueprint(auth_blueprint)
app.register_blueprint(main_blueprint)
# Configure Flask-Security
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
security.init_app(app, user_datastore)
mail.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'auth.index'
login_manager.init_app(app)
init_db()


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return user_datastore.get_user(user_id)


@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=5)
    flask.session.modified = True
    g.user = current_user


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == '__main__':
    app.run(debug=True)
