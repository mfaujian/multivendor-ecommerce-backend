from app.utils import db


# =========================================================================
# MODEL ADDRESSES (saved delivery addresses / project sites)
# =========================================================================
class Addresses(db.Model):
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    label = db.Column(db.String(60), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address_line = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)
    is_default = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    def to_text(self):
        """One-line snapshot stored on the order so history survives address edits."""
        return (
            f"{self.recipient_name} ({self.phone}) - {self.address_line}, "
            f"{self.city}, {self.province} {self.postal_code}"
        )