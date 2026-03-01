from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from app import db
from app.models import Note, Tag, TodoItem

notes_bp = Blueprint("notes", __name__)


def _note(note_id):
    return Note.query.filter_by(id=note_id, user_id=get_jwt_identity()).first()


def _parse_date(val):
    try: return date.fromisoformat(str(val)) if val else None
    except: return None


def _valid_tag(tag_id, user_id):
    if not tag_id: return None
    t = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
    return t.id if t else None


@notes_bp.get("/")
@jwt_required()
def list_notes():
    uid = get_jwt_identity()
    f   = request.args.get("filter", "all")
    q   = request.args.get("q", "").strip()

    query = Note.query.filter_by(user_id=uid)
    if f == "pinned":   query = query.filter_by(pinned=True, trash=False)
    elif f == "trash":  query = query.filter_by(trash=True)
    elif f == "deadline": query = query.filter(Note.deadline.isnot(None), Note.trash == False)
    elif f == "todo":   query = query.filter_by(trash=False).join(TodoItem).distinct()
    elif f == "tag":    query = query.filter_by(tag_id=request.args.get("tag_id"), trash=False)
    else:               query = query.filter_by(trash=False)

    if q:
        query = query.filter(or_(Note.title.ilike(f"%{q}%"), Note.body.ilike(f"%{q}%")))

    notes = query.order_by(Note.pinned.desc(), Note.updated_at.desc()).all()
    return jsonify({"notes": [n.to_dict() for n in notes]})


@notes_bp.post("/")
@jwt_required()
def create_note():
    uid = get_jwt_identity()
    d   = request.get_json() or {}
    note = Note(user_id=uid, title=(d.get("title") or "")[:255],
                body=d.get("body") or "", pinned=bool(d.get("pinned")),
                tag_id=_valid_tag(d.get("tag_id"), uid),
                deadline=_parse_date(d.get("deadline")))
    db.session.add(note)
    for i, item in enumerate(d.get("todos") or []):
        if item.get("text"):
            db.session.add(TodoItem(note=note, text=str(item["text"])[:512],
                                    done=bool(item.get("done")), position=i))
    db.session.commit()
    return jsonify(note.to_dict()), 201


@notes_bp.get("/<note_id>")
@jwt_required()
def get_note(note_id):
    n = _note(note_id)
    return jsonify(n.to_dict()) if n else (jsonify({"error": "Tidak ditemukan."}), 404)


@notes_bp.put("/<note_id>")
@jwt_required()
def update_note(note_id):
    uid = get_jwt_identity()
    n   = _note(note_id)
    if not n: return jsonify({"error": "Tidak ditemukan."}), 404
    d   = request.get_json() or {}
    if "title"    in d: n.title    = str(d["title"])[:255]
    if "body"     in d: n.body     = d["body"] or ""
    if "pinned"   in d: n.pinned   = bool(d["pinned"])
    if "trash"    in d: n.trash    = bool(d["trash"])
    if "deadline" in d: n.deadline = _parse_date(d["deadline"])
    if "tag_id"   in d: n.tag_id   = _valid_tag(d["tag_id"], uid)
    if "todos"    in d:
        TodoItem.query.filter_by(note_id=n.id).delete()
        for i, item in enumerate(d["todos"] or []):
            if item.get("text"):
                db.session.add(TodoItem(note_id=n.id, text=str(item["text"])[:512],
                                        done=bool(item.get("done")), position=i))
    db.session.commit()
    return jsonify(n.to_dict())


@notes_bp.delete("/<note_id>")
@jwt_required()
def delete_note(note_id):
    n = _note(note_id)
    if not n: return jsonify({"error": "Tidak ditemukan."}), 404
    if not n.trash: return jsonify({"error": "Pindahkan ke sampah dulu."}), 400
    db.session.delete(n)
    db.session.commit()
    return jsonify({"message": "Dihapus permanen."})


@notes_bp.delete("/trash/empty")
@jwt_required()
def empty_trash():
    count = Note.query.filter_by(user_id=get_jwt_identity(), trash=True).delete()
    db.session.commit()
    return jsonify({"message": f"{count} catatan dihapus."})
