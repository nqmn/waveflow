"""
Flask application factory for RISNet web interface
"""

from flask import Flask


def create_app(net=None, controller=None, state_manager=None):
    """Create and configure Flask app instance

    Args:
        net: RISNetwork instance
        controller: RISController instance
        state_manager: WebStateManager instance for persistence
    """
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False

    # Register blueprints
    from app.api import bp as api_bp
    from app.web import bp as web_bp

    # Set global network and controller references
    if net and controller:
        from app.api.bp import set_network
        set_network(net, controller, state_manager)

    app.register_blueprint(api_bp.bp)
    app.register_blueprint(web_bp.bp)

    return app
