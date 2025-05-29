"""
Routes package initialization.
This module registers all routes with the Flask application.
"""

def register_routes(app):
    """Register all route blueprints with the application
    
    Args:
        app: Flask application instance
    """
    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.journal import journal_bp
    from routes.gallery import gallery_bp
    from routes.api import api_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(api_bp, url_prefix='/api')