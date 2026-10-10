"""Product service — business logic for products"""
import logging
import re
import uuid
from sqlalchemy.exc import SQLAlchemyError
from app.models import Products, Categories, Orders, OrderItems
from app.utils import db

ACTIVE_ORDER_STATUSES = ('pending', 'processing', 'shipped')


def generate_unique_slug(name):
    """Auto generate a unique slug from a product name."""
    base_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
    base_slug = re.sub(r'[-\s]+', '-', base_slug)
    return f"{base_slug}-{str(uuid.uuid4())[:8]}"


def create_product(seller_id, validated_data):
    category = db.session.get(Categories, validated_data['category_id'])
    if not category:
        return None, {"message": f"Category with ID {validated_data['category_id']} not found!", "status_code": 404}

    try:
        product = Products(
            category_id=validated_data['category_id'], seller_id=seller_id,
            name=validated_data['name'], slug=generate_unique_slug(validated_data['name']),
            description=validated_data.get('description'), price=validated_data['price'],
            stock=validated_data.get('stock', 0), image_url=validated_data.get('image_url')
        )
        db.session.add(product)
        db.session.commit()
        return product, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}

def get_category_tree_ids(category_id):
    """Return the given category ID plus the IDs of all its descendant subcategories.

    Products are assigned to leaf subcategories, so filtering by a top-level
    category must also match everything underneath it.
    """
    ids = {category_id}
    frontier = [category_id]
    while frontier:
        rows = db.session.query(Categories.id).filter(Categories.parent_id.in_(frontier)).all()
        frontier = [row.id for row in rows if row.id not in ids]
        ids.update(frontier)
    return ids

def get_products(filters, page, limit):
    query = Products.query.filter_by(is_active=True)
    if filters.get('category_id'):
        query = query.filter(Products.category_id.in_(get_category_tree_ids(filters['category_id'])))
    if filters.get('name'):
        query = query.filter(Products.name.ilike(f"%{filters['name']}%"))
    if filters.get('min_price') is not None:
        query = query.filter(Products.price >= filters['min_price'])
    if filters.get('max_price') is not None:
        query = query.filter(Products.price <= filters['max_price'])

    # Newest first, with id as a stable tie-breaker so pagination is deterministic
    query = query.order_by(Products.id.desc())
    
    return query.paginate(page=page, per_page=limit, error_out=False)


def get_product_by_id(product_id):
    product = Products.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return None, {"message": "Product not found or is no longer active!", "status_code": 404}
    return product, None


def get_product_by_slug(slug):
    product = Products.query.filter_by(slug=slug, is_active=True).first()
    if not product:
        return None, {"message": "Product not found or is no longer active!", "status_code": 404}
    return product, None


def update_product(product_id, seller_id, validated_data):
    product = Products.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return None, {"message": "Product not found or inactive!", "status_code": 404}
    if product.seller_id != seller_id:
        return None, {"message": "Unauthorized! You do not own this product.", "status_code": 403}

    if 'category_id' in validated_data:
        if not db.session.get(Categories, validated_data['category_id']):
            return None, {"message": f"Category ID {validated_data['category_id']} not found!", "status_code": 404}
        product.category_id = validated_data['category_id']
    if 'name' in validated_data and validated_data['name'] != product.name:
        product.name = validated_data['name']
        product.slug = generate_unique_slug(validated_data['name'])
    for field in ('description', 'price', 'stock', 'image_url'):
        if field in validated_data:
            setattr(product, field, validated_data[field])

    try:
        db.session.commit()
        return product, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def delete_product(product_id, requester_id, requester_role):
    product = Products.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return None, {"message": "Product not found or already deactivated!", "status_code": 404}
    if requester_role != 'admin' and product.seller_id != requester_id:
        return None, {"message": "Unauthorized! You can only delete your own products.", "status_code": 403}

    active_order_item = (
        db.session.query(OrderItems)
        .join(Orders, Orders.id == OrderItems.order_id)
        .filter(OrderItems.product_id == product_id, Orders.status.in_(ACTIVE_ORDER_STATUSES))
        .first()
    )
    if active_order_item:
        return None, {
            "message": "Cannot delete this product because it is tied to one or more active orders (pending, processing, or shipped).",
            "status_code": 409
        }

    try:
        product.is_active = False
        db.session.commit()
        return product, None
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}