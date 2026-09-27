from models import db
from datetime import datetime


class ProductVariant(db.Model):
    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    color_name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "color_name": self.color_name,
            "stock": self.stock,
            "image_url": self.image_url,
            "position": self.position,
        }