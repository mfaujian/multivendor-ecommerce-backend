"""Category service — business logic for product categories."""
import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Categories, Products
from app.utils import db


def create_category(validated_data):
    parent_id = validated_data.get('parent_id')
    if parent_id is not None and not db.session.get(Categories, parent_id):
        return None, {"message": f"Parent category with ID {parent_id} not found!", "status_code": 404}

    try:
        category = Categories(
            name=validated_data['name'],
            description=validated_data.get('description'),
            parent_id=parent_id
        )
        db.session.add(category)
        db.session.commit()
        return category, None
    except IntegrityError:
        db.session.rollback()
        return None, {"message": f"Category name '{validated_data['name']}' already exists on the system!", "status_code": 409}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def get_all_categories():
    return Categories.query.filter_by(parent_id=None).all()


def get_category_by_id(category_id):
    category = db.session.get(Categories, category_id)
    if not category:
        return None, {"message": "Category not found!", "status_code": 404}

    active_products = Products.query.filter_by(category_id=category_id, is_active=True).all()
    return {"category": category, "products": active_products}, None


def update_category(category_id, validated_data):
    category = db.session.get(Categories, category_id)
    if not category:
        return None, {"message": "Category not found!", "status_code": 404}

    try:
        if 'name' in validated_data:
            new_name = validated_data['name']
            if new_name != category.name:
                if Categories.query.filter_by(name=new_name).first():
                    return None, {"message": f"Category name '{new_name}' already exists!", "status_code": 409}
                category.name = new_name
        if 'description' in validated_data:
            category.description = validated_data.get('description')
        if 'parent_id' in validated_data:
            new_parent_id = validated_data['parent_id']
            if new_parent_id == category_id:
                return None, {"message": "A category cannot be its own parent!", "status_code": 400}
            if new_parent_id is not None and not db.session.get(Categories, new_parent_id):
                return None, {"message": f"Parent category with ID {new_parent_id} not found!", "status_code": 404}
            category.parent_id = new_parent_id

        db.session.commit()
        return category, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def delete_category(category_id):
    category = db.session.get(Categories, category_id)
    if not category:
        return None, {"message": "Category not found!", "status_code": 404}

    # Guard 1: products (active or not) still point at this category
    product_count = db.session.query(Products.id).filter(Products.category_id == category_id).count()
    if product_count:
        return None, {
            "message": f"Cannot delete '{category.name}' because {product_count} product(s) are still assigned to it.",
            "status_code": 409
        }

    # Guard 2: subcategories would otherwise be silently promoted to top-level categories
    child_count = db.session.query(Categories.id).filter(Categories.parent_id == category_id).count()
    if child_count:
        return None, {
            "message": f"Cannot delete '{category.name}' because it still has {child_count} subcategory(ies).",
            "status_code": 409
        }

    try:
        deleted_name = category.name
        db.session.delete(category)
        db.session.commit()
        return deleted_name, None
    except IntegrityError:
        db.session.rollback()
        return None, {"message": "Cannot delete this category because there are products or subcategories still assigned to it.", "status_code": 409}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}