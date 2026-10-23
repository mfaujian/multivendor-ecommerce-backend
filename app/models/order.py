import uuid
from sqlalchemy import Uuid
from app.utils import db

# =========================================================================
# MODEL ORDERS
# =========================================================================
class Orders(db.Model):
    __tablename__ = 'orders'

    id = db.Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable = False)
    seller_id = db.Column(db.Integer, db.ForeignKey('sellers.id', ondelete='RESTRICT'), nullable = False)
    status = db.Column(
        db.Enum('pending', 'processing', 'shipped','delivered' ,'cancelled', name='order_logistics_status'),
        nullable = False,
        server_default = "pending",
        index = True
    )
    total_amount = db.Column(db.Numeric(12, 2), nullable = False)
    shipping_address = db.Column(db.Text, nullable=  False)

    po_number = db.Column(db.String(60), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(20), nullable=False, default='bank_transfer', server_default='bank_transfer')
    payment_status = db.Column(db.String(20), nullable=False, default='unpaid', server_default='unpaid')
    requested_delivery_date = db.Column(db.Date, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), server_default = db.func.now(), index = True)
    updated_at = db.Column(db.DateTime(timezone=True), server_default = db.func.now(), onupdate = db.func.now())

    buyer = db.relationship('Users', back_populates = 'orders', lazy = 'joined')
    seller = db.relationship('Sellers', backref=db.backref('store_orders', lazy='selectin'), lazy='joined')
    order_items = db.relationship('OrderItems', backref='order', cascade='all, delete-orphan', lazy='selectin')

    __table_args__ = (
        db.CheckConstraint('total_amount >= 0', name='orders_total_amount_check'),
    )


# =========================================================================
# MODEL ORDER ITEMS
# =========================================================================

class OrderItems(db.Model):
    __tablename__ = 'order_items'
    
    order_id = db.Column(Uuid(as_uuid=True), db.ForeignKey('orders.id', ondelete='CASCADE'), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='RESTRICT'), primary_key=True)
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    sku = db.Column(db.String(64), nullable=True)
    product_name = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='order_items_quantity_check'),
        db.CheckConstraint('unit_price >= 0', name='order_items_unit_price_check')
    )

    product = db.relationship('Products', lazy='joined')
