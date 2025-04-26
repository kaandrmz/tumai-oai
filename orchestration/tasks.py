"""
Task definitions for the multiagent system.
"""

import logging
from crewai import Task, Agent
from typing import Dict, List

# Configure logging
logger = logging.getLogger(__name__)

def create_teacher_preparation_task(teacher_agent: Agent) -> Task:
    """
    Create the teacher preparation task.

    Args:
        teacher_agent: The teacher agent

    Returns:
        Configured teacher preparation task
    """
    logger.info("Creating teacher preparation task")

    teacher_preparation_task = Task(
        description="""
        Prepare to answer questions about the subject matter.
        Review the documents and be ready to share knowledge.
        Remember that some information might be confidential and should not be shared.
        
        Your preparation should include:
        1. Understanding the key concepts related to the topic
        2. Identifying the main points that should be communicated
        3. Recognizing potentially sensitive information that should be withheld
        4. Organizing information in a logical sequence for teaching
        """,
        agent=teacher_agent,
        expected_output="A summary of your preparation and approach to teaching the subject"
    )

    return teacher_preparation_task


def create_student_learning_task(student_agent: Agent, topic: str = None) -> Task:
    """
    Create the student learning task.

    Args:
        student_agent: The student agent
        topic: Optional topic to focus learning on

    Returns:
        Configured student learning task
    """
    topic_context = f" about {topic}" if topic else ""

    logger.info(f"Creating student learning task for topic '{topic}'")

    description = f"""
    Ask the Teacher questions{topic_context} to learn about the subject.
    Continue asking questions until you fully understand the material.
    Your questions should be progressive and build on previous answers.
    Be specific and ask for clarification when needed.
    
    Your learning process should include:
    1. Starting with foundational questions to establish basic understanding
    2. Following up with more specific questions based on the Teacher's responses
    3. Challenging your understanding by asking about connections between concepts
    4. Summarizing what you've learned periodically to ensure retention
    5. Identifying when you have sufficient understanding to conclude the session
    """

    # If topic is provided, include it in the description instead of context
    if topic:
        description = f"""
        Ask the Teacher questions about {topic} to learn about the subject.
        Continue asking questions until you fully understand {topic}.
        Your questions should be progressive and build on previous answers.
        Be specific and ask for clarification when needed.
        
        Your learning process should include:
        1. Starting with foundational questions to establish basic understanding of {topic}
        2. Following up with more specific questions based on the Teacher's responses
        3. Challenging your understanding by asking about connections between concepts in {topic}
        4. Summarizing what you've learned about {topic} periodically to ensure retention
        5. Identifying when you have sufficient understanding to conclude the session
        """

    student_learning_task = Task(
        description=description,
        agent=student_agent,
        expected_output=f"A summary of what you learned about {topic if topic else 'the subject'} and any remaining questions"
    )

    return student_learning_task


def create_security_monitoring_task(security_agent: Agent) -> Task:
    """
    Create the security monitoring task.

    Args:
        security_agent: The security agent

    Returns:
        Configured security monitoring task
    """
    logger.info("Creating security monitoring task")

    security_monitoring_task = Task(
        description="""
        Monitor all exchanges between the Teacher and Student.
        Prevent any disclosure of confidential information.
        Flag any potential security risks in the Teacher's responses.
        If confidential information is detected, intervene immediately.
        
        Your monitoring process should include:
        1. Analyzing all Teacher responses for potential security risks
        2. Filtering out any detected confidential information
        3. Providing explanations when information is removed for security reasons
        4. Balancing security concerns with educational needs
        5. Reporting any security incidents or near-misses
        """,
        agent=security_agent,
        expected_output="A security report detailing any interventions made and overall assessment"
    )

    return security_monitoring_task