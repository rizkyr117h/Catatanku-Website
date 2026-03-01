import uuid
from datetime import datetime, timezone
from app import db


def now(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.String(36), primary_key=True, default=uid)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime(timezone=True), default=now)
    notes         = db.relationship("Note", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    tags          = db.relationship("Tag",  backref="user", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


class Tag(db.Model):
    __tablename__ = "tags"
    __table_args__ = (db.UniqueConstraint("user_id", "name"),)
    id         = db.Column(db.String(36), primary_key=True, default=uid)
    user_id    = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name       = db.Column(db.String(64), nullable=False)
    color      = db.Column(db.String(7), default="#4a6741")
    notes      = db.relationship("Note", backref="tag", lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "color": self.color,
                "note_count": self.notes.filter_by(trash=False).count()}


class Note(db.Model):
    __tablename__ = "notes"
    id         = db.Column(db.String(36), primary_key=True, default=uid)
    user_id    = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tag_id     = db.Column(db.String(36), db.ForeignKey("tags.id",  ondelete="SET NULL"), nullable=True)
    title      = db.Column(db.String(255), default="")
    body       = db.Column(db.Text, default="")
    pinned     = db.Column(db.Boolean, default=False)
    trash      = db.Column(db.Boolean, default=False)
    deadline   = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    todos      = db.relationship("TodoItem", backref="note", cascade="all, delete-orphan",
                                 order_by="TodoItem.position", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "body": self.body,
            "pinned": self.pinned, "trash": self.trash,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "tag": {"id": self.tag.id, "name": self.tag.name, "color": self.tag.color} if self.tag else None,
            "todos": [t.to_dict() for t in self.todos],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TodoItem(db.Model):
    __tablename__ = "todo_items"
    id       = db.Column(db.String(36), primary_key=True, default=uid)
    note_id  = db.Column(db.String(36), db.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    text     = db.Column(db.String(512), nullable=False)
    done     = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {"id": self.id, "text": self.text, "done": self.done, "position": self.position}
