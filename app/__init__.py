import os
import logging
from logging.handlers import TimedRotatingFileHandler

from flask import Flask, jsonify, redirect
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from werkzeug.middleware.proxy_fix import ProxyFix
from app.middleware.errors import register_error_handlers, register_jwt_handlers
from flasgger import Swagger
from app.config import Config
from app.utils import db, limiter
from app.models import Users, Sellers, Categories, Products, PriceTiers, Addresses, Carts, cart_items, Orders, OrderItems
from app.controllers import auth_bp, users_bp, category_bp, seller_bp, product_bp, cart_bp, order_bp, address_bp

def setup_logging(app):
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    if os.getenv('IS_PRODUCTION', 'false').lower() != 'true':
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = TimedRotatingFileHandler('logs/app.log', when='midnight', interval=1, backupCount=7)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def create_app(test_config=None):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Behind Railway's proxy the real client IP is in X-Forwarded-For (needed for rate limiting)
    if app.config.get('TRUST_PROXY_HOPS', 0) > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=app.config['TRUST_PROXY_HOPS'])

    origins = app.config.get('CORS_ORIGINS', '*').strip()
    CORS(app, origins=[o.strip() for o in origins.split(',') if o.strip()] if origins != '*' else '*')

    # Register Flask extensions
    setup_logging(app)
    logging.info("Initializing the Flask application...")
    db.init_app(app)
    limiter.init_app(app)
    Migrate(app, db)
    jwt = JWTManager(app)
    register_jwt_handlers(jwt)
    
    swagger_template = {
        "info": {
            "title": "Multivendor E-Commerce API",
            "description": "A multi-tenant marketplace backend with split-order checkout, role-based access control, and layered service architecture.",
            "version": "1.0.0"
        },

        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Type 'Bearer' followed by 'space', then input your JWT Token.\n\nExample: 'Bearer eyJhbGci...'"
            }
        }
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/swagger-ui/"
    }

    Swagger(app, template=swagger_template, config=swagger_config)

    @app.route('/apidocs')
    @app.route('/apidocs/')
    @app.route('/swagger-ui')
    def redirect_to_swagger():
        return redirect('/swagger-ui/')

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(address_bp)

    # Endpoint routes for checking database connection
    @app.route('/health')
    def index():
        try:
            db.session.execute(db.text('SELECT 1'))
            logging.info("Database connection successful.")
            return jsonify({"status": "healthy", "database": "connected"}), 200
        except SQLAlchemyError as e:
            logging.error(f"Database connection failed: {e}")
            return jsonify({"status": "unhealthy", "database": "disconnected"}), 503
        except Exception as e:
            logging.error(f"General error: {e}")
            return jsonify({"status": "unhealthy", "database": "error"}), 503
        finally:
            db.session.close()

    register_error_handlers(app)

    return app