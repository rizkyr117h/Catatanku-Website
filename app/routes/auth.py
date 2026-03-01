from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app import db, bcrypt
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    d = request.get_json() or {}
    username = (d.get("username") or "").strip()
    email    = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""

    if not username or not email or len(password) < 8:
        return jsonify({"error": "Username, email, dan password (min 8 karakter) wajib diisi."}), 422
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username sudah digunakan."}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email sudah terdaftar."}), 409

    user = User(username=username, email=email,
                password_hash=bcrypt.generate_password_hash(password).decode())
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "user": user.to_dict(),
        "access_token":  create_access_token(identity=user.id),
        "refresh_token": create_refresh_token(identity=user.id),
    }), 201


@auth_bp.post("/login")
def login():
    d = request.get_json() or {}
    identifier = (d.get("username") or d.get("email") or "").strip()
    password   = d.get("password") or ""

    user = (User.query.filter_by(username=identifier).first() or
            User.query.filter_by(email=identifier.lower()).first())

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Username/email atau password salah."}), 401

    return jsonify({
        "user": user.to_dict(),
        "access_token":  create_access_token(identity=user.id),
        "refresh_token": create_refresh_token(identity=user.id),
    })


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    uid = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=uid)})


@auth_bp.get("/me")
@jwt_required()
def me():
    user = User.query.get(get_jwt_identity())
    return jsonify({"user": user.to_dict()}) if user else (jsonify({"error": "Not found"}), 404)
