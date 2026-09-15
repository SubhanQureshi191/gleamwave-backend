from models import db
from datetime import datetime


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)

    # Cost Price (what it costs you to make)
    cost_price = db.Column(db.Float, default=0)  # ← NEW

    # Selling price
    price = db.Column(db.Float, nullable=False)

    # Original price before discount
    original_price = db.Column(db.Float, nullable=True)

    # Discount percentage
    discount_percent = db.Column(db.Float, default=0)

    tag = db.Column(db.String(50), default="New")
    description = db.Column(db.Text, default="")
    stock = db.Column(db.Integer, default=10)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "cost_price": self.cost_price or 0,
            "price": self.price,
            "original_price": self.original_price,
            "discount_percent": self.discount_percent or 0,
            "tag": self.tag,
            "description": self.description,
            "stock": self.stock,
            # Calculated fields
            "profit_per_unit": (self.price or 0) - (self.cost_price or 0),
            "profit_margin": round(((self.price or 0) - (self.cost_price or 0)) / (self.price or 1) * 100, 2) if self.price else 0,
        }