from models import db
from datetime import datetime

class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=True)  # ← NEW
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")
    variant = db.relationship("ProductVariant")  # ← NEW

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "color_name": self.variant.color_name if self.variant else None,
            "quantity": self.quantity,
        }