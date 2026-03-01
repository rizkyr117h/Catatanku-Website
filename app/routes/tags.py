import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Tag, Note

tags_bp = Blueprint("tags", __name__)
HEX = r"^#[0-9A-Fa-f]{6}$"


@tags_bp.get("/")
@jwt_required()
def list_tags():
    tags = Tag.query.filter_by(user_id=get_jwt_identity()).order_by(Tag.name).all()
    return jsonify({"tags": [t.to_dict() for t in tags]})


@tags_bp.post("/")
@jwt_required()
def create_tag():
    uid = get_jwt_identity()
    d   = request.get_json() or {}
    name  = (d.get("name") or "").strip()[:64]
    color = (d.get("color") or "#4a6741").strip()
    if not name: return jsonify({"error": "Nama wajib diisi."}), 422
    if not re.match(HEX, color): color = "#4a6741"
    if Tag.query.filter_by(user_id=uid, name=name).first():
        return jsonify({"error": "Tag sudah ada."}), 409
    tag = Tag(user_id=uid, name=name, color=color)
    db.session.add(tag)
    db.session.commit()
    return jsonify(tag.to_dict()), 201


@tags_bp.put("/<tag_id>")
@jwt_required()
def update_tag(tag_id):
    uid = get_jwt_identity()
    tag = Tag.query.filter_by(id=tag_id, user_id=uid).first()
    if not tag: return jsonify({"error": "Tidak ditemukan."}), 404
    d = request.get_json() or {}
    if "name"  in d: tag.name  = str(d["name"]).strip()[:64] or tag.name
    if "color" in d and re.match(HEX, str(d["color"])): tag.color = d["color"]
    db.session.commit()
    return jsonify(tag.to_dict())


@tags_bp.delete("/<tag_id>")
@jwt_required()
def delete_tag(tag_id):
    uid = get_jwt_identity()
    tag = Tag.query.filter_by(id=tag_id, user_id=uid).first()
    if not tag: return jsonify({"error": "Tidak ditemukan."}), 404
    Note.query.filter_by(user_id=uid, tag_id=tag_id).update({"tag_id": None})
    db.session.delete(tag)
    db.session.commit()
    return jsonify({"message": "Tag dihapus."})
