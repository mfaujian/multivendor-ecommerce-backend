"""Order service — business logic for checkout and order lifecycle management."""
import logging
from datetime import date
from decimal import Decimal
from sqlalchemy import delete, or_
from sqlalchemy.exc import SQLAlchemyError
from app.models import Orders, OrderItems, Carts, cart_items, Products, Users, Addresses
from app.services.pricing_service import unit_price_for
from app.utils import db


def checkout(user_id, validated_data):
    shipping_address = validated_data['shipping_address']

    cart = Carts.query.filter_by(user_id=user_id).first()
    if not cart:
        return None, {"message": "Cart not found", "status_code": 404}

    items = db.session.query(cart_items).filter_by(cart_id=cart.id).order_by(cart_items.c.product_id).all()
    if not items:
        return None, {"message": "Your cart is empty. Cannot proceed to checkout.", "status_code": 400}

    seller_groups = {}
    for item in items:
        product = Products.query.with_for_update(of=Products).filter_by(id=item.product_id, is_active=True).first()
        if not product:
            db.session.rollback()
            return None, {"message": f"Product with ID {item.product_id} is no longer available!", "status_code": 400}
        if item.quantity > product.stock:
            db.session.rollback()
            return None, {"message": f"Insufficient stock for '{product.name}'. Only {product.stock} left.", "status_code": 400}
        seller_groups.setdefault(product.seller_id, []).append((item, product))

    try:
        created_orders = []
        for seller_id, group_items in seller_groups.items():
            order = Orders(user_id=user_id, seller_id=seller_id, shipping_address=shipping_address, total_amount=0)
            db.session.add(order)
            db.session.flush()

            order_total = 0
            for item, product in group_items:
                product.stock -= item.quantity
                subtotal = float(product.price) * item.quantity
                order_total += subtotal
                db.session.add(OrderItems(
                    order_id=order.id, product_id=product.id,
                    quantity=item.quantity, unit_price=product.price
                ))

            order.total_amount = order_total
            created_orders.append(order)

        db.session.execute(delete(cart_items).where(cart_items.c.cart_id == cart.id))
        db.session.commit()
        return created_orders, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def _resolve_shipping_address(user_id, data):
    """Return the address text to store on the order: a saved address wins over free text."""
    address_id = data.get('shipping_address_id')
    if address_id is not None:
        address = Addresses.query.filter_by(id=address_id, user_id=user_id).first()
        if not address:
            return None, {"message": "Saved address not found!", "status_code": 404}
        return address.to_text(), None
    text = (data.get('shipping_address') or '').strip()
    if not text:
        return None, {"message": "A shipping address is required (choose a saved address or type one).", "status_code": 400}
    return text, None


def create_order(user_id, data):
    """POST /orders. The browser sends product ids + quantities; the SERVER decides prices and stock.

    - duplicate product lines are merged
    - quantity must respect the product's minimum order quantity (MOQ)
    - stock products must have enough stock; 'indent' (made-to-order) products skip the stock check
    - the unit price comes from the database (volume tiers included), never from the client
    - one order is created per supplier, all inside a single transaction
    """
    requested_date = data.get('requested_delivery_date')
    if requested_date and requested_date < date.today():
        return None, {"message": "Requested delivery date cannot be in the past.", "status_code": 400}

    address_text, error = _resolve_shipping_address(user_id, data)
    if error:
        return None, error

    merged = {}
    for line in data['items']:
        merged[line['product_id']] = merged.get(line['product_id'], 0) + line['quantity']

    line_errors = []
    seller_groups = {}
    for product_id in sorted(merged):
        quantity = merged[product_id]
        product = (
            Products.query.with_for_update(of=Products)
            .filter_by(id=product_id, is_active=True).first()
        )
        if not product:
            line_errors.append({"product_id": product_id, "message": "This product is no longer available."})
            continue
        if product.seller_id == user_id:
            line_errors.append({"product_id": product_id, "message": "You cannot order your own product."})
            continue
        if quantity < product.min_order_qty:
            line_errors.append({
                "product_id": product_id,
                "message": f"Minimum order for '{product.name}' is {product.min_order_qty} {product.unit}."
            })
            continue
        if product.fulfillment_type == 'stock' and quantity > product.stock:
            line_errors.append({
                "product_id": product_id,
                "message": f"Insufficient stock for '{product.name}'. Only {product.stock} {product.unit} left."
            })
            continue
        seller_groups.setdefault(product.seller_id, []).append((product, quantity))

    if line_errors:
        db.session.rollback()
        return None, {
            "message": "Some items cannot be ordered. Please review your cart.",
            "status_code": 422,
            "details": line_errors,
        }

    payment_method = data.get('payment_method') or 'bank_transfer'
    payment_status = 'terms_requested' if payment_method == 'request_terms' else 'unpaid'

    try:
        created_orders = []
        for seller_id, group in seller_groups.items():
            order = Orders(
                user_id=user_id, seller_id=seller_id, shipping_address=address_text, total_amount=0,
                po_number=(data.get('po_number') or None), notes=(data.get('notes') or None),
                payment_method=payment_method, payment_status=payment_status,
                requested_delivery_date=requested_date,
            )
            db.session.add(order)
            db.session.flush()
            order_total = Decimal('0')
            for product, quantity in group:
                unit_price = unit_price_for(product, quantity)
                if product.fulfillment_type == 'stock':
                    product.stock -= quantity
                order_total += unit_price * quantity
                db.session.add(OrderItems(
                    order_id=order.id, product_id=product.id, quantity=quantity, unit_price=unit_price,
                    sku=product.sku, product_name=product.name,
                ))
            order.total_amount = order_total
            created_orders.append(order)
        db.session.commit()
        return created_orders, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def get_all_orders(status_filter=None, search=None, sort='desc', page=1, limit=10):
    """Admin overview of every order in the marketplace."""
    limit = max(1, min(limit or 10, 100))
    query = Orders.query.filter_by(is_active=True)
    if status_filter:
        query = query.filter(Orders.status == status_filter)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.join(Users, Users.id == Orders.user_id).filter(or_(
            Users.full_name.ilike(pattern), Users.email.ilike(pattern), Orders.po_number.ilike(pattern)
        ))
    order_column = Orders.created_at.asc() if sort == 'asc' else Orders.created_at.desc()
    return query.order_by(order_column).paginate(page=page, per_page=limit, error_out=False)


def update_payment_status(order_id, validated_data):
    order = Orders.query.filter_by(id=order_id, is_active=True).first()
    if not order:
        return None, {"message": "Order not found!", "status_code": 404}
    new_status = validated_data['payment_status']
    if order.payment_method == 'bank_transfer' and new_status in ('terms_requested', 'terms_approved'):
        return None, {"message": "Payment terms only apply to orders that requested them.", "status_code": 400}
    if order.payment_method == 'request_terms' and new_status == 'unpaid':
        return None, {"message": "Use 'terms_requested' for orders that asked for payment terms.", "status_code": 400}
    try:
        order.payment_status = new_status
        db.session.commit()
        return order, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}


def get_my_orders(user_id, status_filter=None, product_search=None, sort='desc', page=1, limit=10):
    query = Orders.query.filter_by(user_id=user_id, is_active=True)

    if status_filter:
        query = query.filter_by(status=status_filter)

    if product_search:
            query = (
                query.join(OrderItems, OrderItems.order_id == Orders.id)
                .join(Products, Products.id == OrderItems.product_id)
                .filter(Products.name.ilike(f"%{product_search}%"))
                .distinct()
            )
    
    order_column = Orders.created_at.asc() if sort == 'asc' else Orders.created_at.desc()
    query = query.order_by(order_column)
    
    return query.paginate(page=page, per_page=limit, error_out=False)


def get_order_details(order_id, requester_id, requester_role):
    order = Orders.query.filter_by(id=order_id, is_active=True).first()
    if not order:
        return None, {"message": "Order not found!", "status_code": 404}
    if requester_role != 'admin' and order.user_id != requester_id and order.seller_id != requester_id:
        return None, {"message": "Unauthorized! You can only view your own orders.", "status_code": 403}
    return order, None


ORDER_STATUS_TRANSITIONS = {
    'pending': {'processing', 'cancelled'},
    'processing': {'shipped', 'cancelled'},
    'shipped': {'delivered'},
    'delivered': set(),
    'cancelled': set(),
}


def update_order_status(order_id, requester_id, requester_role, validated_data):
    new_status = validated_data['status']
    order = Orders.query.filter_by(id=order_id, is_active=True).first()
    if not order:
        return None, {"message": "Order not found!", "status_code": 404}

    if requester_role != 'admin':
        if order.user_id == requester_id:
            if new_status != 'cancelled' or order.status != 'pending':
                return None, {"message": "Buyers can only change status to 'cancelled' while it is still pending.", "status_code": 403}
        elif order.seller_id == requester_id:
            if new_status == 'cancelled':
                return None, {"message": "Sellers cannot cancel orders. Contact admin.", "status_code": 403}
        else:
            return None, {"message": "Unauthorized! You are not involved in this order.", "status_code": 403}

    if new_status not in ORDER_STATUS_TRANSITIONS.get(order.status, set()):
        return None, {
            "message": f"Cannot change status from '{order.status}' to '{new_status}'.",
            "status_code": 409
        }

    try:
        if new_status == 'cancelled' and order.status != 'cancelled':
            for item in order.order_items:
                product = db.session.get(Products, item.product_id)
                # Made-to-order (indent) products never had stock deducted, so nothing to give back
                if product and product.fulfillment_type == 'stock':
                    product.stock += item.quantity

        order.status = new_status
        db.session.commit()
        return order, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}

def delete_order(order_id, requester_id, requester_role):
    order = Orders.query.filter_by(id=order_id, is_active=True).first()
    if not order:
        return None, {"message": "Order not found", "status_code": 404}

    if requester_role != 'admin' and order.user_id != requester_id and order.seller_id != requester_id:
        return None, {"message": "Unauthorized! You can only delete your own orders.", "status_code": 403}

    if order.status != 'cancelled':
        return None, {"message": "Order is not cancelled (immutable constraint)", "status_code": 400}

    try:
        order.is_active = False
        db.session.commit()
        return True, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"[DB ERROR]: {str(e.__dict__.get('orig', e))}")
        return None, {"message": "A database error occurred processing your request.", "status_code": 500}
