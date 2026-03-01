from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_

from app import db, limiter
from app.models import Note, Tag, TodoItem

notes_bp = Blueprint("notes", __name__)


def _get_note_or_404(note_id: str, user_id: str) -> Note:
    note = Note.query.filter_by(id=note_id, user_id=user_id).first()
    if not note:
        return None
    return note


# ── LIST ──────────────────────────────────────────────────────────
@notes_bp.get("/")
@jwt_required()
def list_notes():
    user_id = get_jwt_identity()
    f = request.args.get("filter", "all")
    search = request.args.get("q", "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("per_page", 50)), 100)

    query = Note.query.filter_by(user_id=user_id)

    if f == "pinned":
        query = query.filter_by(pinned=True, trash=False)
    elif f == "trash":
        query = query.filter_by(trash=True)
    elif f == "deadline":
        query = query.filter(Note.deadline.isnot(None), Note.trash == False)
    elif f == "todo":
        query = query.filter_by(trash=False).join(TodoItem).distinct()
    elif f == "tag" and request.args.get("tag_id"):
        query = query.filter_by(tag_id=request.args.get("tag_id"), trash=False)
    else:
        query = query.filter_by(trash=False)

    if search:
        query = query.filter(
            or_(
                Note.title.ilike(f"%{search}%"),
                Note.body.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    notes = (
        query
        .order_by(Note.pinned.desc(), Note.updated_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "notes": [n.to_dict() for n in notes.items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": notes.pages,
    })


# ── CREATE ────────────────────────────────────────────────────────
@notes_bp.post("/")
@jwt_required()
@limiter.limit("120 per minute")
def create_note():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    tag_id = _validate_tag(data.get("tag_id"), user_id)

    note = Note(
        user_id=user_id,
        title=(data.get("title") or "")[:255],
        body=data.get("body") or "",
        tag_id=tag_id,
        pinned=bool(data.get("pinned", False)),
        deadline=_parse_date(data.get("deadline")),
    )
    db.session.add(note)

    for i, item in enumerate(data.get("todos") or []):
        if item.get("text"):
            db.session.add(TodoItem(
                note=note,
                text=str(item["text"])[:512],
                done=bool(item.get("done", False)),
                position=i,
            ))

    db.session.commit()
    return jsonify(note.to_dict()), 201


# ── GET ───────────────────────────────────────────────────────────
@notes_bp.get("/<note_id>")
@jwt_required()
def get_note(note_id):
    note = _get_note_or_404(note_id, get_jwt_identity())
    if not note:
        return jsonify({"error": "Catatan tidak ditemukan."}), 404
    return jsonify(note.to_dict())


# ── UPDATE ────────────────────────────────────────────────────────
@notes_bp.put("/<note_id>")
@jwt_required()
def update_note(note_id):
    user_id = get_jwt_identity()
    note = _get_note_or_404(note_id, user_id)
    if not note:
        return jsonify({"error": "Catatan tidak ditemukan."}), 404

    data = request.get_json(silent=True) or {}

    if "title" in data:
        note.title = str(data["title"])[:255]
    if "body" in data:
        note.body = data["body"] or ""
    if "pinned" in data:
        note.pinned = bool(data["pinned"])
    if "trash" in data:
        note.trash = bool(data["trash"])
    if "deadline" in data:
        note.deadline = _parse_date(data["deadline"])
    if "tag_id" in data:
        note.tag_id = _validate_tag(data["tag_id"], user_id)

    # Replace todos if provided
    if "todos" in data:
        TodoItem.query.filter_by(note_id=note.id).delete()
        for i, item in enumerate(data["todos"] or []):
            if item.get("text"):
                db.session.add(TodoItem(
                    note_id=note.id,
                    text=str(item["text"])[:512],
                    done=bool(item.get("done", False)),
                    position=i,
                ))

    db.session.commit()
    return jsonify(note.to_dict())


# ── DELETE (permanent) ────────────────────────────────────────────
@notes_bp.delete("/<note_id>")
@jwt_required()
def delete_note(note_id):
    note = _get_note_or_404(note_id, get_jwt_identity())
    if not note:
        return jsonify({"error": "Catatan tidak ditemukan."}), 404
    if not note.trash:
        return jsonify({"error": "Pindahkan ke sampah dulu."}), 400
    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Catatan dihapus permanen."})


# ── BULK EMPTY TRASH ──────────────────────────────────────────────
@notes_bp.delete("/trash/empty")
@jwt_required()
def empty_trash():
    user_id = get_jwt_identity()
    deleted = Note.query.filter_by(user_id=user_id, trash=True).delete()
    db.session.commit()
    return jsonify({"message": f"{deleted} catatan dihapus permanen."})


# ── HELPERS ───────────────────────────────────────────────────────
def _parse_date(val):
    if not val:
        return None
    try:
        from datetime import date
        return date.fromisoformat(str(val))
    except Exception:
        return None


def _validate_tag(tag_id, user_id):
    if not tag_id:
        return None
    tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
    return tag.id if tag else None
