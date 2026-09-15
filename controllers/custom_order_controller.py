from flask import request, jsonify
from models import db, CustomOrder
from middleware.auth import get_user_id_from_token
import datetime


class CustomOrderController:

    @staticmethod
    def create():
        """Create a new custom order inquiry (works for both guests and logged-in users)"""
        try:
            data = request.get_json()

            # Validate required fields
            required_fields = ['name', 'email', 'whatsapp', 'product_type', 'description']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"error": f"{field} is required"}), 400

            # ─── OPTIONAL AUTH: link to account if a valid token is present, ───
            # ─── but never require one — guests can submit too ───
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                user_id = get_user_id_from_token(token)

            custom_order = CustomOrder(
                user_id=user_id,
                name=data.get('name'),
                email=data.get('email'),
                whatsapp=data.get('whatsapp'),
                product_type=data.get('product_type'),
                occasion=data.get('occasion', ''),
                color_preference=data.get('color_preference', ''),
                budget=data.get('budget', ''),
                description=data.get('description'),
                status='pending'
            )

            db.session.add(custom_order)
            db.session.commit()

            # Send notification email (optional)
            # send_custom_order_email(custom_order)

            return jsonify({
                "message": "Custom order submitted successfully!",
                "order": custom_order.to_dict()
            }), 201

        except Exception as e:
            db.session.rollback()
            print(f"❌ Custom Order Error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_all():
        """Get all custom orders (Admin only)"""
        try:
            orders = CustomOrder.query.order_by(CustomOrder.created_at.desc()).all()
            return jsonify([o.to_dict() for o in orders]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_user_orders(user_id):
        """Get custom orders for a specific user"""
        try:
            orders = CustomOrder.query.filter_by(user_id=user_id).order_by(CustomOrder.created_at.desc()).all()
            return jsonify([o.to_dict() for o in orders]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_by_id(order_id):
        """Get a specific custom order by ID"""
        try:
            order = CustomOrder.query.get(order_id)
            if not order:
                return jsonify({"error": "Custom order not found"}), 404
            return jsonify(order.to_dict()), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def update_status(order_id):
        """Update custom order status (Admin only)"""
        try:
            order = CustomOrder.query.get(order_id)
            if not order:
                return jsonify({"error": "Custom order not found"}), 404

            data = request.get_json()
            status = data.get('status')

            valid_statuses = ['pending', 'contacted', 'confirmed', 'completed', 'cancelled']
            if status not in valid_statuses:
                return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400

            order.status = status
            db.session.commit()

            return jsonify({
                "message": "Order status updated successfully",
                "order": order.to_dict()
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def delete(order_id):
        """Delete a custom order (Admin only)"""
        try:
            order = CustomOrder.query.get(order_id)
            if not order:
                return jsonify({"error": "Custom order not found"}), 404

            db.session.delete(order)
            db.session.commit()

            return jsonify({"message": "Custom order deleted successfully"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500