"""Product service — business logic for products"""
import logging
import re
import uuid
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Products, PriceTiers, Categories, Orders, OrderItems, Sellers
from app.utils import db

ACTIVE_ORDER_STATUSES = ('pending', 'processing', 'shipped')
MAX_PAGE_SIZE = 100
DB_ERROR = {"message": "A database error occurred processing your request.", "status_code": 500}

PRODUCT_SCALAR_FIELDS = (
    'description', 'price', 'stock', 'image_url', 'brand', 'unit', 'min_order_qty',
    'tkdn_percent', 'datasheet_url', 'fulfillment_type', 'lead_time_days',
)


def generate_unique_slug(name):
    """Auto generate a unique slug from a product name."""
    base_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
    base_slug = re.sub(r'[-\s]+', '-', base_slug)
    return f"{base_slug}-{str(uuid.uuid4())[:8]}"

def normalize_sku(sku):
    """Part numbers are stored upper-case and trimmed so lookups are case-insensitive."""
    if sku is None:
        return None
    sku = sku.strip().upper()
    return sku or None

def _validate_tiers(base_price, tiers):
    """Tiers must have unique quantities and get cheaper as quantity grows."""
    ordered = sorted(tiers, key=lambda tier: tier['min_qty'])
    quantities = [tier['min_qty'] for tier in ordered]
    if len(set(quantities)) != len(quantities):
        return "Price tiers cannot repeat the same minimum quantity."
    previous = base_price
    for tier in ordered:
        if tier['unit_price'] >= previous:
            return "Each price tier must be cheaper than the previous tier and the base price."
        previous = tier['unit_price']
    return None

def _replace_tiers(product, tiers):
    product.price_tiers.clear()
    db.session.flush()
    for tier in sorted(tiers, key=lambda item: item['min_qty']):
        product.price_tiers.append(PriceTiers(min_qty=tier['min_qty'], unit_price=tier['unit_price']))


def _sku_taken(sku, exclude_product_id=None):
    query = Products.query.filter(Products.sku == sku)
    if exclude_product_id is not None:
        query = query.filter(Products.id != exclude_product_id)
    return query.first() is not None

def create_product(actor_id, actor_role, validated_data):
    """Sellers create for their own store. Admins may pass seller_id to create for a supplier."""
    requested_seller = validated_data.get('seller_id')
    if actor_role == 'admin':
        seller_id = requested_seller or actor_id
    else:
        if requested_seller not in (None, actor_id):
            return None, {"message": "You can only create products for your own store.", "status_code": 403}
        seller_id = actor_id

    store = db.session.get(Sellers, seller_id)
    if not store or not store.is_active:
        if actor_role == 'admin':
            return None, {"message": "Choose an active supplier (seller_id) for this product.", "status_code": 400}
        return None, {"message": "Access denied. You must register an active store first to perform this action.", "status_code": 403}

    category = db.session.get(Categories, validated_data['category_id'])
    if not category:
        return None, {"message": f"Category with ID {validated_data['category_id']} not found!", "status_code": 404}

    sku = normalize_sku(validated_data.get('sku'))
    if sku and _sku_taken(sku):
        return None, {"message": f"SKU '{sku}' is already used by another product.", "status_code": 409}

    tiers = validated_data.get('price_tiers') or []
    tier_error = _validate_tiers(validated_data['price'], tiers)
    if tiers and tier_error:
        return None, {"message": tier_error, "status_code": 400}

    try:
        product = Products(
            category_id=validated_data['category_id'], seller_id=seller_id,
            name=validated_data['name'], slug=generate_unique_slug(validated_data['name']),
            sku=sku,
            **{field: validated_data[field] for field in PRODUCT_SCALAR_FIELDS if field in validated_data},
        )
        db.session.add(product)
        db.session.flush()
        _replace_tiers(product, tiers)
        db.session.commit()
        return product, None
    except IntegrityError:
        db.session.rollback()
        return None, {"message": "This product conflicts with an existing one (duplicate SKU).", "status_code": 409}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, DB_ERROR

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
    limit = max(1, min(limit or 10, MAX_PAGE_SIZE))
    query = Products.query.filter_by(is_active=True)
    if filters.get('category_id'):
        query = query.filter(Products.category_id.in_(get_category_tree_ids(filters['category_id'])))

    # `search` looks at name, SKU and brand; `name` is the older parameter and behaves the same
    term = filters.get('search') or filters.get('q') or filters.get('name')
    if term:
        pattern = f"%{term.strip()}%"
        query = query.filter(or_(
            Products.name.ilike(pattern), Products.sku.ilike(pattern), Products.brand.ilike(pattern)
        ))
    if filters.get('brand'):
        query = query.filter(func.lower(Products.brand) == filters['brand'].strip().lower())
    if filters.get('in_stock'):
        query = query.filter(or_(Products.stock > 0, Products.fulfillment_type == 'indent'))
    if filters.get('min_price') is not None:
        query = query.filter(Products.price >= filters['min_price'])
    if filters.get('max_price') is not None:
        query = query.filter(Products.price <= filters['max_price'])

    sort = filters.get('sort') or 'newest'
    if sort == 'price_asc':
        query = query.order_by(Products.price.asc(), Products.id.desc())
    elif sort == 'price_desc':
        query = query.order_by(Products.price.desc(), Products.id.desc())
    elif sort == 'name':
        query = query.order_by(Products.name.asc(), Products.id.desc())
    else:
        # Newest first, with id as a stable tie-breaker so pagination is deterministic
        query = query.order_by(Products.id.desc())
    return query.paginate(page=page, per_page=limit, error_out=False)

def lookup_products(ids=None, skus=None):
    """Bulk fetch by id and/or SKU (used by Quick Order and by the cart to refresh prices)."""
    ids = list(ids or [])[:MAX_PAGE_SIZE]
    skus = [normalize_sku(sku) for sku in (skus or []) if normalize_sku(sku)][:MAX_PAGE_SIZE]
    if not ids and not skus:
        return []
    conditions = []
    if ids:
        conditions.append(Products.id.in_(ids))
    if skus:
        conditions.append(Products.sku.in_(skus))
    return Products.query.filter(Products.is_active.is_(True), or_(*conditions)).all()

def list_brands():
    rows = (
        db.session.query(Products.brand, func.count(Products.id))
        .filter(Products.is_active.is_(True), Products.brand.isnot(None), Products.brand != '')
        .group_by(Products.brand)
        .order_by(Products.brand.asc())
        .all()
    )
    return [{"name": name, "count": count} for name, count in rows]

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

def update_product(product_id, actor_id, actor_role, validated_data):
    product = Products.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return None, {"message": "Product not found or inactive!", "status_code": 404}

    if actor_role != 'admin':
        store = db.session.get(Sellers, actor_id)
        if not store or not store.is_active:
            return None, {"message": "Access denied. You must register an active store first to perform this action.", "status_code": 403}
        if product.seller_id != actor_id:
            return None, {"message": "Unauthorized! You do not own this product.", "status_code": 403}

    if 'category_id' in validated_data:
        if not db.session.get(Categories, validated_data['category_id']):
            return None, {"message": f"Category ID {validated_data['category_id']} not found!", "status_code": 404}
        product.category_id = validated_data['category_id']

    if 'sku' in validated_data:
        sku = normalize_sku(validated_data['sku'])
        if sku and _sku_taken(sku, exclude_product_id=product.id):
            return None, {"message": f"SKU '{sku}' is already used by another product.", "status_code": 409}
        product.sku = sku

    if 'name' in validated_data and validated_data['name'] != product.name:
        product.name = validated_data['name']
        product.slug = generate_unique_slug(validated_data['name'])

    for field in PRODUCT_SCALAR_FIELDS:
        if field in validated_data:
            setattr(product, field, validated_data[field])

    if product.fulfillment_type == 'indent' and not product.lead_time_days:
        db.session.rollback()
        return None, {"message": "Lead time (days) is required for made-to-order (indent) products.", "status_code": 400}

    if 'price_tiers' in validated_data:
        tier_error = _validate_tiers(float(product.price), validated_data['price_tiers'])
        if validated_data['price_tiers'] and tier_error:
            db.session.rollback()
            return None, {"message": tier_error, "status_code": 400}
        _replace_tiers(product, validated_data['price_tiers'])

    try:
        db.session.commit()
        return product, None
    except IntegrityError:
        db.session.rollback()
        return None, {"message": "This change conflicts with an existing product (duplicate SKU).", "status_code": 409}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, DB_ERROR


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
        return None, DB_ERROR