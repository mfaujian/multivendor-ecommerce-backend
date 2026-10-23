import logging
from flask import jsonify
from marshmallow.exceptions import ValidationError

def register_jwt_handlers(jwt):
    """Make every authentication failure use the same {"error": ..., "code": ...} JSON shape."""

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Authentication required. Please log in.", "code": "token_missing"}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": "Invalid session. Please log in again.", "code": "token_invalid"}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"error": "Your session has expired. Please log in again.", "code": "token_expired"}), 401

def register_error_handlers(app):
    
    @app.errorhandler(ValidationError)
    def handle_marshmallow_validation(error):
        messages = error.messages if isinstance(error.messages, dict) else {"_schema": error.messages}
        flat_errors = {
            field: (msgs[0] if isinstance(msgs, list) and msgs else msgs)
            for field, msgs in messages.items()
        }
        return jsonify({
            "error": "Validation failed",
            "details": flat_errors
        }), 400

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": str(error.description)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": str(error.description)}), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        logging.error("Unhandled exception", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": "Something went wrong on the server."}), 500
