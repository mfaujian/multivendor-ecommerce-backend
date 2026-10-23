from app.utils import db


# =========================================================================
# MODEL PRICE TIERS (volume pricing: "buy 50+ and pay less per unit")
# =========================================================================
class PriceTiers(db.Model):
    __tablename__ = 'price_tiers'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    min_qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('product_id', 'min_qty', name='uq_price_tiers_product_min_qty'),
        db.CheckConstraint('min_qty >= 2', name='price_tiers_min_qty_check'),
        db.CheckConstraint('unit_price >= 0', name='price_tiers_unit_price_check'),
    )