import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY")

    # ─── Admin Emails (Multiple Admins Support) ───
    ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "subhanqureshi191@gmail.com,hello.gleamwave.pk@gmail.com").split(",")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "subhanqureshi191@gmail.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
    BUCKET_NAME = "product-images"

    # ─── Email Configuration ───
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "hello.gleamwave.pk@gmail.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "hello.gleamwave.pk@gmail.com")