from flask import request, jsonify
from models import db, User
from middleware.auth import create_token, token_required
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import uuid


class AuthController:

    @staticmethod
    def login():
        """Login user with email and password"""
        data = request.get_json()

        if not data.get("email") or not data.get("password"):
            return jsonify({"error": "Email and password are required"}), 400

        try:
            email = data.get("email")
            password = data.get("password")

            print(f"🔍 Login attempt: {email}")

            # Find user by email
            user = User.query.filter_by(email=email).first()

            if not user:
                print("❌ User not found")
                return jsonify({"error": "Invalid email or password"}), 401

            print(f"👤 User found: {user.email}")

            # ─── PASSWORD CHECK ───
            if not check_password_hash(user.password_hash, password):
                print("❌ Password mismatch")
                return jsonify({"error": "Invalid email or password"}), 401

            # ─── CHECK IF USER IS ADMIN (Multiple Admin Support) ───
            is_admin = False

            # Check if user role is admin in database
            if user.role == "admin":
                is_admin = True
            # Check if email is in admin list
            elif hasattr(Config, 'ADMIN_EMAILS') and user.email in Config.ADMIN_EMAILS:
                # Update role to admin
                user.role = "admin"
                db.session.commit()
                is_admin = True
                print(f"✅ Updated {user.email} role to admin")

            # If user is admin, set role in response
            if is_admin:
                user.role = "admin"

            # ─── CREATE TOKEN ───
            token = create_token(user.id, user.role)

            return jsonify({
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role
                }
            }), 200

        except Exception as e:
            print(f"❌ Login error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def signup():
        """Register new user"""
        data = request.get_json()

        if not data.get("name") or not data.get("email") or not data.get("password"):
            return jsonify({"error": "Name, email and password are required"}), 400

        try:
            # Check if user already exists
            existing = User.query.filter_by(email=data.get("email")).first()
            if existing:
                return jsonify({"error": "User already exists"}), 400

            # ─── CHECK IF NEW USER IS ADMIN ───
            role = "customer"
            if hasattr(Config, 'ADMIN_EMAILS') and data.get("email") in Config.ADMIN_EMAILS:
                role = "admin"
                print(f"✅ New admin user: {data.get('email')}")

            # Hash password
            password_hash = generate_password_hash(data.get("password"))

            # Create user
            user = User(
                name=data.get("name"),
                email=data.get("email"),
                password_hash=password_hash,
                phone=data.get("phone", ""),
                role=role
            )

            db.session.add(user)
            db.session.commit()

            # Create token
            token = create_token(user.id, user.role)

            return jsonify({
                "message": "User created successfully",
                "token": token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role
                }
            }), 201

        except Exception as e:
            db.session.rollback()
            print(f"❌ Signup error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_me(user_id):
        """Get current user profile"""
        try:
            user = User.query.filter_by(id=user_id).first()

            if not user:
                return jsonify({"error": "User not found"}), 404

            return jsonify({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def make_admin(email):
        """Helper function to make a user admin (can be called from flask shell)"""
        try:
            user = User.query.filter_by(email=email).first()
            if user:
                user.role = "admin"
                db.session.commit()
                print(f"✅ {email} is now admin")
                return True
            else:
                print(f"❌ User {email} not found")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False