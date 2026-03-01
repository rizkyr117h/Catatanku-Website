import uuid
from datetime import datetime, timezone
from app import db


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


# ── USER ──────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    tags = db.relationship("Tag", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    refresh_tokens = db.relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


# ── REFRESH TOKEN ─────────────────────────────────────────────────
class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="refresh_tokens")


# ── TAG ───────────────────────────────────────────────────────────
class Tag(db.Model):
    __tablename__ = "tags"
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_user_tag"),
    )

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(7), nullable=False, default="#4a6741")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="tags")
    notes = db.relationship("Note", back_populates="tag", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "note_count": self.notes.filter_by(trash=False).count(),
        }


# ── NOTE ──────────────────────────────────────────────────────────
class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = db.Column(db.String(36), db.ForeignKey("tags.id", ondelete="SET NULL"), nullable=True, index=True)

    title = db.Column(db.String(255), nullable=False, default="")
    body = db.Column(db.Text, nullable=False, default="")
    pinned = db.Column(db.Boolean, default=False, nullable=False)
    trash = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deadline = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="notes")
    tag = db.relationship("Tag", back_populates="notes")
    todos = db.relationship("TodoItem", back_populates="note", cascade="all, delete-orphan",
                            order_by="TodoItem.position", lazy="joined")

    def to_dict(self):
        tag_data = None
        if self.tag:
            tag_data = {"id": self.tag.id, "name": self.tag.name, "color": self.tag.color}
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "pinned": self.pinned,
            "trash": self.trash,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "tag": tag_data,
            "todos": [t.to_dict() for t in self.todos],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ── TODO ITEM ─────────────────────────────────────────────────────
class TodoItem(db.Model):
    __tablename__ = "todo_items"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    note_id = db.Column(db.String(36), db.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    text = db.Column(db.String(512), nullable=False)
    done = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    note = db.relationship("Note", back_populates="todos")

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done,
            "position": self.position,
        }
