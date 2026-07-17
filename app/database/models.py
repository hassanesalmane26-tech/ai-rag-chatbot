from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

from app.database.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

