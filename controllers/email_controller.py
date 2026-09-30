from flask import request, jsonify
from config import Config
from utils.email_sender import send_email
import traceback


class EmailController:

    @staticmethod
    def send_admin_new_order_notification(data):
        """
        Notify the store owner (Config.EMAIL_RECEIVER) that a new order came
        in. Sent for EVERY order — whether it auto-confirmed or is waiting
        for advance-payment approval — separate from the customer's own
        confirmation email.
        """
        try:
            order_id = data.get("order_id")
            name = data.get("name", "Customer")
            customer_email = data.get("email", "N/A")
            phone = data.get("phone", "N/A")
            total = data.get("total", 0)
            status = data.get("status", "confirmed")
            items = data.get("items", [])
            needs_approval = data.get("needs_admin_approval", False)

            items_html = ""
            for item in items:
                product_name = item.get("product_name", "Product")
                color_name = item.get("color_name")
                if color_name:
                    product_name = f"{product_name} ({color_name})"
                quantity = item.get("quantity", 1)
                price = item.get("price", 0)

                advance_note = ""
                if item.get("advance_required"):
                    line_advance = (item.get("advance_amount") or 0) * quantity
                    advance_note = f' — <span style="color:#B8860B;">Advance: Rs. {line_advance:,.0f}</span>'

                items_html += f"""
                    <li style="margin-bottom: 6px;">{product_name} &times; {quantity} — Rs. {price * quantity:,.0f}{advance_note}</li>
                """

            approval_banner = ""
            if needs_approval:
                approval_banner = """
                    <div style="background-color: #FEF3C7; border: 2px solid #F5C453; border-radius: 8px; padding: 12px 16px; margin: 16px 0 20px; color: #92400E; font-size: 14px; line-height: 1.5;">
                        <strong>Action needed:</strong> This order includes an advance-payment item and is waiting in your admin panel for approval before the customer receives their confirmation email.
                    </div>
                """

            body = f"""
                <!DOCTYPE html>
                <html>
                <body style="margin:0; padding:0; font-family: Georgia, 'Times New Roman', serif; background-color:#FDF8F3;">
                    <div style="max-width: 520px; margin: 0 auto; padding: 32px 24px; background-color:#FFFFFF;">
                        <div style="text-align:center; padding-bottom: 16px; border-bottom: 3px solid #B8956A; margin-bottom: 20px;">
                            <div style="font-size: 22px; font-weight: 700; color: #6F4E37; letter-spacing: 1px;">gleamwave</div>
                            <div style="font-size: 10px; color: #B8956A; text-transform: uppercase; letter-spacing: 2px; margin-top: 2px;">Admin Notification</div>
                        </div>

                        <h2 style="color:#4A2E22; margin: 0 0 4px; font-size: 20px;">New Order Received</h2>
                        <p style="color:#6B4F3A; font-size: 15px; margin: 0 0 16px;">Order #{order_id} &middot; Rs. {total:,.0f}</p>

                        {approval_banner}

                        <div style="background-color:#FDF8F3; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; border: 1px solid #F5EDE0;">
                            <p style="color:#6B4F3A; font-size: 14px; margin: 4px 0;"><strong>Customer:</strong> {name}</p>
                            <p style="color:#6B4F3A; font-size: 14px; margin: 4px 0;"><strong>Email:</strong> {customer_email}</p>
                            <p style="color:#6B4F3A; font-size: 14px; margin: 4px 0;"><strong>Phone:</strong> {phone}</p>
                            <p style="color:#6B4F3A; font-size: 14px; margin: 4px 0;"><strong>Status:</strong> {status.upper()}</p>
                        </div>

                        <h3 style="color:#4A2E22; font-size: 15px; margin: 0 0 8px;">Items</h3>
                        <ul style="color:#6B4F3A; font-size: 14px; padding-left: 20px; margin: 0 0 20px;">
                            {items_html}
                        </ul>

                        <p style="color:#A08070; font-size: 12px; margin: 0; border-top: 2px solid #F5EDE0; padding-top: 16px;">
                            Log in to the admin panel to view full details{" and approve this order" if needs_approval else ""}.
                        </p>
                    </div>
                </body>
                </html>
            """

            send_email(
                to_email=Config.EMAIL_RECEIVER,
                subject=f"New Order #{order_id} - Rs. {total:,.0f}" + (" [Needs Approval]" if needs_approval else ""),
                html_body=body,
            )
            print(f"Admin new-order notification sent for order #{order_id}")

        except Exception as e:
            print(f"Admin notification email error: {e}")
            print(traceback.format_exc())

    @staticmethod
    def send_order_confirmation_email(data):
        """
        Send order confirmation email to customer with complete order details
        Returns: (success, message) tuple - for background thread use
        """
        try:
            # Extract order data
            email = data.get("email")
            name = data.get("name", "Customer")
            order_id = data.get("order_id")
            status = data.get("status", "confirmed")
            subtotal = data.get("subtotal", 0)
            delivery_charges = data.get("delivery_charges", 300)
            total = data.get("total", 0)
            items = data.get("items", [])
            payment_method = data.get("payment_method", "cod")
            extra_note = data.get("extra_note", "")
            shipping_address = data.get("shipping_address", {})
            order_date = data.get("order_date", "")

            # Validate email
            if not email or email == "customer@example.com":
                print(f"Warning: Invalid email address: {email}")
                return False, "Invalid email address"

            print(f"Sending confirmation email to: {email}")
            print(f"Order: #{order_id}")

            # Build items HTML
            items_html = ""
            for item in items:
                product_name = item.get("product_name", item.get("product", {}).get("name", "Product"))
                color_name = item.get("color_name")
                if color_name:
                    product_name = f"{product_name} ({color_name})"
                quantity = item.get("quantity", 1)
                price = item.get("price", item.get("product", {}).get("price", 0))
                subtotal_item = price * quantity

                advance_note = ""
                if item.get("advance_required") and item.get("advance_amount"):
                    line_advance = item["advance_amount"] * quantity
                    advance_note = f'<div style="font-size: 11px; color: #B8860B; margin-top: 2px;">Advance paid: Rs. {line_advance:,.0f}</div>'

                items_html += f"""
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; font-family: Georgia, serif;">{product_name}{advance_note}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; text-align: center; font-family: Georgia, serif;">{quantity}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; text-align: right; font-family: Georgia, serif;">Rs. {price:,.0f}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; text-align: right; font-family: Georgia, serif;">Rs. {subtotal_item:,.0f}</td>
                    </tr>
                    """

            # Build shipping address HTML
            shipping_html = ""
            if shipping_address:
                shipping_html = f"""
                    <div style="background-color: #FDF8F3; padding: 16px 20px; border-radius: 8px; border: 1px solid #F5EDE0; margin-bottom: 16px;">
                        <h4 style="font-size: 14px; color: #4A2E22; margin: 0 0 8px; font-family: Georgia, serif;">Shipping Address</h4>
                        <p style="font-size: 14px; color: #6B4F3A; margin: 4px 0;">
                            {shipping_address.get('full_name', name)}<br>
                            {shipping_address.get('street', '')}<br>
                            {shipping_address.get('city', '')}, {shipping_address.get('state', '')} {shipping_address.get('zip_code', '')}<br>
                            {shipping_address.get('country', 'Pakistan')}<br>
                            Phone: {shipping_address.get('phone', '')}
                        </p>
                    </div>
                """

            total_advance_paid = sum(
                (item.get("advance_amount") or 0) * item.get("quantity", 1)
                for item in items
                if item.get("advance_required")
            )

            body = EmailController._build_email_body(
                name=name,
                order_id=order_id,
                status=status,
                subtotal=subtotal,
                delivery_charges=delivery_charges,
                total=total,
                items_html=items_html,
                shipping_html=shipping_html,
                payment_method=payment_method,
                extra_note=extra_note,
                order_date=order_date,
                is_confirmation=True,
                total_advance_paid=total_advance_paid,
            )

            send_email(
                to_email=email,
                subject=f"Order Confirmed! #{order_id} - Gleamwave",
                html_body=body,
            )

            print(f"Order confirmation email sent to {email}")
            return True, "Email sent successfully"

        except Exception as e:
            print(f"Email error: {e}")
            print(traceback.format_exc())
            return False, str(e)

    @staticmethod
    def send_order_status_email(data):
        """
        Send order status update email to customer
        Returns: (success, message) tuple
        """
        try:
            email = data.get("email")
            name = data.get("name", "Customer")
            order_id = data.get("order_id")
            status = data.get("status", "confirmed")
            subtotal = data.get("subtotal", 0)
            delivery_charges = data.get("delivery_charges", 300)
            total = data.get("total", 0)
            items = data.get("items", [])
            payment_method = data.get("payment_method", "cod")
            extra_note = data.get("extra_note", "")

            # Validate email
            if not email or email == "customer@example.com":
                print(f"Warning: Invalid email address: {email}")
                return False, "Invalid email address"

            print(f"Sending status email to: {email}")
            print(f"Order: #{order_id}, Status: {status}")

            # Status messages without emojis
            status_messages = {
                "pending": "Your order is pending confirmation.",
                "confirmed": "Your order has been confirmed! We are now crafting your beautiful piece.",
                "shipped": "Your order has been shipped! It is on its way to you.",
                "delivered": "Your order has been delivered! We hope you love it.",
                "cancelled": "Your order has been cancelled."
            }

            message = status_messages.get(status, "Your order status has been updated.")

            # Build items HTML
            items_html = ""
            for item in items:
                product_name = item.get("product_name", item.get("product", {}).get("name", "Product"))
                color_name = item.get("color_name")
                if color_name:
                    product_name = f"{product_name} ({color_name})"
                quantity = item.get("quantity", 1)
                price = item.get("price", item.get("product", {}).get("price", 0))
                subtotal_item = price * quantity

                advance_note = ""
                if item.get("advance_required") and item.get("advance_amount"):
                    line_advance = item["advance_amount"] * quantity
                    advance_note = f'<div style="font-size: 11px; color: #B8860B; margin-top: 2px;">Advance paid: Rs. {line_advance:,.0f}</div>'

                items_html += f"""
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; font-family: Georgia, serif;">{product_name}{advance_note}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; text-align: center; font-family: Georgia, serif;">{quantity}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; text-align: right; font-family: Georgia, serif;">Rs. {price:,.0f}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #E8D5BF; text-align: right; font-family: Georgia, serif;">Rs. {subtotal_item:,.0f}</td>
                    </tr>
                    """

            total_advance_paid = sum(
                (item.get("advance_amount") or 0) * item.get("quantity", 1)
                for item in items
                if item.get("advance_required")
            )

            body = EmailController._build_email_body(
                name=name,
                order_id=order_id,
                status=status,
                subtotal=subtotal,
                delivery_charges=delivery_charges,
                total=total,
                items_html=items_html,
                shipping_html="",
                payment_method=payment_method,
                extra_note=extra_note,
                order_date="",
                is_confirmation=False,
                status_message=message,
                total_advance_paid=total_advance_paid,
            )

            send_email(
                to_email=email,
                subject=f"Order #{order_id} - {status.upper()} - Gleamwave",
                html_body=body,
            )

            print(f"Status email sent to {email}")
            return True, "Email sent successfully"

        except Exception as e:
            print(f"Email error: {e}")
            print(traceback.format_exc())
            return False, str(e)

    @staticmethod
    def send_contact_email():
        """
        Send contact form email (called from route - has context)
        """
        try:
            data = request.get_json()

            name = data.get("name")
            email = data.get("email")
            phone = data.get("phone")
            message = data.get("message")

            if not name or not email or not message:
                return jsonify({"error": "Name, email and message are required"}), 400

            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Georgia, serif; color: #3D2B1F; }}
                    .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #6F4E37; color: #E8D9C0; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #FDF8F3; padding: 24px; border: 1px solid #F5EDE0; border-radius: 0 0 8px 8px; }}
                    .field {{ margin-bottom: 12px; }}
                    .label {{ font-weight: 600; color: #4A2E22; }}
                    .value {{ color: #6B4F3A; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin: 0;">New Contact Form Message</h2>
                    </div>
                    <div class="content">
                        <div class="field">
                            <div class="label">Name:</div>
                            <div class="value">{name}</div>
                        </div>
                        <div class="field">
                            <div class="label">Email:</div>
                            <div class="value">{email}</div>
                        </div>
                        <div class="field">
                            <div class="label">Phone:</div>
                            <div class="value">{phone or 'Not provided'}</div>
                        </div>
                        <div class="field">
                            <div class="label">Message:</div>
                            <div class="value" style="background: #F5EDE0; padding: 12px; border-radius: 8px; margin-top: 4px;">
                                {message}
                            </div>
                        </div>
                        <hr style="border: 1px solid #F5EDE0; margin: 16px 0;">
                        <p style="font-size: 12px; color: #A08070; text-align: center; margin: 0;">
                            Sent from Gleamwave Website Contact Form
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            send_email(
                to_email=Config.EMAIL_RECEIVER,
                subject=f"New Contact Form Message from {name}",
                html_body=body,
            )

            return jsonify({"message": "Email sent successfully!"}), 200

        except Exception as e:
            print(f"Email error: {e}")
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    # ─── Helper Methods (Static) ───

    @staticmethod
    def _build_email_body(name, order_id, status, subtotal, delivery_charges, total,
                          items_html, shipping_html, payment_method, extra_note,
                          order_date, is_confirmation=True, status_message="",
                          total_advance_paid=0):
        """Build the email HTML body without emojis"""

        if is_confirmation:
            title = "Order Confirmed!"
            subtitle = "Thank you for your order"
            message = "Thank you for shopping with Gleamwave! Your order has been confirmed and we are now crafting your beautiful resin art piece."
        else:
            title = f"Order {status.upper()}"
            subtitle = f"Your order has been {status}"
            message = status_message or f"Your order status has been updated to {status}."

        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Order {status.upper()}</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: Georgia, 'Times New Roman', serif; background-color: #FDF8F3;">
                <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px; background-color: #FFFFFF;">

                    <!-- Header -->
                    <div style="text-align: center; padding: 20px 0 30px; border-bottom: 3px solid #B8956A;">
                        <h1 style="font-size: 28px; font-weight: 700; color: #6F4E37; margin: 0; letter-spacing: 2px;">gleamwave</h1>
                        <p style="font-size: 11px; color: #B8956A; margin: 4px 0 0; text-transform: uppercase; letter-spacing: 3px;">Handcrafted Resin Art</p>
                    </div>

                    <!-- Content -->
                    <div style="padding: 30px 0;">
                        <div style="text-align: center; margin-bottom: 20px;">
                            <h2 style="font-size: 24px; color: #4A2E22; margin: 0; font-family: Georgia, serif;">{title}</h2>
                            <p style="font-size: 14px; color: #6B4F3A; margin: 8px 0 0;">{subtitle}</p>
                        </div>

                        <p style="font-size: 15px; color: #6B4F3A; margin: 0 0 4px;">Dear {name},</p>
                        <p style="font-size: 15px; color: #6B4F3A; margin: 0 0 20px; line-height: 1.6;">
                            {message}
                        </p>

                        <!-- Order Details Box -->
                        <div style="background-color: #FDF8F3; padding: 20px 24px; border-radius: 12px; border: 1px solid #F5EDE0; margin-bottom: 20px;">
                            <h3 style="font-size: 16px; color: #4A2E22; margin: 0 0 12px; font-family: Georgia, serif;">Order Details</h3>
                            <p style="font-size: 14px; color: #6B4F3A; margin: 4px 0;">
                                <strong>Order ID:</strong> #{order_id}
                            </p>
                            {f'<p style="font-size: 14px; color: #6B4F3A; margin: 4px 0;"><strong>Order Date:</strong> {order_date}</p>' if order_date else ''}
                            <p style="font-size: 14px; color: #6B4F3A; margin: 4px 0;">
                                <strong>Status:</strong> {status.upper()}
                            </p>
                            <p style="font-size: 14px; color: #6B4F3A; margin: 4px 0;">
                                <strong>Payment Method:</strong> {"Cash on Delivery" if payment_method == "cod" else "EasyPaisa"}
                            </p>
                        </div>

                        {shipping_html}

                        <!-- Items Table -->
                        <h3 style="font-size: 16px; color: #4A2E22; margin: 20px 0 12px; font-family: Georgia, serif;">Order Items</h3>
                        <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-family: Georgia, serif;">
                            <thead>
                                <tr style="background-color: #6F4E37;">
                                    <th style="padding: 10px 12px; text-align: left; color: #E8D9C0; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;">Product</th>
                                    <th style="padding: 10px 12px; text-align: center; color: #E8D9C0; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;">Qty</th>
                                    <th style="padding: 10px 12px; text-align: right; color: #E8D9C0; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;">Price</th>
                                    <th style="padding: 10px 12px; text-align: right; color: #E8D9C0; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;">Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items_html}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td colspan="3" style="padding: 10px 12px; text-align: right; font-weight: 600; color: #6B4F3A; border-top: 2px solid #E8D5BF;">
                                        Subtotal
                                    </td>
                                    <td style="padding: 10px 12px; text-align: right; font-weight: 600; color: #6B4F3A; border-top: 2px solid #E8D5BF;">
                                        Rs. {subtotal:,.0f}
                                    </td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="padding: 6px 12px; text-align: right; color: #6B4F3A;">
                                        Delivery Charges
                                    </td>
                                    <td style="padding: 6px 12px; text-align: right; color: #6B4F3A;">
                                        Rs. {delivery_charges:,.0f}
                                    </td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="padding: 12px 12px; text-align: right; font-size: 18px; font-weight: 700; color: #4A2E22; border-top: 2px solid #B8956A;">
                                        Total
                                    </td>
                                    <td style="padding: 12px 12px; text-align: right; font-size: 18px; font-weight: 700; color: #6F4E37; border-top: 2px solid #B8956A;">
                                        Rs. {total:,.0f}
                                    </td>
                                </tr>
                                {f'''
                                <tr>
                                    <td colspan="3" style="padding: 6px 12px; text-align: right; color: #B8860B;">
                                        Advance Paid
                                    </td>
                                    <td style="padding: 6px 12px; text-align: right; color: #B8860B;">
                                        - Rs. {total_advance_paid:,.0f}
                                    </td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="padding: 10px 12px; text-align: right; font-size: 15px; font-weight: 700; color: #4A2E22; border-top: 1px solid #E8D9C0;">
                                        Balance Due
                                    </td>
                                    <td style="padding: 10px 12px; text-align: right; font-size: 15px; font-weight: 700; color: #4A2E22; border-top: 1px solid #E8D9C0;">
                                        Rs. {total - total_advance_paid:,.0f}
                                    </td>
                                </tr>
                                ''' if total_advance_paid > 0 else ''}
                            </tfoot>
                        </table>

                        {f'''
                        <div style="background-color: #F5EDE0; padding: 12px 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #6F4E37;">
                            <p style="margin: 0; font-size: 14px; color: #6B4F3A;">
                                <strong>Special Instructions:</strong><br>
                                {extra_note}
                            </p>
                        </div>
                        ''' if extra_note else ''}

                        {'''
                        <div style="background-color: #F5EDE0; padding: 16px 20px; border-radius: 8px; margin: 16px 0; border: 1px solid #E8D5BF;">
                            <p style="margin: 0 0 8px; font-size: 14px; color: #4A2E22; font-weight: 600;">What's Next?</p>
                            <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #6B4F3A; line-height: 1.8;">
                                <li>We'll craft your resin art piece with care (2-3 business days)</li>
                                <li>You'll receive a shipping confirmation with tracking</li>
                                <li>Your order will be delivered to your provided address</li>
                            </ul>
                        </div>
                        ''' if is_confirmation else ''}

                        <p style="font-size: 15px; color: #6B4F3A; margin: 20px 0 8px; line-height: 1.6;">
                            If you have any questions about your order, feel free to contact us.
                        </p>
                        <p style="font-size: 15px; color: #6B4F3A; margin: 0;">
                            Warm regards,<br>
                            <strong style="color: #4A2E22;">Gleamwave Team</strong>
                        </p>
                    </div>

                    <!-- Footer -->
                    <div style="text-align: center; padding: 20px 0 0; border-top: 2px solid #F5EDE0;">
                        <p style="font-size: 12px; color: #A08070; margin: 0 0 6px;">
                            &copy; 2025 Gleamwave · Handcrafted Resin Art · Made with Love in Pakistan
                        </p>
                        <p style="font-size: 12px; color: #A08070; margin: 0;">
                            <a href="mailto:{Config.EMAIL_RECEIVER}" style="color: #6F4E37; text-decoration: none;">{Config.EMAIL_RECEIVER}</a>
                        </p>
                        <p style="font-size: 11px; color: #A08070; margin: 8px 0 0;">
                            This is a system-generated email. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """