from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar        = Column(Text, nullable=True)        # base64 картинка
    bio           = Column(String(300), nullable=True) # о себе

    sent_messages = relationship(
        "Message", back_populates="sender", foreign_keys="Message.sender_id"
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Message(Base):
    __tablename__ = "messages"

    id           = Column(Integer, primary_key=True, index=True)
    sender_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    chat_type    = Column(String(20), nullable=False, default="global")
    text         = Column(Text, nullable=False)
    timestamp    = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<Message из {self.chat_type} от {self.sender_id}>"