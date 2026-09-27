from flask import request, jsonify
from models import db, CartItem, Product, ProductImage, ProductVariant


class CartController:

    @staticmethod
    def get_cart(user_id):
        items = CartItem.query.filter_by(user_id=user_id).all()
        total = 0
        item_list = []

        for item in items:
            product = Product.query.get(item.product_id)
            if product:
                images = ProductImage.query.filter_by(product_id=product.id).order_by(ProductImage.position).all()
                product_dict = product.to_dict()
                product_dict['images'] = [img.to_dict() for img in images]

                subtotal = product.price * item.quantity
                total += subtotal

                item_dict = item.to_dict()
                item_dict['product'] = product_dict

                # ─── If a color was chosen, show that color's image instead ───
                if item.variant_id:
                    variant = ProductVariant.query.get(item.variant_id)
                    if variant:
                        item_dict['color_name'] = variant.color_name
                        item_dict['variant_stock'] = variant.stock
                        if variant.image_url:
                            item_dict['product']['images'] = [{"image_url": variant.image_url, "position": 0}]

                item_dict['subtotal'] = subtotal
                item_list.append(item_dict)

        return jsonify({
            "items": item_list,
            "total": round(total, 2),
            "item_count": sum(item.quantity for item in items),
        })

    @staticmethod
    def add_to_cart(user_id):
        data = request.get_json()
        product_id = data.get("product_id")
        variant_id = data.get("variant_id")  # ← optional, the chosen color
        quantity = data.get("quantity", 1)

        product = Product.query.get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        # ─── VALIDATE THE CHOSEN COLOR, IF ANY ───
        if variant_id:
            variant = ProductVariant.query.filter_by(id=variant_id, product_id=product_id).first()
            if not variant:
                return jsonify({"error": "Selected color is not available for this product"}), 400
            if variant.stock < quantity:
                return jsonify({"error": f"Only {variant.stock} left in this color"}), 400

        # ─── Same product + same color = one cart line; different color = a separate line ───
        existing = CartItem.query.filter_by(
            user_id=user_id, product_id=product_id, variant_id=variant_id
        ).first()

        if existing:
            existing.quantity += quantity
        else:
            existing = CartItem(
                user_id=user_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
            )
            db.session.add(existing)

        db.session.commit()
        return jsonify(existing.to_dict()), 201

    @staticmethod
    def update_item(user_id, item_id):
        item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({"error": "Cart item not found"}), 404

        data = request.get_json()
        quantity = data.get("quantity")
        if quantity is not None:
            if quantity <= 0:
                db.session.delete(item)
                db.session.commit()
                return jsonify({"message": "Item removed"}), 200
            item.quantity = quantity

        db.session.commit()
        return jsonify(item.to_dict())

    @staticmethod
    def remove_item(user_id, item_id):
        item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({"error": "Cart item not found"}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Item removed"}), 200