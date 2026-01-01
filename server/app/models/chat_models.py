# app/models/chat_models.py (Example - adjust to your actual model)
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB # Import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid # Import uuid module
import datetime

from app.database import Base # Assuming Base is defined here

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)) 
    last_updated = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc)) 
    user_id = Column(String, nullable=True) 

    # NEW: Add history and summary columns here
    history = Column(JSONB, default='[]') 
    summary = Column(Text, nullable=True) # Stores the condensed summary of older messages