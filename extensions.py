from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth

db           = SQLAlchemy()
login_manager = LoginManager()
bcrypt       = Bcrypt()
csrf         = CSRFProtect()
oauth        = OAuth()

login_manager.login_view          = "views.login"
login_manager.login_message       = "Please log in to access this page."
login_manager.login_message_category = "info"
