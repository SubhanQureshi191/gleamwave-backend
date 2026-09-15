from models import db
from datetime import datetime

class CustomOrder(db.Model):
    __tablename__ = "custom_orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    whatsapp = db.Column(db.String(30), nullable=False)
    product_type = db.Column(db.String(100), nullable=False)
    occasion = db.Column(db.String(100))
    color_preference = db.Column(db.String(200))
    budget = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "whatsapp": self.whatsapp,
            "product_type": self.product_type,
            "occasion": self.occasion,
            "color_preference": self.color_preference,
            "budget": self.budget,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else None
        }