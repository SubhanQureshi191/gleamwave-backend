from flask import request, jsonify
from models import db, User, PasswordReset
from werkzeug.security import generate_password_hash
from utils.email_sender import send_email


class PasswordResetController:

    @staticmethod
    def _build_otp_email_body(otp):
        """Shared HTML body for the OTP email — used by both send and resend."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Georgia, serif; background-color: #FDF8F3; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #FFFFFF; padding: 30px; border-radius: 16px; border: 2px solid #F5EDE0; }}
                .header {{ text-align: center; border-bottom: 2px solid #F5EDE0; padding-bottom: 20px; }}
                .otp-code {{ font-size: 36px; font-weight: 700; color: #6F4E37; text-align: center; padding: 20px; letter-spacing: 8px; background: #FDF8F3; border-radius: 12px; margin: 20px 0; }}
                .footer {{ text-align: center; font-size: 12px; color: #A08070; border-top: 2px solid #F5EDE0; padding-top: 20px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="color: #6F4E37; font-size: 24px; margin: 0;">gleamwave</h1>
                    <p style="color: #B8956A; font-size: 11px; margin: 4px 0 0; text-transform: uppercase; letter-spacing: 2px;">Handcrafted Resin Art</p>
                </div>

                <h2 style="color: #4A2E22; font-size: 18px; text-align: center; margin: 20px 0 10px;">Password Reset</h2>
                <p style="color: #6B4F3A; text-align: center; font-size: 14px;">Enter the following OTP to reset your password:</p>

                <div class="otp-code">{otp}</div>

                <p style="color: #A08070; text-align: center; font-size: 13px;">This OTP will expire in 10 minutes.</p>
                <p style="color: #A08070; text-align: center; font-size: 13px;">If you didn't request this, please ignore this email.</p>

                <div class="footer">
                    <p>&copy; 2025 Gleamwave &middot; Made with Love in Pakistan</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def _send_otp_email(email, otp):
        """
        Actually sends the OTP email via Resend's HTTPS API.
        Raises an exception on failure so callers can decide how to respond.
        Used by both send_otp() and resend_otp() — keeping this in one place
        means resend can never again silently forget to send the email.
        """
        send_email(
            to_email=email,
            subject="Password Reset OTP - Gleamwave",
            html_body=PasswordResetController._build_otp_email_body(otp),
        )
        print(f"OTP email sent to {email}")

    @staticmethod
    def send_otp():
        """Send OTP to user's email for password reset"""
        try:
            data = request.get_json()
            email = data.get("email")

            if not email:
                return jsonify({"error": "Email is required"}), 400

            # Check if user exists
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"error": "No account found with this email"}), 404

            # Delete any existing OTPs for this email
            PasswordReset.query.filter_by(email=email).delete()
            db.session.commit()

            # Generate OTP
            otp = PasswordReset.generate_otp()

            # Save to database
            password_reset = PasswordReset(email=email, otp=otp)
            db.session.add(password_reset)
            db.session.commit()

            # ─── SEND OTP EMAIL ───
            try:
                PasswordResetController._send_otp_email(email, otp)
            except Exception as e:
                print(f"Email error: {e}")
                # Even if email fails, OTP is saved, user can retry via resend
                return jsonify({
                    "error": "Failed to send OTP. Please try again.",
                    "details": str(e)
                }), 500

            return jsonify({
                "message": "OTP sent successfully to your email",
                "email": email
            }), 200

        except Exception as e:
            print(f"Send OTP error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def verify_otp():
        """Verify OTP for password reset"""
        try:
            data = request.get_json()
            email = data.get("email")
            otp = data.get("otp")

            if not email or not otp:
                return jsonify({"error": "Email and OTP are required"}), 400

            # Find the OTP record
            reset_record = PasswordReset.query.filter_by(
                email=email,
                otp=otp,
                is_verified=False
            ).first()

            if not reset_record:
                return jsonify({"error": "Invalid OTP"}), 400

            if reset_record.is_expired():
                db.session.delete(reset_record)
                db.session.commit()
                return jsonify({"error": "OTP has expired. Please request a new one."}), 400

            # Mark as verified
            reset_record.is_verified = True
            db.session.commit()

            return jsonify({
                "message": "OTP verified successfully",
                "verified": True
            }), 200

        except Exception as e:
            print(f"Verify OTP error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def reset_password():
        """Reset password after OTP verification"""
        try:
            data = request.get_json()
            email = data.get("email")
            otp = data.get("otp")
            new_password = data.get("new_password")
            confirm_password = data.get("confirm_password")

            if not email or not otp or not new_password or not confirm_password:
                return jsonify({"error": "All fields are required"}), 400

            if new_password != confirm_password:
                return jsonify({"error": "Passwords do not match"}), 400

            if len(new_password) < 6:
                return jsonify({"error": "Password must be at least 6 characters"}), 400

            # Verify OTP
            reset_record = PasswordReset.query.filter_by(
                email=email,
                otp=otp,
                is_verified=True
            ).first()

            if not reset_record:
                return jsonify({"error": "Invalid or unverified OTP"}), 400

            if reset_record.is_expired():
                db.session.delete(reset_record)
                db.session.commit()
                return jsonify({"error": "OTP has expired. Please request a new one."}), 400

            # Find user
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Update password
            user.password_hash = generate_password_hash(new_password)

            # Delete used OTP record
            db.session.delete(reset_record)
            db.session.commit()

            return jsonify({
                "message": "Password reset successfully",
                "success": True
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"Reset password error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def resend_otp():
        """Resend OTP to email — now actually sends the email"""
        try:
            data = request.get_json()
            email = data.get("email")

            if not email:
                return jsonify({"error": "Email is required"}), 400

            # Check if user exists
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"error": "No account found with this email"}), 404

            # Delete old OTPs
            PasswordReset.query.filter_by(email=email).delete()
            db.session.commit()

            # Generate new OTP
            otp = PasswordReset.generate_otp()

            reset_record = PasswordReset(email=email, otp=otp)
            db.session.add(reset_record)
            db.session.commit()

            # ─── SEND OTP EMAIL ───
            try:
                PasswordResetController._send_otp_email(email, otp)
            except Exception as e:
                print(f"Email error: {e}")
                return jsonify({
                    "error": "Failed to resend OTP. Please try again.",
                    "details": str(e)
                }), 500

            return jsonify({
                "message": "OTP resent successfully",
                "email": email
            }), 200

        except Exception as e:
            print(f"Resend OTP error: {e}")
            return jsonify({"error": str(e)}), 500