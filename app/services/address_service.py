"""Address service — saved delivery addresses (project sites) per user."""
import logging
from sqlalchemy.exc import SQLAlchemyError
from app.models import Addresses
from app.utils import db

DB_ERROR = {"message": "A database error occurred processing your request.", "status_code": 500}
MAX_ADDRESSES = 20


def list_addresses(user_id):
    return Addresses.query.filter_by(user_id=user_id).order_by(Addresses.is_default.desc(), Addresses.id.asc()).all()


def get_owned_address(user_id, address_id):
    address = Addresses.query.filter_by(id=address_id, user_id=user_id).first()
    if not address:
        return None, {"message": "Address not found!", "status_code": 404}
    return address, None


def _clear_default(user_id, except_id=None):
    query = Addresses.query.filter_by(user_id=user_id, is_default=True)
    if except_id is not None:
        query = query.filter(Addresses.id != except_id)
    for other in query.all():
        other.is_default = False


def create_address(user_id, validated_data):
    existing = Addresses.query.filter_by(user_id=user_id).count()
    if existing >= MAX_ADDRESSES:
        return None, {"message": f"You can save at most {MAX_ADDRESSES} addresses.", "status_code": 400}
    try:
        address = Addresses(user_id=user_id, **validated_data)
        if existing == 0:
            address.is_default = True  # the first address is always the default
        db.session.add(address)
        db.session.flush()
        if address.is_default:
            _clear_default(user_id, except_id=address.id)
        db.session.commit()
        return address, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, DB_ERROR


def update_address(user_id, address_id, validated_data):
    address, error = get_owned_address(user_id, address_id)
    if error:
        return None, error
    try:
        for field, value in validated_data.items():
            setattr(address, field, value)
        if validated_data.get('is_default'):
            _clear_default(user_id, except_id=address.id)
        db.session.commit()
        return address, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, DB_ERROR


def delete_address(user_id, address_id):
    address, error = get_owned_address(user_id, address_id)
    if error:
        return None, error
    try:
        was_default = address.is_default
        db.session.delete(address)
        db.session.flush()
        if was_default:
            replacement = Addresses.query.filter_by(user_id=user_id).order_by(Addresses.id.asc()).first()
            if replacement:
                replacement.is_default = True
        db.session.commit()
        return True, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, DB_ERROR
