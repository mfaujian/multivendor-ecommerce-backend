"""Seller service — business logic for store profiles."""
import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Sellers, Products
from app.utils import db


def create_store(user_id, validated_data):
    existing_store = db.session.get(Sellers, user_id)
    if existing_store:
        if not existing_store.is_active:
            return None, {"message": "You already have a deactivated store. Please use the update endpoint to reactivate it.", "status_code": 400}
        return None, {"message": "Your account already has a registered store!", "status_code": 400}

    try:
        store = Sellers(
            id=user_id,
            store_name=validated_data['store_name'],
            store_description=validated_data.get('store_description'),
            avatar_url=validated_data.get('avatar_url')
        )
        db.session.add(store)
        db.session.commit()
        return store, None
    except IntegrityError:
        db.session.rollback()
        return None, {"message": f"Store name '{validated_data['store_name']}' is already taken!", "status_code": 409}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def get_store_profile(seller_id):
    store = Sellers.query.filter_by(id=seller_id, is_active=True).first()
    if not store:
        return None, {"message": f"Active store with ID {seller_id} not found!", "status_code": 404}
    return store, None


def update_store(user_id, validated_data):
    store = db.session.get(Sellers, user_id)
    new_name = validated_data.get('store_name')

    try:
        if new_name and new_name != store.store_name:
            duplicate = Sellers.query.filter_by(store_name=new_name).first()
            if duplicate:
                return None, {"message": f"Store name '{new_name}' is already taken!", "status_code": 409}
            store.store_name = new_name

        if 'store_description' in validated_data:
            store.store_description = validated_data.get('store_description')
        if 'avatar_url' in validated_data:
            store.avatar_url = validated_data.get('avatar_url')
        if 'is_active' in validated_data:
            store.is_active = validated_data.get('is_active')

        db.session.commit()
        return store, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def close_store(user_id):
    try:
        store = db.session.get(Sellers, user_id)
        store.is_active = False
        for product in Products.query.filter_by(seller_id=user_id).all():
            product.is_active = False
        db.session.commit()
        return store, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}

def list_active_sellers():
    return Sellers.query.filter_by(is_active=True).order_by(Sellers.store_name.asc()).all()