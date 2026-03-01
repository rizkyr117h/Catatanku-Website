from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Tag, Note

tags_bp = Blueprint("tags", __name__)

HEX_COLOR_RE = r"^#[0-9A-Fa-f]{6}$"


@tags_bp.get("/")
@jwt_required()
def list_tags():
    user_id = get_jwt_identity()
    tags = Tag.query.filter_by(user_id=user_id).order_by(Tag.name).all()
    return jsonify({"tags": [t.to_dict() for t in tags]})


@tags_bp.post("/")
@jwt_required()
def create_tag():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:64]
    color = (data.get("color") or "#4a6741").strip()

    if not name:
        return jsonify({"error": "Nama tag wajib diisi."}), 422

    import re
    if not re.match(HEX_COLOR_RE, color):
        color = "#4a6741"

    if Tag.query.filter_by(user_id=user_id, name=name).first():
        return jsonify({"error": "Tag sudah ada."}), 409

    tag = Tag(user_id=user_id, name=name, color=color)
    db.session.add(tag)
    db.session.commit()
    return jsonify(tag.to_dict()), 201


@tags_bp.put("/<tag_id>")
@jwt_required()
def update_tag(tag_id):
    user_id = get_jwt_identity()
    tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
    if not tag:
        return jsonify({"error": "Tag tidak ditemukan."}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = str(data["name"]).strip()[:64]
        if name and name != tag.name:
            if Tag.query.filter_by(user_id=user_id, name=name).first():
                return jsonify({"error": "Nama tag sudah ada."}), 409
            tag.name = name
    if "color" in data:
        import re
        color = str(data["color"]).strip()
        tag.color = color if re.match(HEX_COLOR_RE, color) else tag.color

    db.session.commit()
    return jsonify(tag.to_dict())


@tags_bp.delete("/<tag_id>")
@jwt_required()
def delete_tag(tag_id):
    user_id = get_jwt_identity()
    tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
    if not tag:
        return jsonify({"error": "Tag tidak ditemukan."}), 404

    # Unlink notes
    Note.query.filter_by(user_id=user_id, tag_id=tag_id).update({"tag_id": None})
    db.session.delete(tag)
    db.session.commit()
    return jsonify({"message": "Tag dihapus."})
