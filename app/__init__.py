"""
Flask application factory and initialization.
"""

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_mail import Mail
# from flask_babel import Babel
import os

from app.models import db, User

mail = Mail()
# babel = Babel()


def create_app(config_name='development'):
    """Create and configure Flask application."""
    
    app = Flask(__name__)
    
    # Load configuration
    if config_name == 'production':
        from config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Create upload folder
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    # babel.init_app(app)
    migrate = Migrate(app, db)

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в аккаунт.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for session management."""
        return User.query.get(int(user_id))
    
    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Register blueprints
    from app.routes import auth_bp, main_bp, product_bp, profile_bp, admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register context processors
    register_context_processors(app)

    # # Register Babel locale selector
    # @babel.localeselector
    # def get_locale():
    #     # For now, default to Russian, but can be extended to detect from user preference
    #     return 'ru'

    return app


def register_error_handlers(app):
    """Register error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def server_error(error):
        from flask import render_template
        if db.session.is_active:
            db.session.rollback()
        return render_template('errors/500.html'), 500


def register_context_processors(app):
    """Register context processors."""
    
    @app.context_processor
    def inject_categories():
        from app.models import Category
        categories = Category.query.all()
        return dict(categories=categories)
