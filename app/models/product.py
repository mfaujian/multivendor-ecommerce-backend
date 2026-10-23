from app.utils import db

FULFILLMENT_TYPES = ('stock', 'indent')

# =========================================================================
# MODEL PRODUCTS
# =========================================================================
class Products(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key = True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable = False, index = True)
    seller_id = db.Column(db.Integer, db.ForeignKey('sellers.id', ondelete='RESTRICT'), nullable = False, index = True)
    name = db.Column(db.String(255),nullable = False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable = False)
    stock = db.Column(db.Integer, nullable = False, server_default = '0')
    image_url = db.Column(db.String(255), nullable = True)

    sku = db.Column(db.String(64), unique=True, nullable=True)            
    brand = db.Column(db.String(100), nullable=True, index=True)
    unit = db.Column(db.String(20), nullable=False, default='pcs', server_default='pcs')
    min_order_qty = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    tkdn_percent = db.Column(db.Numeric(5, 2), nullable=True)
    datasheet_url = db.Column(db.String(500), nullable=True)
    fulfillment_type = db.Column(db.String(10), nullable=False, default='stock', server_default='stock')
    lead_time_days = db.Column(db.Integer, nullable=True) 

    is_active = db.Column(db.Boolean, default = True, nullable = False)

    created_at = db.Column(db.DateTime(timezone=True), server_default = db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default = db.func.now(), onupdate = db.func.now())

    category = db.relationship('Categories', back_populates = 'products', lazy = 'joined')
    seller = db.relationship('Sellers', back_populates = 'products', lazy = 'joined')
    price_tiers = db.relationship(
        'PriceTiers', backref='product', cascade='all, delete-orphan',
        order_by='PriceTiers.min_qty', lazy='selectin'
    )

    __table_args__ = (
        db.CheckConstraint('price >= 0', name='products_price_check'),
        db.CheckConstraint('stock >= 0', name='products_stock_check'),
        db.CheckConstraint('min_order_qty >= 1', name='products_min_order_qty_check'),
        db.CheckConstraint("fulfillment_type IN ('stock', 'indent')", name='products_fulfillment_type_check'),
    )
