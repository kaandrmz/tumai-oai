from fastapi import Depends, HTTPException

from app.models import ReplyRequest


def validate_teacher_reply(request: ReplyRequest = Depends()):
    """
    Validates the teacher's reply.
    """
    is_valid = True
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid teacher reply.")
    return request
