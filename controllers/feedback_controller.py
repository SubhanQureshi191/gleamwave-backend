from flask import request, jsonify
from models import db, Feedback, User
from datetime import datetime
import jwt
from config import Config


class FeedbackController:

    @staticmethod
    def submit_feedback():
        """Submit new feedback"""
        try:
            data = request.get_json()

            name = data.get("name")
            email = data.get("email")
            rating = data.get("rating")
            comment = data.get("comment")
            category = data.get("category", "general")

            # Validation
            if not name or not email or not rating or not comment:
                return jsonify({"error": "Name, email, rating and comment are required"}), 400

            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({"error": "Rating must be between 1 and 5"}), 400

            # Check if user is logged in
            user_id = None
            token = request.headers.get("Authorization")
            if token:
                try:
                    token = token.split(" ")[1]
                    payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
                    user_id = payload.get("user_id")
                except Exception as e:
                    print(f"Token decode error: {e}")

            feedback = Feedback(
                user_id=user_id,  # Now it's integer
                name=name,
                email=email,
                rating=rating,
                comment=comment,
                category=category,
                is_approved=False
            )

            db.session.add(feedback)
            db.session.commit()

            # Return feedback with user details
            feedback_dict = feedback.to_dict()

            return jsonify({
                "message": "Feedback submitted successfully! Thank you for your review.",
                "feedback": feedback_dict
            }), 201

        except Exception as e:
            db.session.rollback()
            print(f"❌ Feedback error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_all_feedback():
        """Get all approved feedback (public) with user details"""
        try:
            feedbacks = Feedback.query.filter_by(is_approved=True).order_by(Feedback.created_at.desc()).all()
            result = []
            for f in feedbacks:
                fb_dict = f.to_dict()
                # Add user details if user exists
                if f.user:
                    fb_dict['user'] = {
                        'id': f.user.id,
                        'name': f.user.name,
                        'email': f.user.email
                    }
                result.append(fb_dict)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_all_feedback_admin():
        """Get all feedback for admin (including unapproved) with user details"""
        try:
            feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
            result = []
            for f in feedbacks:
                fb_dict = f.to_dict()
                # Add user details if user exists
                if f.user:
                    fb_dict['user'] = {
                        'id': f.user.id,
                        'name': f.user.name,
                        'email': f.user.email
                    }
                result.append(fb_dict)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def approve_feedback(feedback_id):
        """Approve feedback (admin only)"""
        try:
            feedback = Feedback.query.get(feedback_id)
            if not feedback:
                return jsonify({"error": "Feedback not found"}), 404

            feedback.is_approved = True
            db.session.commit()

            return jsonify({"message": "Feedback approved successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def delete_feedback(feedback_id):
        """Delete feedback (admin only)"""
        try:
            feedback = Feedback.query.get(feedback_id)
            if not feedback:
                return jsonify({"error": "Feedback not found"}), 404

            db.session.delete(feedback)
            db.session.commit()

            return jsonify({"message": "Feedback deleted successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_feedback_stats():
        """Get feedback statistics"""
        try:
            total = Feedback.query.count()
            approved = Feedback.query.filter_by(is_approved=True).count()
            pending = Feedback.query.filter_by(is_approved=False).count()

            from sqlalchemy import func
            avg_rating = db.session.query(func.avg(Feedback.rating)).filter_by(is_approved=True).scalar()

            rating_dist = {}
            for i in range(1, 6):
                count = Feedback.query.filter_by(rating=i, is_approved=True).count()
                rating_dist[str(i)] = count

            return jsonify({
                "total": total,
                "approved": approved,
                "pending": pending,
                "average_rating": round(avg_rating, 1) if avg_rating else 0,
                "rating_distribution": rating_dist
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500