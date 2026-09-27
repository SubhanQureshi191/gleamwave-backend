from flask import request, jsonify, send_file
from models import db, Order, OrderItem, CartItem, Product, ProductVariant, User
from controllers.email_controller import EmailController
from utils.invoice_generator import InvoiceGenerator
import threading
import traceback
import os


class OrderController:

    @staticmethod
    def create_order(user_id):
        """Create a new order from user's cart - AUTO CONFIRMED"""
        data = request.get_json()
        items = CartItem.query.filter_by(user_id=user_id).all()

        if not items:
            return jsonify({"error": "Cart is empty"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        subtotal = sum(item.product.price * item.quantity for item in items if item.product)
        delivery_charges = data.get("delivery_charges", 300)
        total = subtotal + delivery_charges

        order = Order(
            user_id=user_id,
            total_amount=round(total, 2),
            subtotal=round(subtotal, 2),
            delivery_charges=round(delivery_charges, 2),
            status="confirmed",
            shipping_name=data.get("shipping_name"),
            shipping_phone=data.get("shipping_phone"),
            shipping_address=data.get("shipping_address"),
            billing_address=data.get("billing_address", data.get("shipping_address")),
            payment_method=data.get("payment_method", "cod"),
            extra_note=data.get("extra_note", ""),
        )
        db.session.add(order)
        db.session.flush()

        order_items_data = []
        for item in items:
            product = Product.query.get(item.product_id)
            if not product:
                continue

            color_name = None

            # ─── If a color was chosen, check & decrement THAT color's stock ───
            if item.variant_id:
                variant = ProductVariant.query.get(item.variant_id)
                if not variant:
                    db.session.rollback()
                    return jsonify({"error": f"Selected color is no longer available for {product.name}"}), 400
                if variant.stock < item.quantity:
                    db.session.rollback()
                    return jsonify({
                        "error": f"Insufficient stock for {product.name} ({variant.color_name}). Available: {variant.stock}, Required: {item.quantity}"
                    }), 400
                variant.stock -= item.quantity
                color_name = variant.color_name
            else:
                if product.stock >= item.quantity:
                    product.stock -= item.quantity
                else:
                    db.session.rollback()
                    return jsonify({
                        "error": f"Insufficient stock for {product.name}. Available: {product.stock}, Required: {item.quantity}"
                    }), 400

            # ─── SAVE COST PRICE + COLOR IN ORDER ITEM ───
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                color_name=color_name,
                product_name=item.product.name,
                price=item.product.price,
                cost_price=item.product.cost_price or 0,
                quantity=item.quantity,
            )
            db.session.add(order_item)
            order_items_data.append({
                "product_name": item.product.name,
                "color_name": color_name,
                "quantity": item.quantity,
                "price": item.product.price,
                "cost_price": item.product.cost_price or 0
            })
            db.session.delete(item)

        db.session.commit()

        # ─── GENERATE INVOICE ───
        invoice_path = None
        try:
            invoice_path = InvoiceGenerator.generate_invoice(order, order_items_data, user)
            print(f"Invoice generated: {invoice_path}")
        except Exception as e:
            print(f"Invoice generation error: {e}")
            print(traceback.format_exc())

        # ─── SEND ORDER CONFIRMATION EMAIL ───
        try:
            email_data = {
                "email": user.email,
                "name": order.shipping_name or user.name,
                "order_id": order.id,
                "status": "confirmed",
                "subtotal": subtotal,
                "delivery_charges": delivery_charges,
                "total": total,
                "items": order_items_data,
                "payment_method": order.payment_method,
                "extra_note": order.extra_note or "",
                "shipping_address": {
                    "full_name": order.shipping_name or user.name,
                    "street": order.shipping_address or "",
                    "city": data.get("city", ""),
                    "zip_code": data.get("postalCode", ""),
                    "country": "Pakistan",
                    "phone": order.shipping_phone or user.phone or ""
                },
                "order_date": order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "",
                "invoice_path": invoice_path
            }

            def send_email_async():
                try:
                    from app import app
                    with app.app_context():
                        result = EmailController.send_order_confirmation_email(email_data)
                        print(f"Order confirmation email result: {result}")
                except Exception as e:
                    print(f"Background email error: {e}")
                    print(traceback.format_exc())

            thread = threading.Thread(target=send_email_async)
            thread.daemon = True
            thread.start()
            print(f"Order confirmation email queued for order #{order.id} to {user.email}")

        except Exception as e:
            print(f"Failed to queue email: {e}")
            print(traceback.format_exc())

        order_dict = order.to_dict()
        order_dict['user_email'] = user.email
        order_dict['items'] = order_items_data
        order_dict['invoice_path'] = invoice_path

        return jsonify(order_dict), 201

    # ─── GET SINGLE ORDER FOR USER (Profile Page) ───
    @staticmethod
    def get_order_by_id_user(user_id, order_id):
        """Get a specific order by ID for a user"""
        try:
            order = Order.query.filter_by(id=order_id, user_id=user_id).first()
            if not order:
                return jsonify({"error": "Order not found"}), 404

            order_dict = order.to_dict()

            # Get order items
            order_items = OrderItem.query.filter_by(order_id=order_id).all()
            order_dict['items'] = [item.to_dict() for item in order_items]

            return jsonify(order_dict), 200

        except Exception as e:
            print(f"Get order error: {e}")
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    # ─── GET SINGLE ORDER FOR ADMIN ───
    @staticmethod
    def get_order_by_id(order_id):
        """Get a specific order by ID with full details (Admin only)"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return jsonify({"error": "Order not found"}), 404

            order_dict = order.to_dict()

            # Add user email
            if order.user_id:
                user = User.query.get(order.user_id)
                if user:
                    order_dict['user_email'] = user.email

            # Get order items with product details
            order_items = OrderItem.query.filter_by(order_id=order_id).all()
            order_dict['items'] = []
            for item in order_items:
                item_dict = item.to_dict()
                # Add product_id for frontend
                item_dict['product_id'] = item.product_id
                order_dict['items'].append(item_dict)

            return jsonify(order_dict), 200

        except Exception as e:
            print(f"Get order error: {e}")
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def download_invoice(order_id):
        """Download invoice PDF for an order"""
        try:
            # Check if order exists
            order = Order.query.get(order_id)
            if not order:
                return jsonify({"error": "Order not found"}), 404

            # Find invoice file
            invoice_path = InvoiceGenerator.get_invoice_path(order_id)

            if not invoice_path:
                # Generate invoice if not exists
                user = User.query.get(order.user_id)
                order_items = OrderItem.query.filter_by(order_id=order_id).all()
                order_items_data = [{
                    "product_name": item.product_name,
                    "color_name": item.color_name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "cost_price": item.cost_price or 0
                } for item in order_items]

                invoice_path = InvoiceGenerator.generate_invoice(order, order_items_data, user)

            return send_file(
                invoice_path,
                as_attachment=True,
                download_name=f"Invoice_Order_{order_id}.pdf",
                mimetype='application/pdf'
            )

        except Exception as e:
            print(f"Invoice download error: {e}")
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def get_user_orders(user_id):
        orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
        return jsonify([o.to_dict() for o in orders])

    @staticmethod
    def get_all_orders():
        orders = Order.query.order_by(Order.created_at.desc()).all()
        order_list = []
        for order in orders:
            order_dict = order.to_dict()
            if order.user_id:
                user = User.query.get(order.user_id)
                if user:
                    order_dict['user_email'] = user.email
            order_list.append(order_dict)
        return jsonify(order_list), 200

    @staticmethod
    def update_status(order_id):
        from models import Order, OrderItem, Product, ProductVariant, User
        from controllers.email_controller import EmailController

        order = Order.query.get(order_id)
        if not order:
            return jsonify({"error": "Order not found"}), 404

        data = request.get_json()
        new_status = data.get("status")
        old_status = order.status

        # Get user email
        user_email = None
        if order.user_id:
            user = User.query.get(order.user_id)
            if user:
                user_email = user.email

        order_items = OrderItem.query.filter_by(order_id=order_id).all()

        # If order is being cancelled - restore stock (to the right color, if any)
        if new_status == "cancelled" and old_status != "cancelled":
            try:
                for item in order_items:
                    if item.variant_id:
                        variant = ProductVariant.query.get(item.variant_id)
                        if variant:
                            variant.stock += item.quantity
                    else:
                        product = Product.query.get(item.product_id)
                        if product:
                            product.stock += item.quantity
                db.session.commit()

                # Send cancellation email
                if user_email:
                    try:
                        email_data = {
                            "email": user_email,
                            "name": order.shipping_name,
                            "order_id": order.id,
                            "subtotal": order.subtotal,
                            "delivery_charges": order.delivery_charges,
                            "total": order.total_amount,
                            "payment_method": order.payment_method,
                            "extra_note": order.extra_note or "",
                            "status": "cancelled",
                            "items": [
                                {
                                    "product_name": item.product_name,
                                    "color_name": item.color_name,
                                    "quantity": item.quantity,
                                    "price": item.price
                                }
                                for item in order_items
                            ]
                        }
                        EmailController.send_order_status_email(email_data)
                        print(f"Cancellation email sent to {user_email}")
                    except Exception as e:
                        print(f"Email error: {e}")

            except Exception as e:
                db.session.rollback()
                return jsonify({"error": str(e)}), 500

        # If order is being shipped or delivered - send notification
        elif new_status in ["shipped", "delivered"] and old_status != new_status:
            try:
                if user_email:
                    email_data = {
                        "email": user_email,
                        "name": order.shipping_name,
                        "order_id": order.id,
                        "subtotal": order.subtotal,
                        "delivery_charges": order.delivery_charges,
                        "total": order.total_amount,
                        "payment_method": order.payment_method,
                        "extra_note": order.extra_note or "",
                        "status": new_status,
                        "items": [
                            {
                                "product_name": item.product_name,
                                "color_name": item.color_name,
                                "quantity": item.quantity,
                                "price": item.price
                            }
                            for item in order_items
                        ]
                    }
                    EmailController.send_order_status_email(email_data)
                    print(f"{new_status} email sent to {user_email}")
            except Exception as e:
                print(f"Email error: {e}")

        order.status = new_status
        db.session.commit()

        # ─── GENERATE INVOICE ON STATUS CHANGE ───
        if new_status in ["shipped", "delivered"]:
            try:
                user = User.query.get(order.user_id)
                order_items_data = [{
                    "product_name": item.product_name,
                    "color_name": item.color_name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "cost_price": item.cost_price or 0
                } for item in order_items]

                # Generate/update invoice with new status
                InvoiceGenerator.generate_invoice(order, order_items_data, user)
                print(f"Invoice updated with status: {new_status}")
            except Exception as e:
                print(f"Invoice generation error on status change: {e}")

        # Return updated order with email
        order_dict = order.to_dict()
        order_dict['user_email'] = user_email

        return jsonify(order_dict), 200

    @staticmethod
    def create_guest_order():
        """Create a new order for GUEST (no login required)"""
        data = request.get_json()

        # ─── VALIDATE REQUIRED FIELDS ───
        required_fields = ['shipping_name', 'shipping_phone', 'shipping_address', 'guest_email', 'items']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        guest_email = data.get("guest_email")
        items = data.get("items", [])  # ← Items from localStorage cart

        if not items:
            return jsonify({"error": "Cart is empty"}), 400

        # ─── CALCULATE TOTALS ───
        subtotal = 0
        order_items_data = []
        variant_updates = []
        product_updates = []

        for item in items:
            product = Product.query.get(item.get("product_id"))
            if not product:
                return jsonify({"error": f"Product not found: {item.get('product_id')}"}), 404

            quantity = item.get("quantity", 1)
            variant_id = item.get("variant_id")
            color_name = None

            # ─── If a color was chosen, check stock on THAT color ───
            if variant_id:
                variant = ProductVariant.query.filter_by(id=variant_id, product_id=product.id).first()
                if not variant:
                    return jsonify({"error": f"Selected color is no longer available for {product.name}"}), 400
                if variant.stock < quantity:
                    return jsonify({
                        "error": f"Insufficient stock for {product.name} ({variant.color_name}). Available: {variant.stock}, Required: {quantity}"
                    }), 400
                color_name = variant.color_name
                variant_updates.append({"variant": variant, "quantity": quantity})
            else:
                # Check stock
                if product.stock < quantity:
                    return jsonify({
                        "error": f"Insufficient stock for {product.name}. Available: {product.stock}, Required: {quantity}"
                    }), 400
                product_updates.append({"product": product, "quantity": quantity})

            item_price = product.price
            item_total = item_price * quantity
            subtotal += item_total

            order_items_data.append({
                "product_id": product.id,
                "variant_id": variant_id,
                "color_name": color_name,
                "product_name": product.name,
                "price": item_price,
                "cost_price": product.cost_price or 0,
                "quantity": quantity
            })

        delivery_charges = data.get("delivery_charges", 300)
        total = subtotal + delivery_charges

        # ─── CREATE ORDER ───
        order = Order(
            user_id=None,  # ← Guest order
            guest_email=guest_email,  # ← Guest email
            is_guest_order=True,  # ← Mark as guest
            total_amount=round(total, 2),
            subtotal=round(subtotal, 2),
            delivery_charges=round(delivery_charges, 2),
            status="confirmed",
            shipping_name=data.get("shipping_name"),
            shipping_phone=data.get("shipping_phone"),
            shipping_address=data.get("shipping_address"),
            billing_address=data.get("billing_address", data.get("shipping_address")),
            payment_method=data.get("payment_method", "cod"),
            extra_note=data.get("extra_note", ""),
        )
        db.session.add(order)
        db.session.flush()

        # ─── CREATE ORDER ITEMS ───
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data["product_id"],
                variant_id=item_data["variant_id"],
                color_name=item_data["color_name"],
                product_name=item_data["product_name"],
                price=item_data["price"],
                cost_price=item_data["cost_price"],
                quantity=item_data["quantity"],
            )
            db.session.add(order_item)

        # ─── UPDATE STOCK (variant-specific where applicable) ───
        for update in variant_updates:
            update["variant"].stock -= update["quantity"]
        for update in product_updates:
            update["product"].stock -= update["quantity"]

        db.session.commit()

        # ─── GENERATE INVOICE ───
        invoice_path = None
        try:
            # Create a temporary user-like object for invoice
            class GuestUser:
                def __init__(self, email, name, phone):
                    self.email = email
                    self.name = name
                    self.phone = phone

            guest_user = GuestUser(
                email=guest_email,
                name=data.get("shipping_name"),
                phone=data.get("shipping_phone")
            )

            invoice_path = InvoiceGenerator.generate_invoice(order, order_items_data, guest_user)
            print(f"Guest invoice generated: {invoice_path}")
        except Exception as e:
            print(f"Guest invoice generation error: {e}")
            print(traceback.format_exc())

        # ─── SEND ORDER CONFIRMATION EMAIL ───
        try:
            email_data = {
                "email": guest_email,
                "name": order.shipping_name,
                "order_id": order.id,
                "status": "confirmed",
                "subtotal": subtotal,
                "delivery_charges": delivery_charges,
                "total": total,
                "items": order_items_data,
                "payment_method": order.payment_method,
                "extra_note": order.extra_note or "",
                "shipping_address": {
                    "full_name": order.shipping_name,
                    "street": order.shipping_address or "",
                    "city": data.get("city", ""),
                    "zip_code": data.get("postalCode", ""),
                    "country": "Pakistan",
                    "phone": order.shipping_phone or ""
                },
                "order_date": order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "",
                "invoice_path": invoice_path
            }

            def send_email_async():
                try:
                    from app import app
                    with app.app_context():
                        result = EmailController.send_order_confirmation_email(email_data)
                        print(f"Guest order confirmation email result: {result}")
                except Exception as e:
                    print(f"Background email error: {e}")
                    print(traceback.format_exc())

            thread = threading.Thread(target=send_email_async)
            thread.daemon = True
            thread.start()
            print(f"Guest order confirmation email queued for #{order.id} to {guest_email}")

        except Exception as e:
            print(f"Failed to queue email: {e}")
            print(traceback.format_exc())

        # ─── RETURN ORDER ───
        order_dict = order.to_dict()
        order_dict['items'] = order_items_data
        order_dict['invoice_path'] = invoice_path

        return jsonify(order_dict), 201

    @staticmethod
    def get_guest_order(order_id, guest_email):
        """Get a guest order by ID + email verification"""
        try:
            order = Order.query.filter_by(
                id=order_id,
                guest_email=guest_email,
                is_guest_order=True
            ).first()

            if not order:
                return jsonify({"error": "Order not found"}), 404

            order_dict = order.to_dict()
            order_items = OrderItem.query.filter_by(order_id=order_id).all()
            order_dict['items'] = [item.to_dict() for item in order_items]

            return jsonify(order_dict), 200

        except Exception as e:
            print(f"Get guest order error: {e}")
            return jsonify({"error": str(e)}), 500