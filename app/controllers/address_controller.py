from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.schemas import AddressCreateSchema, AddressUpdateSchema, AddressResponseSchema
from app.services import address_service

# Blueprint
address_bp = Blueprint('address', __name__, url_prefix='/addresses')

# Schemas
create_schema = AddressCreateSchema()
update_schema = AddressUpdateSchema()
response_schema = AddressResponseSchema()


# =========================================================================
# ADDRESS MODULE (BLUEPRINT: address_bp | PREFIX: /addresses)
# =========================================================================

@address_bp.route('', methods=['GET'])
@jwt_required()
def list_addresses():
    """List my saved delivery addresses
    ---
    tags:
      - Addresses
    security:
      - Bearer: []
    responses:
      200:
        description: The current user's addresses (default first)
      401:
        description: Unauthorized
    """
    addresses = address_service.list_addresses(int(get_jwt_identity()))
    return jsonify({
        "message": "Addresses retrieved successfully",
        "addresses": AddressResponseSchema(many=True).dump(addresses)
    }), 200


@address_bp.route('', methods=['POST'])
@jwt_required()
def create_address():
    """Save a new delivery address
    ---
    tags:
      - Addresses
    security:
      - Bearer: []
    responses:
      201:
        description: Address saved
      400:
        description: Validation error
    """
    validated_data = create_schema.load(request.get_json(silent=True) or {})
    address, error = address_service.create_address(int(get_jwt_identity()), validated_data)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
    return jsonify({"message": "Address saved!", "address": response_schema.dump(address)}), 201


@address_bp.route('/<int:address_id>', methods=['PUT'])
@jwt_required()
def update_address(address_id):
    """Update a saved address
    ---
    tags:
      - Addresses
    security:
      - Bearer: []
    parameters:
      - in: path
        name: address_id
        type: integer
        required: true
    responses:
      200:
        description: Address updated
      404:
        description: Address not found
    """
    validated_data = update_schema.load(request.get_json(silent=True) or {})
    address, error = address_service.update_address(int(get_jwt_identity()), address_id, validated_data)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
    return jsonify({"message": "Address updated!", "address": response_schema.dump(address)}), 200


@address_bp.route('/<int:address_id>', methods=['DELETE'])
@jwt_required()
def delete_address(address_id):
    """Delete a saved address
    ---
    tags:
      - Addresses
    security:
      - Bearer: []
    parameters:
      - in: path
        name: address_id
        type: integer
        required: true
    responses:
      200:
        description: Address deleted
      404:
        description: Address not found
    """
    _, error = address_service.delete_address(int(get_jwt_identity()), address_id)
    if error:
        return jsonify({"error": error["message"]}), error["status_code"]
    return jsonify({"message": "Address deleted!"}), 200