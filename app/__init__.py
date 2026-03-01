import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address)


def create_app():
    app = Flask(__name__)

    # ── CONFIG ────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600          # 1 jam
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 2592000      # 30 hari

    # Security headers
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # ── EXTENSIONS ────────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    CORS(app, resources={
        r"/api/*": {
            "origins": os.environ.get("ALLOWED_ORIGINS", "").split(","),
            "supports_credentials": True,
        }
    })

    # ── BLUEPRINTS ────────────────────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.notes import notes_bp
    from app.routes.tags import tags_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(notes_bp, url_prefix="/api/notes")
    app.register_blueprint(tags_bp, url_prefix="/api/tags")

    # ── HEALTH CHECK ─────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    # ── SECURITY HEADERS ─────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:;"
        )
        return response

    with app.app_context():
        db.create_all()

    return app
