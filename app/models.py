from pydantic import BaseModel
from typing import List, Optional, Dict

class Task(BaseModel):
    id: int
    title: str
    description: str

class ChatMessage(BaseModel):
    role: str  # 'student' 'teacher'
    content: str

class ReplyRequest(BaseModel):
    session_id: int
    history: List[ChatMessage]

class ReplyResponse(BaseModel):
    session_id: int
    history: List[ChatMessage]
    score: Optional[float] = None
    is_end: bool

class SessionInfo(BaseModel):
    id: str
    status: str
