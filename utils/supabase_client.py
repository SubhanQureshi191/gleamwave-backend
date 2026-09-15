from supabase import create_client
from config import Config
import datetime
import re

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SECRET_KEY)
BUCKET_NAME = Config.BUCKET_NAME


def upload_image(file, product_id, position):
    """
    Upload image to Supabase Storage
    """
    try:
        ext = file.filename.split(".")[-1]
        timestamp = datetime.datetime.utcnow().timestamp()
        filename = f"product_{product_id}_{timestamp}_{position}.{ext}"

        file_bytes = file.read()

        # Upload to Supabase Storage
        supabase.storage.from_(BUCKET_NAME).upload(
            filename,
            file_bytes,
            {"content-type": file.content_type}
        )

        # Get public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        return public_url

    except Exception as e:
        print(f"Error uploading image: {e}")
        raise e


def delete_image(image_url):
    """
    Delete image from Supabase Storage
    """
    try:
        # Extract file path from URL
        # Handle different URL formats
        if f"{BUCKET_NAME}/" in image_url:
            file_path = image_url.split(f"{BUCKET_NAME}/")[-1]
        else:
            # Try to get last part after /
            file_path = image_url.split("/")[-1]

        # Remove any query parameters
        file_path = file_path.split("?")[0]

        # Decode URL if needed
        file_path = file_path.replace("%20", " ")

        # Delete from Supabase Storage
        result = supabase.storage.from_(BUCKET_NAME).remove([file_path])
        print(f"✅ Deleted from Supabase: {file_path}")
        return True

    except Exception as e:
        print(f"❌ Error deleting image from Supabase: {e}")
        print(f"   Image URL: {image_url}")
        return False


def delete_multiple_images(image_urls):
    """
    Delete multiple images from Supabase Storage
    """
    try:
        file_paths = []
        for image_url in image_urls:
            if f"{BUCKET_NAME}/" in image_url:
                file_path = image_url.split(f"{BUCKET_NAME}/")[-1]
            else:
                file_path = image_url.split("/")[-1]
            file_path = file_path.split("?")[0]
            file_path = file_path.replace("%20", " ")
            file_paths.append(file_path)

        if file_paths:
            supabase.storage.from_(BUCKET_NAME).remove(file_paths)
            print(f"✅ Deleted {len(file_paths)} images from Supabase")
        return True

    except Exception as e:
        print(f"Error deleting multiple images: {e}")
        return False


def get_image_url(file_path):
    """
    Get public URL for an image
    """
    try:
        return supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
    except Exception as e:
        print(f"Error getting image URL: {e}")
        return None