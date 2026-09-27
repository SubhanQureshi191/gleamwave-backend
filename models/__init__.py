from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User
from models.product import Product
from models.product_image import ProductImage
from models.product_variant import ProductVariant  # ← ADD THIS
from models.cart_item import CartItem
from models.order import Order
from models.order_item import OrderItem
from models.custom_order import CustomOrder
from models.feedback import Feedback
from models.password_reset import PasswordReset

__all__ = [
    'db',
    'User',
    'Product',
    'ProductImage',
    'ProductVariant',  # ← ADD THIS
    'CartItem',
    'Order',
    'OrderItem',
    'CustomOrder',
    'Feedback',
    'PasswordReset'
]