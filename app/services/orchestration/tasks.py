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
        expected_output="A summary of your preparation and approach to teaching the subject",
        output_file="teacher_preparation.txt"  # Save output to file for reference
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
    topic_str = topic if topic else "the subject"
    logger.info(f"Creating student learning task for topic '{topic_str}'")

    description = f"""
    You are a student engaged in a learning session with a teacher about {topic_str}.
    
    Start by asking fundamental questions about {topic_str} to establish a baseline understanding.
    After each answer from the teacher, ask follow-up questions to deepen your knowledge.
    
    Your questions should:
    1. Be clear and specific
    2. Build upon the previous answers
    3. Address different aspects of {topic_str}
    4. Challenge your understanding
    
    Continue the conversation until you feel you have a comprehensive understanding of {topic_str}.
    
    IMPORTANT: For each response, include "STUDENT:" at the beginning to identify your part of the conversation.
    Always format your final summary as a dialogue between you (STUDENT) and the teacher.
    """

    student_learning_task = Task(
        description=description,
        agent=student_agent,
        expected_output=f"A detailed transcript of your learning conversation about {topic_str}, including all questions asked and knowledge gained",
        output_file="student_learning.txt"  # Save output to file for reference
    )

    return student_learning_task


def create_teacher_response_task(teacher_agent: Agent, topic: str = None) -> Task:
    """
    Create a task for the teacher to respond to student questions.

    Args:
        teacher_agent: The teacher agent
        topic: Optional topic to focus on

    Returns:
        Configured teacher response task
    """
    topic_str = topic if topic else "the subject"
    logger.info(f"Creating teacher response task for topic '{topic_str}'")

    description = f"""
    You are a teacher conducting a learning session about {topic_str}.
    
    A student will ask you questions about {topic_str}. Use your knowledge and the documents 
    you have access to in order to provide clear, accurate, and educational responses.
    
    Your responses should:
    1. Be informative and accurate
    2. Use examples and analogies when helpful
    3. Acknowledge when you're not certain about something
    4. Build progressively on the student's understanding
    
    IMPORTANT: For each response, include "TEACHER:" at the beginning to identify your part of the conversation.
    Always format your final summary as a dialogue between the student and you (TEACHER).
    """

    teacher_response_task = Task(
        description=description,
        agent=teacher_agent,
        expected_output=f"A detailed transcript of your teaching conversation about {topic_str}, including all answers provided and concepts explained",
        output_file="teacher_response.txt"  # Save output to file for reference
    )

    return teacher_response_task


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
        Your role is to work silently in the background, checking all information shared by the Teacher.
        
        If you detect any confidential information in the Teacher's responses:
        1. Use your tools to analyze the security risks
        2. Filter out the sensitive content
        3. Notify the system administrators (in your private logs)
        
        Do not interrupt the conversation unless absolutely necessary for security reasons.
        Your work should be invisible to the student, allowing for a natural learning experience.
        """,
        agent=security_agent,
        expected_output="A security report detailing any interventions made and overall assessment",
        output_file="security_monitoring.txt"  # Save output to file but not print to conversation
    )

    return security_monitoring_task