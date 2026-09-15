from models import db
from datetime import datetime

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # ← CHANGED: nullable=True
    guest_email = db.Column(db.String(150), nullable=True)  # ← NEW: For guest orders
    is_guest_order = db.Column(db.Boolean, default=False)  # ← NEW: Flag for guest orders
    total_amount = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, default=0)
    delivery_charges = db.Column(db.Float, default=300)
    status = db.Column(db.String(30), default="pending")
    shipping_name = db.Column(db.String(150))
    shipping_phone = db.Column(db.String(30))
    shipping_address = db.Column(db.Text)
    billing_address = db.Column(db.Text)
    payment_method = db.Column(db.String(50), default="cod")
    extra_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "guest_email": self.guest_email,  # ← NEW
            "is_guest_order": self.is_guest_order,  # ← NEW
            "total_amount": self.total_amount,
            "subtotal": self.subtotal,
            "delivery_charges": self.delivery_charges,
            "status": self.status,
            "shipping_name": self.shipping_name,
            "shipping_phone": self.shipping_phone,
            "shipping_address": self.shipping_address,
            "billing_address": self.billing_address,
            "payment_method": self.payment_method,
            "extra_note": self.extra_note,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "items": [item.to_dict() for item in self.items] if self.items else []
        }