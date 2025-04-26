from fastapi import Depends, HTTPException
from app.agents.security_agent import SecurityAgent
from app.models import ReplyRequest


security_agent = SecurityAgent()


class SecurityBreachException(HTTPException):
    pass


def validate_teacher_reply(request: ReplyRequest = Depends()):
    """
    Validates the teacher's reply.
    """
    invalid_because = security_agent.check(request.history[-1].content)
    if invalid_because:
        raise SecurityBreachException(
            status_code=400,
            detail=f"Invalid teacher reply: {invalid_because}",
        )
    return request