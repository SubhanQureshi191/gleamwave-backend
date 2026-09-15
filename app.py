import os
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from supabase import create_client
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# ─── Create App FIRST ──────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# ─── Import db from models ──────────────────────────────
from models import db

# ─── DATABASE CONFIGURATION WITH CONNECTION POOLING ──────
# Get DATABASE_URL from Config
DATABASE_URL = Config.SQLALCHEMY_DATABASE_URI or Config.DATABASE_URL

# Configure engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    pool_recycle=280,        # Recycle connections before Supabase timeout
    pool_pre_ping=True,      # Check connection health before using
    pool_timeout=30,
    max_overflow=10
)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'pool_recycle': 280,
    'pool_pre_ping': True,
    'pool_timeout': 30,
    'max_overflow': 10
}

db.init_app(app)

# ─── Supabase Client ──────────────────────────────────────
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SECRET_KEY)

# ─── Import Models ──────────────────────────────────────
from models import User, Product, ProductImage, CartItem, Order, OrderItem, CustomOrder

# ─── Import Controllers ──────────────────────────────
from controllers.auth_controller import AuthController
from controllers.product_controller import ProductController
from controllers.cart_controller import CartController
from controllers.order_controller import OrderController
from controllers.custom_order_controller import CustomOrderController
from controllers.email_controller import EmailController
from controllers.feedback_controller import FeedbackController
from controllers.password_reset_controller import PasswordResetController
# ─── Import Middleware ──────────────────────────────
from middleware.auth import token_required, admin_required


# ══════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════

# ── HEALTH CHECK ──
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "Gleamwave API is running",
        "version": "2.0",
        "endpoints": {
            "auth": "/api/auth/*",
            "products": "/api/products/*",
            "cart": "/api/cart/*",
            "orders": "/api/orders/*",
            "custom_orders": "/api/custom-orders/*",
            "email": "/api/email/*",
            "feedback": "/api/feedback/*"
        }
    })


# ── AUTH ROUTES ──
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    return AuthController.signup()


@app.route("/api/auth/login", methods=["POST"])
def login():
    return AuthController.login()


@app.route("/api/auth/me", methods=["GET"])
@token_required
def get_me():
    return AuthController.get_me(request.user_id)


# ── PRODUCT ROUTES — Public ──
@app.route("/api/products", methods=["GET"])
def get_products():
    return ProductController.get_all()


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    return ProductController.get_by_id(product_id)


# ── PRODUCT ROUTES — Admin only ──
@app.route("/api/admin/products", methods=["POST"])
@admin_required
def create_product():
    return ProductController.create()


@app.route("/api/admin/products/<int:product_id>", methods=["PUT"])
@admin_required
def update_product(product_id):
    return ProductController.update(product_id)


@app.route("/api/admin/products/<int:product_id>", methods=["DELETE"])
@admin_required
def delete_product(product_id):
    return ProductController.delete(product_id)


@app.route("/api/admin/products/<int:product_id>/images", methods=["POST"])
@admin_required
def upload_product_images(product_id):
    return ProductController.upload_images(product_id)


@app.route("/api/admin/products/images/<int:image_id>", methods=["DELETE"])
@admin_required
def delete_product_image(image_id):
    return ProductController.delete_image(image_id)


# ── CART ROUTES ──
@app.route("/api/cart", methods=["GET"])
@token_required
def get_cart():
    return CartController.get_cart(request.user_id)


@app.route("/api/cart", methods=["POST"])
@token_required
def add_to_cart():
    return CartController.add_to_cart(request.user_id)


@app.route("/api/cart/<int:item_id>", methods=["PUT"])
@token_required
def update_cart_item(item_id):
    return CartController.update_item(request.user_id, item_id)


@app.route("/api/cart/<int:item_id>", methods=["DELETE"])
@token_required
def remove_cart_item(item_id):
    return CartController.remove_item(request.user_id, item_id)


# ── ORDER ROUTES ──
@app.route("/api/orders", methods=["POST"])
@token_required
def create_order():
    return OrderController.create_order(request.user_id)


@app.route("/api/orders", methods=["GET"])
@token_required
def get_my_orders():
    return OrderController.get_user_orders(request.user_id)


@app.route("/api/admin/orders", methods=["GET"])
@admin_required
def get_all_orders():
    return OrderController.get_all_orders()


@app.route("/api/admin/orders/<int:order_id>", methods=["PUT"])
@admin_required
def update_order_status(order_id):
    return OrderController.update_status(order_id)


# ── CUSTOM ORDER ROUTES ──
@app.route("/api/custom-orders", methods=["POST"])
def create_custom_order():
    return CustomOrderController.create()


@app.route("/api/custom-orders", methods=["GET"])
@token_required
def get_my_custom_orders():
    return CustomOrderController.get_user_orders(request.user_id)


@app.route("/api/custom-orders/<int:order_id>", methods=["GET"])
@token_required
def get_custom_order(order_id):
    return CustomOrderController.get_by_id(order_id)


@app.route("/api/admin/custom-orders", methods=["GET"])
@admin_required
def get_all_custom_orders():
    return CustomOrderController.get_all()


@app.route("/api/admin/custom-orders/<int:order_id>/status", methods=["PUT"])
@admin_required
def update_custom_order_status(order_id):
    return CustomOrderController.update_status(order_id)


@app.route("/api/admin/custom-orders/<int:order_id>", methods=["DELETE"])
@admin_required
def delete_custom_order(order_id):
    return CustomOrderController.delete(order_id)


# ─── FEEDBACK ROUTES ───
@app.route("/api/feedback/submit", methods=["POST"])
def submit_feedback():
    return FeedbackController.submit_feedback()


@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    return FeedbackController.get_all_feedback()


@app.route("/api/feedback/stats", methods=["GET"])
def get_feedback_stats():
    return FeedbackController.get_feedback_stats()


@app.route("/api/admin/feedback", methods=["GET"])
@admin_required
def get_all_feedback_admin():
    return FeedbackController.get_all_feedback_admin()


@app.route("/api/admin/feedback/<int:feedback_id>/approve", methods=["PUT"])
@admin_required
def approve_feedback(feedback_id):
    return FeedbackController.approve_feedback(feedback_id)


@app.route("/api/admin/feedback/<int:feedback_id>", methods=["DELETE"])
@admin_required
def delete_feedback(feedback_id):
    return FeedbackController.delete_feedback(feedback_id)


# ─── EMAIL ROUTES ───
@app.route("/api/email/send-order-confirmation", methods=["POST"])
@token_required
def send_order_confirmation():
    try:
        data = request.get_json()

        required_fields = ['email', 'order_id', 'items']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required_fields": required_fields
            }), 400

        return EmailController.send_order_confirmation_email(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/email/send-order-status", methods=["POST"])
@token_required
def send_order_status():
    try:
        data = request.get_json()

        required_fields = ['email', 'order_id']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required_fields": required_fields
            }), 400

        return EmailController.send_order_status_email(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/orders/<int:order_id>/invoice", methods=["GET"])
@token_required
def download_invoice(order_id):
    return OrderController.download_invoice(order_id)

# ─── GET SINGLE ORDER (For Invoice) ───
@app.route("/api/admin/orders/<int:order_id>", methods=["GET"])
@admin_required
def get_order_by_id(order_id):
    return OrderController.get_order_by_id(order_id)

# ─── GET SINGLE ORDER FOR USER (Profile Page) ───
@app.route("/api/orders/<int:order_id>", methods=["GET"])
@token_required
def get_order_by_id_user(order_id):
    return OrderController.get_order_by_id_user(request.user_id, order_id)

# ─── GUEST ORDER ROUTES (No Login Required) ───

@app.route("/api/guest/orders", methods=["POST"])
def create_guest_order():
    """Create order without login - Guest Checkout"""
    return OrderController.create_guest_order()


@app.route("/api/guest/orders/<int:order_id>", methods=["GET"])
def get_guest_order(order_id):
    """Get guest order by ID + email (query param)"""
    guest_email = request.args.get("email")
    if not guest_email:
        return jsonify({"error": "Email is required"}), 400
    return OrderController.get_guest_order(order_id, guest_email)

@app.route("/api/email/send-contact", methods=["POST"])
def send_contact_email():
    try:
        data = request.get_json()

        required_fields = ['name', 'email', 'message']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required_fields": required_fields
            }), 400

        return EmailController.send_contact_email()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/email/test", methods=["GET"])
@token_required
def test_email_config():
    try:
        sender_email = Config.EMAIL_SENDER
        receiver_email = Config.EMAIL_RECEIVER

        if sender_email and receiver_email:
            return jsonify({
                "status": "success",
                "message": "Email configuration is set up correctly",
                "sender": sender_email,
                "receiver": receiver_email
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Email configuration is missing or incomplete"
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/email/test-send", methods=["POST"])
@token_required
def test_send_email():
    try:
        import smtplib
        import ssl
        from email.mime.text import MIMEText

        sender = Config.EMAIL_SENDER
        password = Config.EMAIL_PASSWORD
        test_email = request.json.get('test_email', sender)

        print(f"🧪 Testing email with: {sender}")
        print(f"🧪 Sending to: {test_email}")

        msg = MIMEText(f"""
        Test Email from Gleamwave API

        Sender: {sender}
        Time: {datetime.now()}

        This is a test email to verify your email configuration.
        """)
        msg["Subject"] = "Test Email - Gleamwave"
        msg["From"] = sender
        msg["To"] = test_email

        context = ssl.create_default_context()

        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context)
            print("✅ Connected via SSL")
        except Exception as e:
            print(f"⚠️ SSL failed, trying STARTTLS: {e}")
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls(context=context)
            print("✅ Connected via STARTTLS")

        server.login(sender, password)
        print("✅ Login successful")
        server.send_message(msg)
        server.quit()

        return jsonify({
            "success": True,
            "message": f"Test email sent successfully to {test_email}",
            "from": sender,
            "to": test_email
        }), 200

    except smtplib.SMTPAuthenticationError as e:
        return jsonify({
            "success": False,
            "error": "Authentication failed. Check your App Password.",
            "details": str(e)
        }), 401
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ─── PASSWORD RESET ROUTES ───


@app.route("/api/auth/forgot-password/send-otp", methods=["POST"])
def send_otp():
    return PasswordResetController.send_otp()

@app.route("/api/auth/forgot-password/verify-otp", methods=["POST"])
def verify_otp():
    return PasswordResetController.verify_otp()

@app.route("/api/auth/forgot-password/reset", methods=["POST"])
def reset_password():
    return PasswordResetController.reset_password()

@app.route("/api/auth/forgot-password/resend-otp", methods=["POST"])
def resend_otp():
    return PasswordResetController.resend_otp()


# ─── CREATE TABLES ──────────────────────────────────────
with app.app_context():
    try:
        db.create_all()
        print("Database runs successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")


if __name__ == "__main__":
    app.run(debug=True, port=5000)