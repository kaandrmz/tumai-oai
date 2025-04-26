from fastapi import HTTPException, Request
from fastapi import Depends

async def send_logvis_event(request: Request, event: str, data: dict):
    pass