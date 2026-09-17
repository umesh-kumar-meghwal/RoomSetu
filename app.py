"""
app.py
Main entry point and application factory for RoomSetu.
"""
from flask import Flask, render_template, session
from config import Config

# Blueprint imports
from routes.auth import auth_bp
from routes.student import student_bp
from routes.landlord import landlord_bp
from routes.admin import admin_bp
from routes.properties import properties_bp
from routes.inquiries import inquiries_bp
from routes.favorites import favorites_bp
from routes.reports import reports_bp
from routes.api import api_bp


def create_app(config_class=Config) -> Flask:
    """Configures and returns the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(landlord_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(properties_bp)
    app.register_blueprint(inquiries_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)

    # Context Processor for Jinja2 Templates
    # Context Processor for Jinja2 Templates
    @app.context_processor
    def inject_auth_state():
        """Provides session, auth state, and Supabase config to all Jinja2 templates."""
        return {
            "supabase_url": Config.SUPABASE_URL.rstrip('/'), # <-- YEH NAYA ADD KAREIN
            "current_user": {
                "is_authenticated": bool(session.get("user_id")),
                "id": session.get("user_id"),
                "email": session.get("email"),
                "full_name": session.get("full_name"),
                "role": session.get("role"),
                "account_status": session.get("account_status")
            }
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("errors/500.html"), 500

    # Index route defaults to the properties exploration view
    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("properties_bp.browse"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)