from fastapi import Depends, HTTPException
from app.agents.security_agent import SecurityAgent
from app.models import ReplyRequest

def validate_teacher_reply(request: ReplyRequest = Depends()):
    """
    Validates the teacher's reply.
    """
    security_agent = SecurityAgent()
    is_valid = security_agent.validate_reply(request)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid teacher reply.")
    return request
