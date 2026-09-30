import json
from models import db

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=True)
    color_name = db.Column(db.String(100), nullable=True)
    product_name = db.Column(db.String(200))
    price = db.Column(db.Float)  # Sale price
    cost_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer)

    # ─── ADVANCE PAYMENT (for handcrafted products that require it) ───
    advance_required = db.Column(db.Boolean, default=False)
    advance_amount = db.Column(db.Float, nullable=True)
    # Stored as a JSON-encoded list of URLs, e.g. '["url1", "url2"]',
    # since a customer may attach more than one screenshot.
    advance_screenshot_urls = db.Column(db.Text, nullable=True)

    def to_dict(self):
        screenshots = []
        if self.advance_screenshot_urls:
            try:
                screenshots = json.loads(self.advance_screenshot_urls)
            except (ValueError, TypeError):
                screenshots = []

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
            "advance_required": self.advance_required or False,
            "advance_amount": self.advance_amount,
            "advance_screenshot_urls": screenshots,
        }