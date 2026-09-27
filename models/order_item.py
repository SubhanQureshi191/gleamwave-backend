from models import db

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=True)  # ← NEW
    color_name = db.Column(db.String(100), nullable=True)  # ← NEW (stored permanently, like product_name)
    product_name = db.Column(db.String(200))
    price = db.Column(db.Float)  # Sale price
    cost_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer)

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "color_name": self.color_name,
            "product_name": self.product_name,
            "price": self.price,
            "cost_price": self.cost_price or 0,
            "quantity": self.quantity,
            "subtotal": round(self.price * self.quantity, 2) if self.price else 0,
            "profit": round((self.price - (self.cost_price or 0)) * self.quantity, 2) if self.price else 0,
        }