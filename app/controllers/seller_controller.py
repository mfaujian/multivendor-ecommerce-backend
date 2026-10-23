from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.middleware.auth import seller_required
from app.schemas import SellerCreateSchema, SellerUpdateSchema, SellerResponseSchema
from app.services import seller_service 

# Blueprint
seller_bp = Blueprint('seller', __name__, url_prefix='/sellers')

# Schemas
create_schema = SellerCreateSchema()
update_schema = SellerUpdateSchema()
response_schema = SellerResponseSchema()

# =========================================================================
# SELLER MODULE (BLUEPRINT: seller_bp | PREFIX: /sellers)
# =========================================================================

@seller_bp.route('', methods=['POST'])
@jwt_required()
def create_store():
    """Register a store profile and upgrade account role
    ---
    tags:
      - Sellers
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - store_name
          properties:
            store_name:
              type: string
              example: "Toko Angkasa Elektrik"
            store_description:
              type: string
              example: "Electrical component distributor"
            avatar_url:
              type: string
              example: "https://example.com/logo.png"
    responses:
      201:
        description: Store profile successfully created
      400:
        description: Validation error, missing store_name or profile already exists
      401:
        description: Unauthorized (Invalid or missing token)
      409:
        description: Store name is already taken by another user
      500:
        description: Internal database error
    """
    data = request.get_json(silent=True) or {}
    validated_data = create_schema.load(data)
    user_id =int(get_jwt_identity())

    store, error = seller_service.create_store(user_id, validated_data)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({
        "message": "Store profile successfully created!",
        "store": response_schema.dump(store)
    }), 201        


@seller_bp.route('', methods=['GET'])
def list_stores():
    """List all active stores (suppliers)
    ---
    tags:
      - Sellers
    responses:
      200:
        description: Active stores, sorted by name
    """
    stores = seller_service.list_active_sellers()
    return jsonify({
        "message": "Stores retrieved successfully",
        "stores": SellerResponseSchema(many=True).dump(stores)
    }), 200


@seller_bp.route('/<int:seller_id>', methods=['GET'])
def get_store_profile(seller_id):
    """View public store profile
    ---
    tags:
      - Sellers
    parameters:
      - in: path
        name: seller_id
        type: integer
        required: true
        description: The ID of the store (same as user ID)
    responses:
      200:
        description: Store profile details
      404:
        description: Store not found or inactive
      500:
        description: Internal database error
    """
    store, error = seller_service.get_store_profile(seller_id)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({
        "message": "Store profile retrieved successfully",
        "store": response_schema.dump(store)
    }), 200        


@seller_bp.route('', methods=['PUT'])
@jwt_required()
@seller_required()
def update_store():
    """Update store profile (Partial Update)
    ---
    tags:
      - Sellers
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            store_name:
              type: string
            store_description:
              type: string
            avatar_url:
              type: string
            is_active:
              type: boolean
              description: Pass true to reactivate a closed store
    responses:
      200:
        description: Store profile updated successfully
      400:
        description: Validation error
      401:
        description: Unauthorized (Invalid or missing token)
      403:
        description: Forbidden (Requires active seller profile)
      409:
        description: New store name is already taken
      500:
        description: Internal server error
    """
    data = request.get_json(silent=True) or {}
    validated_data = update_schema.load(data)
    user_id = int(get_jwt_identity())

    store, error = seller_service.update_store(user_id, validated_data)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({
        "message": "Store profile updated successfully",
        "store": response_schema.dump(store)
    }), 200


@seller_bp.route('', methods=['DELETE'])
@jwt_required()
@seller_required()
def close_store():
    """Deactivate store (Soft Delete)
    ---
    tags:
      - Sellers
    security:
      - Bearer: []
    responses:
      200:
        description: Store and its products successfully deactivated
      401:
        description: Unauthorized (Invalid or missing token)
      403:
        description: Forbidden (Requires active seller profile)
      500:
        description: Internal server error
    """
    user_id = int(get_jwt_identity())
    _, error = seller_service.close_store(user_id)
    
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
        
    return jsonify({"message": "Your store and all associated products have been deactivated."}), 200
