# Create the Flask-Security app and datastore
from flask_security import Security, SQLAlchemyUserDatastore

from database import db_session
from models import User, Role

security = Security()
user_datastore = SQLAlchemyUserDatastore(db_session, User, Role)
