from flask import request, jsonify
from models import db, Product, ProductImage, CartItem, OrderItem
from utils.supabase_client import upload_image, delete_image
import datetime


class ProductController:

    @staticmethod
    def get_all():
        category = request.args.get("category")
        search = request.args.get("search")

        query = Product.query
        if category and category != "All":
            query = query.filter_by(category=category)
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))

        products = query.order_by(Product.created_at.desc()).all()

        result = []
        for product in products:
            product_dict = product.to_dict()
            images = ProductImage.query.filter_by(product_id=product.id).order_by(ProductImage.position).all()
            product_dict['images'] = [img.to_dict() for img in images]
            result.append(product_dict)

        return jsonify(result)

    @staticmethod
    def get_by_id(product_id):
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        product_dict = product.to_dict()
        images = ProductImage.query.filter_by(product_id=product.id).order_by(ProductImage.position).all()
        product_dict['images'] = [img.to_dict() for img in images]

        return jsonify(product_dict)

    @staticmethod
    def create():
        data = request.get_json()

        if not data.get("name"):
            return jsonify({"error": "Product name is required"}), 400
        if not data.get("category"):
            return jsonify({"error": "Category is required"}), 400
        if not data.get("price"):
            return jsonify({"error": "Price is required"}), 400

        try:
            original_price = None
            if data.get("original_price"):
                original_price = float(data.get("original_price"))

            discount_percent = 0
            if data.get("discount_percent"):
                discount_percent = float(data.get("discount_percent"))

            product = Product(
                name=data.get("name"),
                category=data.get("category"),
                price=float(data.get("price")),
                cost_price=float(data.get("cost_price", 0)),
                original_price=original_price,
                discount_percent=discount_percent,
                tag=data.get("tag", "New"),
                description=data.get("description", ""),
                stock=int(data.get("stock", 10)),
            )
            db.session.add(product)
            db.session.commit()

            product_dict = product.to_dict()
            product_dict['images'] = []

            return jsonify(product_dict), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def update(product_id):
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        data = request.get_json()

        try:
            product.cost_price = float(data.get("cost_price", 0))
            product.name = data.get("name", product.name)
            product.category = data.get("category", product.category)
            product.price = float(data.get("price", product.price))

            if "original_price" in data:
                if data["original_price"]:
                    product.original_price = float(data["original_price"])
                else:
                    product.original_price = None

            if "discount_percent" in data:
                product.discount_percent = float(data.get("discount_percent", 0))

            product.tag = data.get("tag", product.tag)
            product.description = data.get("description", product.description)
            product.stock = int(data.get("stock", product.stock))

            db.session.commit()

            product_dict = product.to_dict()
            images = ProductImage.query.filter_by(product_id=product.id).order_by(ProductImage.position).all()
            product_dict['images'] = [img.to_dict() for img in images]

            return jsonify(product_dict), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def delete(product_id):
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        try:
            # ─── STEP 1: Delete cart items referencing this product ───
            cart_items = CartItem.query.filter_by(product_id=product_id).all()
            for item in cart_items:
                db.session.delete(item)
            db.session.commit()
            print(f"✅ Deleted {len(cart_items)} cart items for product {product_id}")

            # ─── STEP 2: Delete order items referencing this product ───
            order_items = OrderItem.query.filter_by(product_id=product_id).all()
            for item in order_items:
                db.session.delete(item)
            db.session.commit()
            print(f"✅ Deleted {len(order_items)} order items for product {product_id}")

            # ─── STEP 3: Get all images ───
            images = ProductImage.query.filter_by(product_id=product_id).all()

            # ─── STEP 4: Delete images from Supabase Storage ───
            for img in images:
                try:
                    delete_image(img.image_url)
                    print(f"✅ Deleted from Supabase: {img.image_url}")
                except Exception as e:
                    print(f"⚠️ Error deleting image {img.id}: {e}")

            # ─── STEP 5: Delete product ───
            db.session.delete(product)
            db.session.commit()

            print(f"✅ Product {product_id} deleted successfully")
            return jsonify({"message": "Product deleted successfully"}), 200

        except Exception as e:
            db.session.rollback()
            print(f"❌ Delete error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def upload_images(product_id):
        from app import db
        from models import Product, ProductImage
        from utils.supabase_client import upload_image

        product = Product.query.get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        if "images" not in request.files:
            return jsonify({"error": "No images provided"}), 400

        files = request.files.getlist("images")
        files = [f for f in files if f.filename != '']

        if not files:
            return jsonify({"error": "No valid images selected"}), 400

        uploaded = []

        try:
            existing_images = ProductImage.query.filter_by(product_id=product_id).all()
            current_max_position = max([img.position for img in existing_images], default=-1)

            for idx, file in enumerate(files):
                try:
                    public_url = upload_image(file, product_id, current_max_position + 1 + idx)
                    image = ProductImage(
                        product_id=product_id,
                        image_url=public_url,
                        position=current_max_position + 1 + idx,
                    )
                    db.session.add(image)
                    uploaded.append(public_url)
                    print(f"✅ Uploaded image {idx + 1}: {public_url}")

                except Exception as e:
                    print(f"❌ Error uploading image {idx + 1}: {e}")

            db.session.commit()

            return jsonify({
                "message": f"{len(uploaded)} images uploaded successfully",
                "images": uploaded
            }), 201

        except Exception as e:
            db.session.rollback()
            print(f"❌ Upload error: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def delete_image(image_id):
        image = ProductImage.query.get(image_id)
        if not image:
            return jsonify({"error": "Image not found"}), 404

        try:
            delete_image(image.image_url)
            db.session.delete(image)
            db.session.commit()
            return jsonify({"message": "Image deleted"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500