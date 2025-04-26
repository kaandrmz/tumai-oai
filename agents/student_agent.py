"""
Student agent implementation for the multiagent system.
"""

import os
import sys
from crewai import Agent

# Add the project root to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import llm


def create_student_agent() -> Agent:
    """
    Create the student agent focused on learning through questioning.

    Returns:
        Configured student agent
    """
    student_agent = Agent(
        role="Student",
        goal="Understand the subject matter through asking effective questions",
        backstory="""
        You are a curious learner who wants to gain comprehensive knowledge on various topics.
        You ask progressive questions that build upon previous answers to deepen your understanding.
        You continue questioning until you are satisfied with your understanding of the topic.
        You are specific in your questions and ask for clarification when needed.
        You process information systematically and identify gaps in your knowledge.
        """,
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    return student_agent