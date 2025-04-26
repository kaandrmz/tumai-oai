"""
FastAPI endpoints for the multiagent system.
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional
from crewai import Process

# Add the project root to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orchestration.crew_setup import CrewOrchestrator

# Create FastAPI app
app = FastAPI(
    title="CrewAI Educational System API",
    description="API for running multiagent educational sessions with RAG",
    version="1.0.0"
)

# Initialize orchestrator
orchestrator = CrewOrchestrator()


class TopicRequest(BaseModel):
    """Request model for educational session."""
    topic: str
    process_type: Optional[str] = "sequential"  # Can be "sequential" or "hierarchical"
    docs_path: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    message: str


class SessionResponse(BaseModel):
    """Response model for educational session endpoint."""
    status: str
    result: Dict[str, Any]


@app.get("/health/", response_model=HealthResponse)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "message": "The CrewAI Educational System API is running correctly"
    }


@app.post("/educational-session/", response_model=SessionResponse)
async def create_educational_session(request: TopicRequest) -> Dict[str, Any]:
    """
    Create and run an educational session on the specified topic.

    Args:
        request: The session request containing topic and optional configurations

    Returns:
        Session result

    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        # Create a new orchestrator if a custom docs_path is provided
        session_orchestrator = orchestrator
        if request.docs_path:
            session_orchestrator = CrewOrchestrator(docs_path=request.docs_path)

        # Determine process type
        process_type = Process.sequential
        if request.process_type.lower() == "hierarchical":
            process_type = Process.hierarchical

        # Set up the crew with the specified process type
        session_orchestrator.setup_crew(request.topic, process_type)

        # Run the educational session
        result = session_orchestrator.run_educational_session(request.topic)

        return {
            "status": "success",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running educational session: {str(e)}"
        )