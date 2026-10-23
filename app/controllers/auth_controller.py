from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app.schemas import LoginSchema, UserRegisterSchema, UserResponseSchema
from app.services import auth_service, user_service
from app.utils import limiter

# Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
users_bp = Blueprint('users', __name__, url_prefix='/users')

# Schema
login_schema = LoginSchema()
register_schema = UserRegisterSchema()
user_response_schema = UserResponseSchema()


# =========================================================================
# USER MODULE (BLUEPRINT: users_bp | PREFIX: /users)
# =========================================================================

@users_bp.route('', methods = ['POST'])
@limiter.limit(lambda: current_app.config["RATELIMIT_REGISTER"])
def register_user():
    """Register a new user
    ---
    tags:
      - Users
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
            - full_name
          properties:
            email:
              type: string
              example: "johndoe@example.com"
            password:
              type: string
              example: "securepassword123"
            full_name:
              type: string
              example: "John Doe"
            avatar_url:
              type: string
              example: "https://example.com/avatar.jpg"
    responses:
      201:
        description: User registered successfully
      400:
        description: Bad request (Missing required fields or validation error)
      409:
        description: Email already registered
      500:
        description: Internal server error
    """
    data = request.get_json(silent=True) or {}
    validated_data = register_schema.load(data)

    user, error = user_service.register_user(validated_data)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]

    return jsonify({
        "message": "User registration successful",
        "user": user_response_schema.dump(user)
    }), 201


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_by_id(user_id):
    """Get user profile by ID
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: The user ID
    responses:
      200:
        description: User profile details
      401:
        description: Unauthorized (Invalid or missing token)
      403:
        description: Forbidden (Not the owner and not an admin)
      404:
        description: User not found
      500:
        description: Internal server error
    """
    
    requester_id = int(get_jwt_identity())
    requester_role= get_jwt().get('role')

    user, error = user_service.get_user_by_id(user_id, requester_id, requester_role)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({
        "message": "User data successfully retrieved!",
        "user": user_response_schema.dump(user)
    }), 200


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete user account
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: The user ID
    responses:
      200:
        description: Account successfully deactivated
      401:
        description: Unauthorized (Invalid or missing token)
      403:
        description: Forbidden (Not the owner and not an admin)
      404:
        description: User not found
      500:
        description: Internal server error
    """

    requester_id = int(get_jwt_identity())
    requester_role = get_jwt().get('role')

    _, error = user_service.delete_user(user_id, requester_id, requester_role)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({
        "message": f"User with ID {user_id} and its associated data successfully deactivated"
        }), 200


@users_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user profile
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Current user profile details
      401:
        description: Unauthorized (Missing or invalid token)
      404:
        description: User not found
      500:
        description: Internal server error
    """
    user_id = int(get_jwt_identity())
    user, error = user_service.get_current_user(user_id)

    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({
        "message": "Current user data successfully retrieved!",
        "user": user_response_schema.dump(user)
    }), 200

# =========================================================================
# AUTH MODULE (BLUEPRINT: auth_bp | PREFIX: /auth)
# =========================================================================

@auth_bp.route('/login', methods=['POST'])
@limiter.limit(lambda: current_app.config["RATELIMIT_LOGIN"])
def login():
    """Login and generate JWT Token
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: "johndoe@example.com"
            password:
              type: string
              example: "securepassword123"
    responses:
      200:
        description: Login successful, returns JWT token
      400:
        description: Missing email or password
      401:
        description: Invalid credentials
      500:
        description: Internal server error
    """
    data = request.get_json(silent=True) or {}
    validated_data = login_schema.load(data)

    result, error = auth_service.authenticate_user(validated_data['email'], validated_data['password'])
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({
        "message": result["message"],
        "token": result["token"],
        "user": user_response_schema.dump(result["user"])
    }), 200