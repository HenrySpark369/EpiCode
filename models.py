# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

# Define db here, but don't initialize it yet
db = SQLAlchemy()

class RoleEnum(enum.Enum):
    system = "system"
    user = "user"
    assistant = "assistant"

class Conversation(db.Model):
    __tablename__ = "conversations"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, default="Sin título")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship(
        "Message", back_populates="conversation",
        cascade="all, delete-orphan", order_by="Message.turn_index"
    )

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    role = db.Column(db.Enum(RoleEnum), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    turn_index = db.Column(db.Integer, nullable=False)
    conversation = db.relationship("Conversation", back_populates="messages")