import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize login manager
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "barterhub-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/barterhub")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "connect_args": {"client_encoding": "utf8"}
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = "static/uploads"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

    # Apply proxy fix for proper URL generation
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
    login_manager.login_message_category = 'info'

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    # Register blueprints
    from routes import main, auth, products, chat, transactions, admin, init_db
    
    # Import all models untuk database initialization
    from models import User, Category, Product, ProductImage, ChatRoom, ChatMessage, Transaction, TransactionOffer, Report, Review, Wishlist

    # Create database tables after importing models
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        logging.info("Database tables created")
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(products, url_prefix='/products')
    app.register_blueprint(chat, url_prefix='/chat')
    app.register_blueprint(transactions, url_prefix='/transactions')
    app.register_blueprint(admin, url_prefix='/admin')

    # Initialize default data within the app context
    with app.app_context():
        init_db()

    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Assuming create_admin_user is defined elsewhere and handles admin user creation
        # For this example, we'll assume it exists and is called correctly.
        # If create_admin_user is not defined, this part will cause an error.
        # from utils import create_admin_user # Uncomment if create_admin_user is in utils
        # create_admin_user() 

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)