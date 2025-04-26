"""
Optimized security dependencies for FastAPI routes.
"""
from fastapi import Depends, HTTPException, Request
from app.agents.security_agent import SecurityAgent
from app.models import ReplyRequest
import asyncio
import logging
from typing import List

# Configure logging
logger = logging.getLogger(__name__)

# Initialize security agent (singleton pattern ensures only one instance)
security_agent = SecurityAgent()


class SecurityBreachException(HTTPException):
    """
    Exception raised when a security breach is detected.
    """
    pass


async def validate_teacher_reply(request: ReplyRequest = Depends()) -> ReplyRequest:
    """
    Validates the teacher's reply asynchronously.
    Uses non-blocking processing for faster handling.

    Args:
        request: The request to validate

    Returns:
        The validated request

    Raises:
        SecurityBreachException: If the reply contains security risks
    """
    # Run security check in a background thread to avoid blocking
    invalid_because = await asyncio.to_thread(
        security_agent.check, request.history[-1].content
    )

    if invalid_because:
        logger.warning(f"Security breach detected: {invalid_because}")
        raise SecurityBreachException(
            status_code=400,
            detail=f"Invalid teacher reply: {invalid_because}",
        )
    return request


async def batch_validate_teacher_replies(requests: List[ReplyRequest]) -> List[ReplyRequest]:
    """
    Validates multiple teacher replies in batch.

    Args:
        requests: List of requests to validate

    Returns:
        List of validated requests
    """
    # Extract contents to check
    contents = [request.history[-1].content for request in requests]

    # Run batch check in background thread
    results = await asyncio.to_thread(security_agent.batch_check, contents)

    # Filter out invalid requests
    valid_requests = []
    for request, invalid_because in zip(requests, results):
        if not invalid_because:
            valid_requests.append(request)
        else:
            logger.warning(f"Security breach detected in batch: {invalid_because}")

    return valid_requests


async def content_security_middleware(request: Request, call_next):
    """
    Middleware to apply security checks to all responses.

    Args:
        request: The incoming request
        call_next: The next middleware or route handler

    Returns:
        The processed response
    """
    # Process the request normally
    response = await call_next(request)

    # If this is an API response with potential sensitive content, filter it
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        # Get the response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Convert to string and check for security issues
        body_str = body.decode("utf-8")
        filtered_body = await asyncio.to_thread(security_agent.filter_confidential_content, body_str)

        # If filtering changed anything, create a new response
        if filtered_body != body_str:
            logger.warning(f"Filtered sensitive content from response")

            # Create new response with filtered body
            return Response(
                content=filtered_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

    return response