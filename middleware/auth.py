import jwt
import datetime
from functools import wraps
from flask import request, jsonify
from config import Config
import uuid


def create_token(user_id, role):
    """Create JWT token with UUID converted to string"""
    # ✅ Convert UUID to string if it's a UUID object
    if isinstance(user_id, uuid.UUID):
        user_id = str(user_id)

    payload = {
        "user_id": user_id,  # Now a string, JSON serializable ✅
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")


def decode_token(token):
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_id_from_token(token):
    """Extract user_id from token"""
    payload = decode_token(token)
    if payload:
        return payload.get("user_id")
    return None


def token_required(f):
    """Decorator to verify JWT token"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "Token is required"}), 401

        # Decode token
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Add user info to request
        request.user_id = payload.get("user_id")
        request.user_role = payload.get("role")

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator to verify admin access"""

    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        # Check if user has admin role
        if request.user_role != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return decorated