from pydantic import BaseModel
from typing import List, Optional, Dict


class Task(BaseModel):
    id: int
    title: str
    description: str


class ChatMessage(BaseModel):
    role: str  # 'student' 'teacher'
    content: str


class Scenario(BaseModel):
    session_id: int
    history: List[ChatMessage]


class ReplyRequest(BaseModel):
    session_id: int
    history: List[ChatMessage]


class ScoreFeedback(BaseModel):
    scenario: Scenario
    score: float
    is_end: bool
