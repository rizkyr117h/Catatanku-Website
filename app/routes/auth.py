import hashlib
import os
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
)
from email_validator import validate_email, EmailNotValidError

from app import db, bcrypt, limiter
from app.models import User, RefreshToken

auth_bp = Blueprint("auth", __name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── REGISTER ──────────────────────────────────────────────────────
@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Validation
    errors = {}
    if not username or len(username) < 3:
        errors["username"] = "Minimal 3 karakter."
    if len(username) > 64:
        errors["username"] = "Maksimal 64 karakter."
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        errors["email"] = "Email tidak valid."
    if len(password) < 8:
        errors["password"] = "Minimal 8 karakter."
    if errors:
        return jsonify({"errors": errors}), 422

    if User.query.filter_by(username=username).first():
        return jsonify({"errors": {"username": "Username sudah digunakan."}}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"errors": {"email": "Email sudah terdaftar."}}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(username=username, email=email, password_hash=pw_hash)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    _store_refresh_token(user.id, refresh_token)

    return jsonify({
        "message": "Registrasi berhasil.",
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), 201


# ── LOGIN ─────────────────────────────────────────────────────────
@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    user = (
        User.query.filter_by(username=identifier).first() or
        User.query.filter_by(email=identifier.lower()).first()
    )

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Username/email atau password salah."}), 401
    if not user.is_active:
        return jsonify({"error": "Akun dinonaktifkan."}), 403

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    _store_refresh_token(user.id, refresh_token)

    return jsonify({
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token,
    })


# ── REFRESH ───────────────────────────────────────────────────────
@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    raw_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    token_hash = _hash_token(raw_token)

    stored = RefreshToken.query.filter_by(
        user_id=user_id, token_hash=token_hash, revoked=False
    ).first()

    if not stored or stored.expires_at < datetime.now(timezone.utc):
        return jsonify({"error": "Token tidak valid atau kadaluarsa."}), 401

    # Rotate token
    stored.revoked = True
    new_access = create_access_token(identity=user_id)
    new_refresh = create_refresh_token(identity=user_id)
    _store_refresh_token(user_id, new_refresh)
    db.session.commit()

    return jsonify({"access_token": new_access, "refresh_token": new_refresh})


# ── LOGOUT ────────────────────────────────────────────────────────
@auth_bp.post("/logout")
@jwt_required()
def logout():
    user_id = get_jwt_identity()
    raw_token = request.get_json(silent=True, force=True).get("refresh_token", "")
    if raw_token:
        token_hash = _hash_token(raw_token)
        stored = RefreshToken.query.filter_by(user_id=user_id, token_hash=token_hash).first()
        if stored:
            stored.revoked = True
            db.session.commit()
    return jsonify({"message": "Logout berhasil."})


# ── ME ────────────────────────────────────────────────────────────
@auth_bp.get("/me")
@jwt_required()
def me():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"error": "User tidak ditemukan."}), 404
    return jsonify({"user": user.to_dict()})


# ── HELPER ───────────────────────────────────────────────────────
def _store_refresh_token(user_id: str, raw_token: str):
    rt = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:255],
    )
    db.session.add(rt)
    db.session.commit()
