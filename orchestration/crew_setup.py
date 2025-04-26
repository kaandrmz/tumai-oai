"""
CrewAI setup module for orchestrating the multiagent system.
"""

import logging
from typing import Dict, List, Any
from crewai import Crew, Process, Agent, Task

from agents.teacher_agent import create_teacher_agent
from agents.student_agent import create_student_agent
from agents.security_agent import create_security_agent
from utils.document_retriever import DocumentRetriever
from utils.security_filter import SecurityFilter
from orchestration.tasks import (
    create_teacher_preparation_task,
    create_student_learning_task,
    create_security_monitoring_task
)

# Configure logging
logger = logging.getLogger(__name__)

class CrewOrchestrator:
    """
    Orchestrates the creation and execution of the CrewAI-based multiagent system.
    """

    def __init__(self, docs_path: str = None):
        """
        Initialize the crew orchestrator.

        Args:
            docs_path: Optional path to the documents directory
        """
        logger.info("Initializing CrewOrchestrator")

        # Initialize utility classes
        try:
            self.document_retriever = DocumentRetriever(docs_path) if docs_path else DocumentRetriever()
            self.security_filter = SecurityFilter()

            # Initialize agents
            self.teacher_agent = create_teacher_agent(self.document_retriever)
            self.student_agent = create_student_agent()
            self.security_agent = create_security_agent(self.security_filter)

            # Initialize tasks
            self.teacher_preparation_task = create_teacher_preparation_task(self.teacher_agent)
            self.student_learning_task = None  # Will be created at runtime with topic
            self.security_monitoring_task = create_security_monitoring_task(self.security_agent)

            # Initialize crew
            self.crew = None

            logger.info("CrewOrchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing CrewOrchestrator: {e}")
            raise

    def setup_crew(self, topic: str = None, process_type: Process = Process.sequential) -> Crew:
        """
        Set up the crew with the specified topic and process type.

        Args:
            topic: Optional topic for the educational session
            process_type: CrewAI process type (sequential or hierarchical)

        Returns:
            Configured Crew instance
        """
        logger.info(f"Setting up crew with topic '{topic}' and process type '{process_type}'")

        try:
            # Create student learning task with specified topic
            self.student_learning_task = create_student_learning_task(self.student_agent, topic)

            # Create the crew
            self.crew = Crew(
                agents=[
                    self.teacher_agent,
                    self.student_agent,
                    self.security_agent
                ],
                tasks=[
                    self.teacher_preparation_task,
                    self.student_learning_task,
                    self.security_monitoring_task
                ],
                verbose=True,
                process=process_type,
                memory=True  # Enable memory for better conversation flow
            )

            logger.info("Crew setup completed successfully")
            return self.crew
        except Exception as e:
            logger.error(f"Error setting up crew: {e}")
            raise

    def run_educational_session(self, topic: str = "general knowledge") -> Dict[str, Any]:
        """
        Run an educational session on the specified topic.

        Args:
            topic: Topic for the educational session

        Returns:
            Dictionary containing the result of the session
        """
        logger.info(f"Starting educational session on: {topic}")

        try:
            # Set up the crew if not already done
            if self.crew is None:
                self.setup_crew(topic)

            # Run the crew
            result = self.crew.kickoff(inputs={"topic": topic})

            logger.info(f"Educational session completed with result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error running educational session: {e}")
            raise